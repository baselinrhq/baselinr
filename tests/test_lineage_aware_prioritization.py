"""
Tests for lineage-aware prioritization (Phase 3).

Tests cover:
- LineageAdapter for querying lineage data
- LineageGraph construction and metrics
- ImpactScorer calculations
- LineageAwareScorer integration
- Configuration schema for lineage settings
"""

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine, text

from baselinr.smart_selection.config import (
    LineageConfig,
    LineageQueryConfig,
    LineageScoringConfig,
    LineageScoringWeightsConfig,
    LineageBoostsConfig,
    LineagePenaltiesConfig,
    SmartSelectionConfig,
)
from baselinr.smart_selection.lineage.adapter import LineageAdapter
from baselinr.smart_selection.lineage.graph import LineageGraph, LineageNode
from baselinr.smart_selection.lineage.impact_scorer import (
    BlastRadius,
    ImpactScore,
    ImpactScorer,
    ScoringWeights,
    BoostFactors,
    create_impact_scorer,
)
from baselinr.smart_selection.lineage.lineage_scorer import (
    LineageAwareScorer,
    LineageScoringConfig as InternalLineageScoringConfig,
    LineageContext,
)


# Fixtures
@pytest.fixture
def sqlite_engine():
    """Create a SQLite in-memory engine with lineage data."""
    engine = create_engine("sqlite:///:memory:")
    
    # Create lineage table
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE baselinr_lineage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                downstream_schema VARCHAR(255),
                downstream_table VARCHAR(255) NOT NULL,
                downstream_database VARCHAR(255),
                upstream_schema VARCHAR(255),
                upstream_table VARCHAR(255) NOT NULL,
                upstream_database VARCHAR(255),
                lineage_type VARCHAR(100),
                provider VARCHAR(100),
                confidence_score REAL DEFAULT 1.0,
                metadata TEXT,
                last_seen_at TIMESTAMP
            )
        """))
        conn.commit()
    
    return engine


@pytest.fixture
def populated_engine(sqlite_engine):
    """Populate the engine with sample lineage data."""
    # Create a lineage graph:
    # raw.transactions (source) -> staging.transactions_cleaned -> marts.daily_revenue -> exposure.dashboard
    #                           -> staging.transactions_enriched -> marts.customer_ltv
    # raw.users (source) -> staging.users_cleaned -> marts.customer_ltv
    #                    -> staging.users_enriched -> marts.user_metrics
    # orphaned.unused_table (orphaned)
    
    edges = [
        # raw.transactions lineage
        ("staging", "transactions_cleaned", "raw", "transactions", "dbt_ref"),
        ("staging", "transactions_enriched", "raw", "transactions", "dbt_ref"),
        ("marts", "daily_revenue", "staging", "transactions_cleaned", "dbt_ref"),
        ("exposure", "dashboard", "marts", "daily_revenue", "exposure"),
        ("marts", "customer_ltv", "staging", "transactions_enriched", "dbt_ref"),
        
        # raw.users lineage
        ("staging", "users_cleaned", "raw", "users", "dbt_ref"),
        ("staging", "users_enriched", "raw", "users", "dbt_ref"),
        ("marts", "customer_ltv", "staging", "users_cleaned", "dbt_ref"),
        ("marts", "user_metrics", "staging", "users_enriched", "dbt_ref"),
        
        # exposure for ml_model
        ("exposure", "ml_model", "marts", "customer_ltv", "exposure"),
    ]
    
    with sqlite_engine.connect() as conn:
        for ds, dt, us, ut, lt in edges:
            conn.execute(text("""
                INSERT INTO baselinr_lineage 
                (downstream_schema, downstream_table, upstream_schema, upstream_table, lineage_type, provider, confidence_score)
                VALUES (:ds, :dt, :us, :ut, :lt, 'dbt', 1.0)
            """), {"ds": ds, "dt": dt, "us": us, "ut": ut, "lt": lt})
        conn.commit()
    
    return sqlite_engine


class TestLineageAdapter:
    """Tests for LineageAdapter."""
    
    def test_init(self, sqlite_engine):
        """Test adapter initialization."""
        adapter = LineageAdapter(engine=sqlite_engine)
        assert adapter.lineage_table == "baselinr_lineage"
        assert adapter.cache_ttl_hours == 24
        assert adapter.max_depth == 10
    
    def test_has_lineage_data_empty(self, sqlite_engine):
        """Test has_lineage_data returns False for empty table."""
        adapter = LineageAdapter(engine=sqlite_engine)
        assert adapter.has_lineage_data("nonexistent_table") is False
    
    def test_has_lineage_data_exists(self, populated_engine):
        """Test has_lineage_data returns True for existing table."""
        adapter = LineageAdapter(engine=populated_engine)
        assert adapter.has_lineage_data("transactions", "raw") is True
        assert adapter.has_lineage_data("daily_revenue", "marts") is True
    
    def test_get_upstream_tables_direct(self, populated_engine):
        """Test getting direct upstream dependencies."""
        adapter = LineageAdapter(engine=populated_engine)
        upstream = adapter.get_upstream_tables("transactions_cleaned", "staging", recursive=False)
        
        assert len(upstream) == 1
        assert upstream[0]["table"] == "transactions"
        assert upstream[0]["schema"] == "raw"
    
    def test_get_upstream_tables_recursive(self, populated_engine):
        """Test getting recursive upstream dependencies."""
        adapter = LineageAdapter(engine=populated_engine)
        upstream = adapter.get_upstream_tables("daily_revenue", "marts", recursive=True)
        
        # Should include: staging.transactions_cleaned and raw.transactions
        table_names = [u["table"] for u in upstream]
        assert "transactions_cleaned" in table_names
        assert "transactions" in table_names
    
    def test_get_downstream_tables_direct(self, populated_engine):
        """Test getting direct downstream dependencies."""
        adapter = LineageAdapter(engine=populated_engine)
        downstream = adapter.get_downstream_tables("transactions", "raw", recursive=False)
        
        assert len(downstream) == 2
        table_names = [d["table"] for d in downstream]
        assert "transactions_cleaned" in table_names
        assert "transactions_enriched" in table_names
    
    def test_get_downstream_tables_recursive(self, populated_engine):
        """Test getting recursive downstream dependencies."""
        adapter = LineageAdapter(engine=populated_engine)
        downstream = adapter.get_downstream_tables("transactions", "raw", recursive=True)
        
        # Should include all downstream tables
        table_names = [d["table"] for d in downstream]
        assert "transactions_cleaned" in table_names
        assert "daily_revenue" in table_names
        assert "dashboard" in table_names
    
    def test_get_all_tables_with_lineage(self, populated_engine):
        """Test getting all tables with lineage data."""
        adapter = LineageAdapter(engine=populated_engine)
        tables = adapter.get_all_tables_with_lineage()
        
        # Should have all unique tables
        assert len(tables) >= 10  # At least 10 unique tables
    
    def test_get_lineage_stats(self, populated_engine):
        """Test getting lineage statistics."""
        adapter = LineageAdapter(engine=populated_engine)
        stats = adapter.get_lineage_stats()
        
        assert stats["total_edges"] == 10
        assert stats["edges_by_provider"]["dbt"] == 10
    
    def test_cache_refresh(self, populated_engine):
        """Test cache refresh."""
        adapter = LineageAdapter(engine=populated_engine)
        
        # Populate cache
        adapter.get_all_tables_with_lineage()
        assert adapter._is_cache_valid()
        
        # Refresh should invalidate cache
        adapter.refresh_cache()
        assert not adapter._is_cache_valid()


class TestLineageGraph:
    """Tests for LineageGraph."""
    
    def test_build_from_adapter(self, populated_engine):
        """Test building graph from adapter."""
        adapter = LineageAdapter(engine=populated_engine)
        graph = LineageGraph.build_from_adapter(adapter)
        
        assert len(graph.nodes) >= 10
        assert graph._built is True
    
    def test_roots_identified(self, populated_engine):
        """Test root nodes are correctly identified."""
        adapter = LineageAdapter(engine=populated_engine)
        graph = LineageGraph.build_from_adapter(adapter)
        
        # Root tables should be raw.transactions and raw.users
        root_tables = [r.table for r in graph.roots]
        assert "transactions" in root_tables
        assert "users" in root_tables
    
    def test_leaves_identified(self, populated_engine):
        """Test leaf nodes are correctly identified."""
        adapter = LineageAdapter(engine=populated_engine)
        graph = LineageGraph.build_from_adapter(adapter)
        
        # Leaf tables should include exposures
        leaf_tables = [l.table for l in graph.leaves]
        assert "dashboard" in leaf_tables or "ml_model" in leaf_tables
    
    def test_node_metrics_computed(self, populated_engine):
        """Test node metrics are correctly computed."""
        adapter = LineageAdapter(engine=populated_engine)
        graph = LineageGraph.build_from_adapter(adapter)
        
        # Get raw.transactions node
        transactions_node = graph.get_node("transactions", "raw")
        assert transactions_node is not None
        assert transactions_node.is_root is True
        assert transactions_node.downstream_count >= 2
        assert transactions_node.total_downstream >= 4  # All downstream tables
    
    def test_depths_computed(self, populated_engine):
        """Test depths are correctly computed."""
        adapter = LineageAdapter(engine=populated_engine)
        graph = LineageGraph.build_from_adapter(adapter)
        
        # Root should have depth 0
        transactions_node = graph.get_node("transactions", "raw")
        assert transactions_node.depth == 0
        
        # Staging should have depth 1
        staging_node = graph.get_node("transactions_cleaned", "staging")
        if staging_node:
            assert staging_node.depth == 1
    
    def test_node_types_inferred(self, populated_engine):
        """Test node types are inferred from position and naming."""
        adapter = LineageAdapter(engine=populated_engine)
        graph = LineageGraph.build_from_adapter(adapter)
        
        # Raw tables should be sources
        transactions_node = graph.get_node("transactions", "raw")
        assert transactions_node.node_type == "source"
        
        # Exposure tables should have special type (may be mart or exposure)
        dashboard_node = graph.get_node("dashboard", "exposure")
        if dashboard_node:
            assert dashboard_node.is_leaf is True
    
    def test_get_subgraph(self, populated_engine):
        """Test getting a subgraph centered on a table."""
        adapter = LineageAdapter(engine=populated_engine)
        graph = LineageGraph.build_from_adapter(adapter)
        
        subgraph = graph.get_subgraph("daily_revenue", "marts", upstream_depth=2, downstream_depth=1)
        
        assert len(subgraph.nodes) >= 3  # At least center + upstream + downstream
    
    def test_graph_stats(self, populated_engine):
        """Test graph statistics."""
        adapter = LineageAdapter(engine=populated_engine)
        graph = LineageGraph.build_from_adapter(adapter)
        
        stats = graph.get_stats()
        assert stats["total_nodes"] >= 10
        assert stats["total_roots"] >= 2
        assert stats["total_leaves"] >= 2


class TestImpactScorer:
    """Tests for ImpactScorer."""
    
    def test_score_table(self, populated_engine):
        """Test scoring a single table."""
        adapter = LineageAdapter(engine=populated_engine)
        graph = LineageGraph.build_from_adapter(adapter)
        scorer = ImpactScorer(graph)
        
        score = scorer.score_table("transactions", "raw")
        
        assert score is not None
        assert 0.0 <= score.total_score <= 1.0
        assert score.position == "root"
        assert score.blast_radius.total_affected >= 4
    
    def test_root_table_has_high_score(self, populated_engine):
        """Test that root tables get higher scores."""
        adapter = LineageAdapter(engine=populated_engine)
        graph = LineageGraph.build_from_adapter(adapter)
        scorer = ImpactScorer(graph)
        
        root_score = scorer.score_table("transactions", "raw")
        staging_score = scorer.score_table("transactions_cleaned", "staging")
        
        # Root tables should have higher scores due to boost
        assert root_score.total_score >= staging_score.total_score
    
    def test_leaf_table_has_lower_score(self, populated_engine):
        """Test that leaf tables get lower scores."""
        adapter = LineageAdapter(engine=populated_engine)
        graph = LineageGraph.build_from_adapter(adapter)
        scorer = ImpactScorer(graph)
        
        root_score = scorer.score_table("transactions", "raw")
        leaf_score = scorer.score_table("dashboard", "exposure")
        
        if leaf_score:
            # Leaf tables should have lower scores due to penalty
            assert root_score.total_score > leaf_score.total_score
    
    def test_blast_radius_calculation(self, populated_engine):
        """Test blast radius calculation."""
        adapter = LineageAdapter(engine=populated_engine)
        graph = LineageGraph.build_from_adapter(adapter)
        scorer = ImpactScorer(graph)
        
        score = scorer.score_table("transactions", "raw")
        br = score.blast_radius
        
        assert br.immediate_downstream >= 2
        assert br.total_affected >= br.immediate_downstream
        assert br.estimated_user_impact in ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    
    def test_score_all_tables(self, populated_engine):
        """Test scoring all tables."""
        adapter = LineageAdapter(engine=populated_engine)
        graph = LineageGraph.build_from_adapter(adapter)
        scorer = ImpactScorer(graph)
        
        all_scores = scorer.score_all_tables()
        
        assert len(all_scores) >= 10
        for key, score in all_scores.items():
            assert 0.0 <= score.total_score <= 1.0
    
    def test_get_top_impact_tables(self, populated_engine):
        """Test getting top impact tables."""
        adapter = LineageAdapter(engine=populated_engine)
        graph = LineageGraph.build_from_adapter(adapter)
        scorer = ImpactScorer(graph)
        
        top_tables = scorer.get_top_impact_tables(limit=5)
        
        assert len(top_tables) <= 5
        # Scores should be in descending order
        for i in range(len(top_tables) - 1):
            assert top_tables[i].total_score >= top_tables[i + 1].total_score
    
    def test_custom_weights(self, populated_engine):
        """Test scorer with custom weights."""
        adapter = LineageAdapter(engine=populated_engine)
        graph = LineageGraph.build_from_adapter(adapter)
        
        # Custom weights emphasizing downstream count
        weights = ScoringWeights(
            downstream_count=0.7,
            criticality=0.1,
            depth_position=0.1,
            fanout=0.1,
        )
        scorer = ImpactScorer(graph, weights=weights)
        
        score = scorer.score_table("transactions", "raw")
        assert score is not None
    
    def test_custom_boosts(self, populated_engine):
        """Test scorer with custom boost factors."""
        adapter = LineageAdapter(engine=populated_engine)
        graph = LineageGraph.build_from_adapter(adapter)
        
        # Higher boost for root tables
        boosts = BoostFactors(
            root_tables=1.5,
            critical_path=1.3,
            high_fanout=1.2,
            leaf_tables=0.5,
            orphaned_tables=0.4,
        )
        scorer = ImpactScorer(graph, boosts=boosts)
        
        score = scorer.score_table("transactions", "raw")
        assert score is not None
    
    def test_create_impact_scorer_factory(self, populated_engine):
        """Test factory function for creating scorer."""
        adapter = LineageAdapter(engine=populated_engine)
        
        scorer = create_impact_scorer(
            adapter,
            weights={"downstream_count": 0.5, "criticality": 0.2, "depth_position": 0.2, "fanout": 0.1},
            boosts={"root_tables": 1.3},
        )
        
        assert scorer is not None
        score = scorer.score_table("transactions", "raw")
        assert score is not None


class TestLineageConfig:
    """Tests for lineage configuration schema."""
    
    def test_default_config(self):
        """Test default lineage configuration."""
        config = LineageConfig()
        
        assert config.enabled is True
        assert config.lineage_weight == 0.4
        assert config.query.cache_ttl_hours == 24
        assert config.scoring.weights.downstream_count == 0.4
    
    def test_scoring_weights_validation(self):
        """Test that scoring weights must sum to 1.0."""
        # Valid weights
        weights = LineageScoringWeightsConfig(
            downstream_count=0.4,
            criticality=0.3,
            depth_position=0.2,
            fanout=0.1,
        )
        assert weights is not None
        
        # Invalid weights should raise
        with pytest.raises(ValueError):
            LineageScoringWeightsConfig(
                downstream_count=0.5,
                criticality=0.5,
                depth_position=0.5,
                fanout=0.5,
            )
    
    def test_boost_config(self):
        """Test boost configuration."""
        boosts = LineageBoostsConfig(
            root_tables=1.3,
            critical_path=1.25,
            high_fanout=1.2,
        )
        
        assert boosts.root_tables == 1.3
        assert 1.0 <= boosts.root_tables <= 2.0
    
    def test_penalty_config(self):
        """Test penalty configuration."""
        penalties = LineagePenaltiesConfig(
            leaf_tables=0.7,
            orphaned_tables=0.5,
        )
        
        assert penalties.leaf_tables == 0.7
        assert 0.1 <= penalties.leaf_tables <= 1.0
    
    def test_smart_selection_config_with_lineage(self):
        """Test SmartSelectionConfig includes lineage settings."""
        config = SmartSelectionConfig(
            enabled=True,
            lineage=LineageConfig(
                enabled=True,
                lineage_weight=0.5,
            ),
        )
        
        assert config.lineage.enabled is True
        assert config.lineage.lineage_weight == 0.5


class TestLineageAwareScorer:
    """Tests for LineageAwareScorer integration."""
    
    def test_init(self):
        """Test scorer initialization."""
        from baselinr.smart_selection.config import SmartSelectionCriteria
        
        criteria = SmartSelectionCriteria()
        scorer = LineageAwareScorer(criteria)
        
        assert scorer.base_scorer is not None
        assert scorer.lineage_config is not None
    
    def test_set_lineage_engine(self, populated_engine):
        """Test setting up lineage engine."""
        from baselinr.smart_selection.config import SmartSelectionCriteria
        
        criteria = SmartSelectionCriteria()
        scorer = LineageAwareScorer(criteria)
        scorer.set_lineage_engine(populated_engine)
        
        assert scorer._lineage_adapter is not None
        assert scorer._lineage_graph is not None
        assert scorer._impact_scorer is not None
        assert len(scorer._impact_scores) >= 10
    
    def test_explain_table_lineage(self, populated_engine):
        """Test explaining lineage for a table."""
        from baselinr.smart_selection.config import SmartSelectionCriteria
        
        criteria = SmartSelectionCriteria()
        scorer = LineageAwareScorer(criteria)
        scorer.set_lineage_engine(populated_engine)
        
        explanation = scorer.explain_table_lineage("transactions", "raw")
        
        assert explanation["has_lineage"] is True
        assert "impact_score" in explanation
        assert explanation["impact_score"]["position"] == "root"
    
    def test_explain_nonexistent_table(self, populated_engine):
        """Test explaining lineage for a nonexistent table."""
        from baselinr.smart_selection.config import SmartSelectionCriteria
        
        criteria = SmartSelectionCriteria()
        scorer = LineageAwareScorer(criteria)
        scorer.set_lineage_engine(populated_engine)
        
        explanation = scorer.explain_table_lineage("nonexistent", "schema")
        
        assert explanation["has_lineage"] is False
    
    def test_get_graph_stats(self, populated_engine):
        """Test getting graph statistics."""
        from baselinr.smart_selection.config import SmartSelectionCriteria
        
        criteria = SmartSelectionCriteria()
        scorer = LineageAwareScorer(criteria)
        scorer.set_lineage_engine(populated_engine)
        
        stats = scorer.get_graph_stats()
        
        assert "total_nodes" in stats
        assert stats["total_nodes"] >= 10
    
    def test_refresh_lineage_data(self, populated_engine):
        """Test refreshing lineage data."""
        from baselinr.smart_selection.config import SmartSelectionCriteria
        
        criteria = SmartSelectionCriteria()
        scorer = LineageAwareScorer(criteria)
        scorer.set_lineage_engine(populated_engine)
        
        # Should not raise
        scorer.refresh_lineage_data()
        
        assert scorer._lineage_graph is not None


class TestBlastRadius:
    """Tests for BlastRadius dataclass."""
    
    def test_default_values(self):
        """Test default values."""
        br = BlastRadius()
        
        assert br.immediate_downstream == 0
        assert br.total_affected == 0
        assert br.estimated_user_impact == "NONE"
    
    def test_to_dict(self):
        """Test serialization."""
        br = BlastRadius(
            immediate_downstream=5,
            total_affected=15,
            critical_assets_affected=3,
            affected_exposures=["dashboard1", "dashboard2"],
            affected_tables=["table1", "table2", "table3"],
            estimated_user_impact="HIGH",
        )
        
        d = br.to_dict()
        
        assert d["immediate_downstream"] == 5
        assert d["total_affected"] == 15
        assert d["estimated_user_impact"] == "HIGH"
        assert len(d["affected_exposures"]) == 2


class TestImpactScore:
    """Tests for ImpactScore dataclass."""
    
    def test_default_values(self):
        """Test default values."""
        score = ImpactScore(table="test", schema="public")
        
        assert score.total_score == 0.0
        assert score.position == "unknown"
    
    def test_to_dict(self):
        """Test serialization."""
        score = ImpactScore(
            table="test",
            schema="public",
            total_score=0.85,
            downstream_score=0.9,
            depth_score=0.8,
            criticality_score=0.7,
            fanout_score=0.5,
            position="root",
            node_type="source",
            is_critical_path=True,
            reasoning=["High impact table"],
        )
        
        d = score.to_dict()
        
        assert d["total_score"] == 0.85
        assert d["position"] == "root"
        assert d["is_critical_path"] is True
        assert "component_scores" in d


class TestLineageNode:
    """Tests for LineageNode dataclass."""
    
    def test_identifier(self):
        """Test node identifier property."""
        node = LineageNode(table="test", schema="public")
        assert node.identifier == "public.test"
        
        node2 = LineageNode(table="test", schema="")
        assert node2.identifier == "test"
    
    def test_to_dict(self):
        """Test serialization."""
        node = LineageNode(
            table="test",
            schema="public",
            node_type="source",
            is_root=True,
            downstream_count=5,
        )
        
        d = node.to_dict()
        
        assert d["table"] == "test"
        assert d["is_root"] is True
        assert d["downstream_count"] == 5


# Integration tests
class TestIntegration:
    """Integration tests for the complete lineage-aware prioritization flow."""
    
    def test_full_flow(self, populated_engine):
        """Test the complete flow from adapter to scored recommendations."""
        from baselinr.smart_selection.config import SmartSelectionCriteria
        
        # 1. Create adapter
        adapter = LineageAdapter(engine=populated_engine)
        
        # 2. Build graph
        graph = LineageGraph.build_from_adapter(adapter)
        
        # 3. Create scorer
        scorer = ImpactScorer(graph)
        
        # 4. Get top impact tables
        top_tables = scorer.get_top_impact_tables(limit=5)
        
        # 5. Verify root tables are prioritized
        root_tables = [s for s in top_tables if s.position == "root"]
        assert len(root_tables) >= 1
        
        # 6. Verify blast radius is computed
        for score in top_tables:
            assert score.blast_radius is not None
            assert len(score.reasoning) > 0
    
    def test_lineage_aware_scorer_integration(self, populated_engine):
        """Test LineageAwareScorer integrates properly."""
        from baselinr.smart_selection.config import SmartSelectionCriteria
        
        criteria = SmartSelectionCriteria()
        scorer = LineageAwareScorer(
            criteria,
            lineage_config=InternalLineageScoringConfig(
                enabled=True,
                lineage_weight=0.5,
            ),
        )
        scorer.set_lineage_engine(populated_engine)
        
        # Explain a table
        explanation = scorer.explain_table_lineage("transactions", "raw")
        
        assert explanation["has_lineage"] is True
        assert explanation["impact_score"]["total_score"] > 0
        assert "blast_radius" in explanation["impact_score"]
