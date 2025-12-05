"""
Lineage-aware table scorer that integrates with smart selection.

Combines usage-based scoring (Phase 1) with lineage-based impact scoring
to provide comprehensive table prioritization.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy.engine import Engine

from ..config import SmartSelectionCriteria
from ..metadata_collector import TableMetadata
from ..scorer import TableScore, TableScorer
from .adapter import LineageAdapter
from .graph import LineageGraph
from .impact_scorer import BlastRadius, ImpactScore, ImpactScorer

logger = logging.getLogger(__name__)


@dataclass
class LineageContext:
    """Lineage context information for a table."""

    node_type: str = "unknown"
    depth: int = 0
    position: str = "unknown"  # root, intermediate, leaf, orphaned
    upstream_dependencies: int = 0
    downstream_dependencies: Dict[str, int] = field(default_factory=dict)
    blast_radius: Optional[BlastRadius] = None
    critical_path: bool = False
    reasoning: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "node_type": self.node_type,
            "depth": self.depth,
            "position": self.position,
            "upstream_dependencies": self.upstream_dependencies,
            "downstream_dependencies": self.downstream_dependencies,
            "critical_path": self.critical_path,
            "reasoning": self.reasoning,
        }
        if self.blast_radius:
            result["blast_radius"] = self.blast_radius.to_dict()
        return result


@dataclass
class LineageAwareTableScore(TableScore):
    """Extended table score with lineage information."""

    # Lineage scoring components
    lineage_score: float = 0.0
    lineage_context: Optional[LineageContext] = None

    # Check adjustments based on lineage
    check_adjustments: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "schema": self.metadata.schema,
            "table": self.metadata.table,
            "database": self.metadata.database,
            "total_score": round(self.total_score, 4),
            "confidence": round(self.confidence, 4),
            "usage_score": round(
                (
                    self.query_frequency_score * 0.4
                    + self.query_recency_score * 0.25
                    + self.write_activity_score * 0.2
                    + self.table_size_score * 0.15
                ),
                4,
            ),
            "lineage_score": round(self.lineage_score, 4),
            "reasons": self.reasons,
            "warnings": self.warnings,
        }
        if self.lineage_context:
            result["lineage_context"] = self.lineage_context.to_dict()
        if self.check_adjustments:
            result["check_adjustments"] = self.check_adjustments
        return result


@dataclass
class LineageScoringConfig:
    """Configuration for lineage-aware scoring."""

    enabled: bool = True

    # Weight for lineage in final score (rest goes to usage-based scoring)
    lineage_weight: float = 0.4

    # Impact scoring weights
    scoring_weights: Dict[str, float] = field(
        default_factory=lambda: {
            "downstream_count": 0.4,
            "criticality": 0.3,
            "depth_position": 0.2,
            "fanout": 0.1,
        }
    )

    # Boost/penalty factors
    boosts: Dict[str, float] = field(
        default_factory=lambda: {
            "root_tables": 1.25,
            "critical_path": 1.20,
            "high_fanout": 1.15,
        }
    )

    penalties: Dict[str, float] = field(
        default_factory=lambda: {
            "leaf_tables": 0.60,
            "orphaned_tables": 0.50,
        }
    )

    # Check adjustments based on lineage position
    check_adjustments: Dict[str, Dict[str, Any]] = field(
        default_factory=lambda: {
            "root_tables": {
                "prioritize_checks": ["freshness", "completeness", "schema_validation"],
                "severity": "critical",
            },
            "high_impact": {
                "min_confidence_threshold": 0.6,
                "check_frequency": "high",
            },
            "leaf_tables": {
                "min_confidence_threshold": 0.8,
                "check_frequency": "medium",
            },
        }
    )


class LineageAwareScorer:
    """
    Combines usage-based scoring with lineage-based impact scoring.

    Provides comprehensive table prioritization that considers both:
    - Phase 1: Usage patterns (query frequency, recency, etc.)
    - Phase 3: Lineage position and downstream impact
    """

    def __init__(
        self,
        criteria: SmartSelectionCriteria,
        lineage_config: Optional[LineageScoringConfig] = None,
    ):
        """
        Initialize lineage-aware scorer.

        Args:
            criteria: Smart selection criteria from Phase 1
            lineage_config: Optional lineage scoring configuration
        """
        self.criteria = criteria
        self.lineage_config = lineage_config or LineageScoringConfig()
        self.base_scorer = TableScorer(criteria)

        # Lineage components (initialized when set_lineage_engine is called)
        self._lineage_adapter: Optional[LineageAdapter] = None
        self._lineage_graph: Optional[LineageGraph] = None
        self._impact_scorer: Optional[ImpactScorer] = None
        self._impact_scores: Dict[str, ImpactScore] = {}

    def set_lineage_engine(
        self,
        engine: Engine,
        lineage_table: str = "baselinr_lineage",
        cache_ttl_hours: int = 24,
        max_depth: int = 10,
    ) -> None:
        """
        Set up lineage components with a database engine.

        Args:
            engine: SQLAlchemy engine for querying lineage data
            lineage_table: Name of the lineage table
            cache_ttl_hours: Cache TTL for lineage data
            max_depth: Maximum depth for recursive queries
        """
        self._lineage_adapter = LineageAdapter(
            engine=engine,
            lineage_table=lineage_table,
            cache_ttl_hours=cache_ttl_hours,
            max_depth=max_depth,
        )

        # Build the graph
        self._lineage_graph = LineageGraph.build_from_adapter(self._lineage_adapter)

        # Create impact scorer
        self._impact_scorer = ImpactScorer(
            graph=self._lineage_graph,
            weights=self._create_scoring_weights(),
            boosts=self._create_boost_factors(),
        )

        # Pre-compute all impact scores
        self._impact_scores = self._impact_scorer.score_all_tables()

        logger.info(
            f"Lineage scoring initialized: {len(self._lineage_graph.nodes)} nodes, "
            f"{len(self._impact_scores)} scores computed"
        )

    def _create_scoring_weights(self):
        """Create scoring weights from config."""
        from .impact_scorer import ScoringWeights

        weights = self.lineage_config.scoring_weights
        return ScoringWeights(
            downstream_count=weights.get("downstream_count", 0.4),
            criticality=weights.get("criticality", 0.3),
            depth_position=weights.get("depth_position", 0.2),
            fanout=weights.get("fanout", 0.1),
        )

    def _create_boost_factors(self):
        """Create boost factors from config."""
        from .impact_scorer import BoostFactors

        boosts = self.lineage_config.boosts
        penalties = self.lineage_config.penalties
        return BoostFactors(
            root_tables=boosts.get("root_tables", 1.25),
            critical_path=boosts.get("critical_path", 1.20),
            high_fanout=boosts.get("high_fanout", 1.15),
            leaf_tables=penalties.get("leaf_tables", 0.60),
            orphaned_tables=penalties.get("orphaned_tables", 0.50),
        )

    def score_tables(self, tables: List[TableMetadata]) -> List[LineageAwareTableScore]:
        """
        Score a list of tables with combined usage and lineage scoring.

        Args:
            tables: List of table metadata to score

        Returns:
            List of LineageAwareTableScore objects, sorted by score (highest first)
        """
        # Get base scores from Phase 1 scorer
        base_scores = self.base_scorer.score_tables(tables)

        # Convert to lineage-aware scores
        lineage_scores = []
        for base_score in base_scores:
            lineage_score = self._enhance_with_lineage(base_score)
            lineage_scores.append(lineage_score)

        # Re-sort by combined score
        lineage_scores.sort(reverse=True, key=lambda x: x.total_score)

        logger.info(
            f"Scored {len(lineage_scores)} tables with lineage-aware scoring "
            f"(lineage data available for {self._count_lineage_matches(tables)} tables)"
        )

        return lineage_scores

    def _enhance_with_lineage(self, base_score: TableScore) -> LineageAwareTableScore:
        """Enhance a base score with lineage information."""
        table = base_score.metadata.table
        schema = base_score.metadata.schema

        # Get lineage impact score
        impact_score = self._get_impact_score(table, schema)

        # Calculate combined score
        if impact_score and self.lineage_config.enabled:
            lineage_weight = self.lineage_config.lineage_weight
            usage_weight = 1.0 - lineage_weight

            # Usage-based score (normalized to 0-1)
            usage_score = base_score.total_score / 100.0  # Assuming 0-100 scale

            # Combined score
            combined_score = usage_weight * usage_score + lineage_weight * impact_score.total_score

            # Scale back to original range (0-100)
            total_score = combined_score * 100.0

            # Create lineage context
            lineage_context = self._create_lineage_context(impact_score)

            # Get check adjustments
            check_adjustments = self._get_check_adjustments(impact_score)

            # Add lineage-based reasons
            reasons = list(base_score.reasons)
            reasons.extend(impact_score.reasoning)
        else:
            # No lineage data - use base score
            total_score = base_score.total_score
            lineage_context = None
            check_adjustments = {}
            reasons = base_score.reasons

        return LineageAwareTableScore(
            metadata=base_score.metadata,
            total_score=total_score,
            confidence=base_score.confidence,
            query_frequency_score=base_score.query_frequency_score,
            query_recency_score=base_score.query_recency_score,
            write_activity_score=base_score.write_activity_score,
            table_size_score=base_score.table_size_score,
            reasons=reasons,
            warnings=base_score.warnings,
            lineage_score=impact_score.total_score if impact_score else 0.0,
            lineage_context=lineage_context,
            check_adjustments=check_adjustments,
        )

    def _get_impact_score(self, table: str, schema: Optional[str] = None) -> Optional[ImpactScore]:
        """Get pre-computed impact score for a table."""
        if not self._impact_scores:
            return None

        # Try different key formats
        key = f"{schema}.{table}" if schema else f".{table}"
        if key in self._impact_scores:
            return self._impact_scores[key]

        # Try without leading dot
        key = f"{schema}.{table}" if schema else table
        if key in self._impact_scores:
            return self._impact_scores[key]

        # Search by table name
        for score_key, score in self._impact_scores.items():
            if score.table == table and (schema is None or score.schema == schema):
                return score

        return None

    def _create_lineage_context(self, impact_score: ImpactScore) -> LineageContext:
        """Create lineage context from impact score."""
        return LineageContext(
            node_type=impact_score.node_type,
            depth=0,  # Would need graph node for this
            position=impact_score.position,
            upstream_dependencies=0,  # Would need graph node for this
            downstream_dependencies={
                "immediate": impact_score.blast_radius.immediate_downstream,
                "total": impact_score.blast_radius.total_affected,
            },
            blast_radius=impact_score.blast_radius,
            critical_path=impact_score.is_critical_path,
            reasoning=impact_score.reasoning,
        )

    def _get_check_adjustments(self, impact_score: ImpactScore) -> Dict[str, Any]:
        """Get check adjustments based on lineage position."""
        adjustments = {}
        config_adjustments = self.lineage_config.check_adjustments

        # Root tables
        if impact_score.position == "root":
            if "root_tables" in config_adjustments:
                adjustments.update(config_adjustments["root_tables"])

        # High impact tables
        if impact_score.total_score >= 0.7:
            if "high_impact" in config_adjustments:
                adjustments.update(config_adjustments["high_impact"])

        # Leaf tables
        if impact_score.position == "leaf":
            if "leaf_tables" in config_adjustments:
                adjustments.update(config_adjustments["leaf_tables"])

        return adjustments

    def _count_lineage_matches(self, tables: List[TableMetadata]) -> int:
        """Count how many tables have lineage data."""
        count = 0
        for table in tables:
            if self._get_impact_score(table.table, table.schema):
                count += 1
        return count

    def get_lineage_graph(self) -> Optional[LineageGraph]:
        """Get the lineage graph if available."""
        return self._lineage_graph

    def get_impact_scorer(self) -> Optional[ImpactScorer]:
        """Get the impact scorer if available."""
        return self._impact_scorer

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the lineage graph."""
        if not self._lineage_graph:
            return {"error": "Lineage graph not initialized"}
        return self._lineage_graph.get_stats()

    def explain_table_lineage(self, table: str, schema: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed lineage explanation for a table.

        Args:
            table: Table name
            schema: Optional schema name

        Returns:
            Dictionary with lineage details and scoring explanation
        """
        impact_score = self._get_impact_score(table, schema)

        if not impact_score:
            return {
                "table": table,
                "schema": schema,
                "has_lineage": False,
                "message": "No lineage data found for this table",
            }

        node = self._lineage_graph.get_node(table, schema) if self._lineage_graph else None

        result: Dict[str, Any] = {
            "table": table,
            "schema": schema,
            "has_lineage": True,
            "impact_score": impact_score.to_dict(),
        }

        if node:
            result["node"] = node.to_dict()
            result["upstream_tables"] = node.upstream[:10]
            result["downstream_tables"] = node.downstream[:10]

            # Get subgraph for visualization
            if self._lineage_graph:
                subgraph = self._lineage_graph.get_subgraph(table, schema, 2, 2)
                result["subgraph"] = {
                    "node_count": len(subgraph.nodes),
                    "nodes": list(subgraph.nodes.keys())[:20],
                }

        return result

    def refresh_lineage_data(self) -> None:
        """Refresh lineage data by re-querying and rebuilding the graph."""
        if self._lineage_adapter:
            self._lineage_adapter.refresh_cache()

            # Rebuild graph
            self._lineage_graph = LineageGraph.build_from_adapter(self._lineage_adapter)

            # Recreate scorer
            self._impact_scorer = ImpactScorer(
                graph=self._lineage_graph,
                weights=self._create_scoring_weights(),
                boosts=self._create_boost_factors(),
            )

            # Re-compute scores
            self._impact_scores = self._impact_scorer.score_all_tables()

            logger.info("Lineage data refreshed")
