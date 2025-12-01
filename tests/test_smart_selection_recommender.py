"""
Unit tests for smart selection recommendation engine.

Tests the recommendation generation and report creation.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from baselinr.config.schema import ConnectionConfig, DatabaseType, TablePattern
from baselinr.smart_selection.config import SmartSelectionConfig
from baselinr.smart_selection.metadata_collector import TableMetadata
from baselinr.smart_selection.recommender import (
    ExcludedTable,
    RecommendationEngine,
    RecommendationReport,
    TableRecommendation,
)
from baselinr.smart_selection.scorer import TableScore


class TestTableRecommendation:
    """Test TableRecommendation dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        rec = TableRecommendation(
            database="prod",
            schema="analytics",
            table="users",
            confidence=0.95,
            score=87.5,
            reasons=["High query frequency", "Recently updated"],
            suggested_checks=["freshness", "row_count"],
        )
        
        result = rec.to_dict()
        
        assert result["schema"] == "analytics"
        assert result["table"] == "users"
        assert result["database"] == "prod"
        assert result["confidence"] == 0.95
        assert len(result["reasons"]) == 2
        assert len(result["suggested_checks"]) == 2

    def test_to_table_pattern(self):
        """Test conversion to TablePattern."""
        rec = TableRecommendation(
            database="prod",
            schema="analytics",
            table="users",
            confidence=0.95,
        )
        
        pattern = rec.to_table_pattern()
        
        assert isinstance(pattern, TablePattern)
        assert pattern.database == "prod"
        assert pattern.schema_ == "analytics"
        assert pattern.table == "users"


class TestExcludedTable:
    """Test ExcludedTable dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        exc = ExcludedTable(
            database="prod",
            schema="staging",
            table="temp_load",
            reasons=["Matches exclude pattern: temp_*", "Low query count"],
        )
        
        result = exc.to_dict()
        
        assert result["schema"] == "staging"
        assert result["table"] == "temp_load"
        assert result["database"] == "prod"
        assert len(result["reasons"]) == 2


class TestRecommendationReport:
    """Test RecommendationReport dataclass."""

    def test_to_yaml_dict(self):
        """Test conversion to YAML dictionary."""
        rec = TableRecommendation(
            schema="analytics",
            table="users",
            confidence=0.95,
            reasons=["High usage"],
        )
        
        exc = ExcludedTable(
            schema="staging",
            table="temp",
            reasons=["Excluded"],
        )
        
        report = RecommendationReport(
            generated_at=datetime.now(),
            lookback_days=30,
            database_type="postgres",
            recommended_tables=[rec],
            excluded_tables=[exc],
            total_tables_analyzed=10,
            total_recommended=1,
            total_excluded=1,
            confidence_distribution={"high (0.8+)": 1},
        )
        
        result = report.to_yaml_dict()
        
        assert "metadata" in result
        assert result["metadata"]["lookback_days"] == 30
        assert result["metadata"]["database_type"] == "postgres"
        assert len(result["recommended_tables"]) == 1
        assert len(result["excluded_tables"]) == 1


class TestRecommendationEngine:
    """Test RecommendationEngine class."""

    @pytest.fixture
    def connection_config(self):
        """Create connection config for testing."""
        return ConnectionConfig(
            type=DatabaseType.POSTGRES,
            host="localhost",
            port=5432,
            database="testdb",
            username="testuser",
            password="testpass",
        )

    @pytest.fixture
    def smart_config(self):
        """Create smart selection config for testing."""
        return SmartSelectionConfig(
            enabled=True,
            mode="recommend",
        )

    @pytest.fixture
    def engine(self, connection_config, smart_config):
        """Create recommendation engine instance."""
        return RecommendationEngine(
            connection_config=connection_config,
            smart_config=smart_config,
        )

    def test_engine_initialization(self, engine):
        """Test engine initialization."""
        assert engine.database_type == DatabaseType.POSTGRES
        assert engine.scorer is not None

    def test_suggest_checks_active_table(self, engine):
        """Test suggested checks for active table."""
        table = TableMetadata(
            database="prod",
            schema="analytics",
            table="users",
            query_count=500,
            queries_per_day=20.0,
            row_count=100000,
            table_type="BASE TABLE",
        )
        
        checks = engine._suggest_checks(table)
        
        assert "freshness" in checks
        assert "row_count" in checks
        assert "completeness" in checks

    def test_suggest_checks_view(self, engine):
        """Test suggested checks for view."""
        table = TableMetadata(
            database="prod",
            schema="analytics",
            table="user_summary",
            query_count=100,
            queries_per_day=5.0,
            table_type="VIEW",
        )
        
        checks = engine._suggest_checks(table)
        
        # Should not suggest numeric_distribution for views
        assert "freshness" in checks
        assert "row_count" in checks

    def test_filter_existing_tables(self, engine):
        """Test filtering of existing tables."""
        # Create some scored tables
        scored_tables = [
            Mock(
                metadata=TableMetadata(
                    database="prod",
                    schema="analytics",
                    table="users",
                    query_count=100,
                    queries_per_day=5.0,
                )
            ),
            Mock(
                metadata=TableMetadata(
                    database="prod",
                    schema="analytics",
                    table="events",
                    query_count=200,
                    queries_per_day=10.0,
                )
            ),
        ]
        
        # Existing patterns include "users"
        existing_patterns = [
            TablePattern(database="prod", schema_="analytics", table="users")
        ]
        
        filtered = engine._filter_existing(scored_tables, existing_patterns)
        
        # Should only have "events" left
        assert len(filtered) == 1
        assert filtered[0].metadata.table == "events"

    def test_explain_exclusion(self, engine):
        """Test exclusion reason generation."""
        table = TableMetadata(
            database="prod",
            schema="staging",
            table="temp_load",
            query_count=5,  # Below threshold
            queries_per_day=0.5,  # Below threshold
            row_count=50,  # Below min
        )
        
        reasons = engine._explain_exclusion(table)
        
        assert len(reasons) >= 2
        assert any("query count" in r.lower() for r in reasons)
        assert any("queries per day" in r.lower() for r in reasons)

    def test_calculate_confidence_distribution(self, engine):
        """Test confidence distribution calculation."""
        scored_tables = [
            Mock(confidence=0.95),
            Mock(confidence=0.85),
            Mock(confidence=0.70),
            Mock(confidence=0.50),
        ]
        
        dist = engine._calculate_confidence_distribution(scored_tables)
        
        assert dist["high (0.8+)"] == 2
        assert dist["medium (0.6-0.8)"] == 1
        assert dist["low (<0.6)"] == 1

    @patch("baselinr.smart_selection.recommender.MetadataCollector")
    def test_generate_recommendations_basic(self, mock_collector_class, engine):
        """Test basic recommendation generation."""
        # Mock metadata collection
        mock_collector = Mock()
        mock_collector_class.return_value = mock_collector
        
        sample_metadata = [
            TableMetadata(
                database="prod",
                schema="analytics",
                table="users",
                query_count=500,
                queries_per_day=20.0,
                last_query_time=datetime.now(),
                row_count=100000,
            ),
            TableMetadata(
                database="prod",
                schema="analytics",
                table="events",
                query_count=5,  # Too low, will be excluded
                queries_per_day=0.2,
                row_count=1000,
            ),
        ]
        mock_collector.collect_metadata.return_value = sample_metadata
        
        # Mock engine
        mock_engine = Mock()
        
        # Generate recommendations
        report = engine.generate_recommendations(
            engine=mock_engine,
            schema="analytics",
            existing_tables=None,
        )
        
        assert isinstance(report, RecommendationReport)
        assert report.total_tables_analyzed == 2
        # Only "users" should be recommended (events filtered out)
        assert report.total_recommended == 1
        assert report.recommended_tables[0].table == "users"

    def test_create_recommendation(self, engine):
        """Test recommendation creation from score."""
        metadata = TableMetadata(
            database="prod",
            schema="analytics",
            table="users",
            query_count=500,
            queries_per_day=20.0,
            row_count=100000,
            last_query_time=datetime.now(),
        )
        
        score = TableScore(
            metadata=metadata,
            total_score=87.5,
            confidence=0.95,
            query_frequency_score=90.0,
            query_recency_score=95.0,
            write_activity_score=80.0,
            table_size_score=85.0,
            reasons=["High query frequency", "Recently queried"],
            warnings=[],
        )
        
        rec = engine._create_recommendation(score)
        
        assert isinstance(rec, TableRecommendation)
        assert rec.table == "users"
        assert rec.confidence == 0.95
        assert rec.score == 87.5
        assert len(rec.reasons) == 2
        assert len(rec.suggested_checks) > 0

    def test_save_recommendations(self, engine, tmp_path):
        """Test saving recommendations to file."""
        report = RecommendationReport(
            generated_at=datetime.now(),
            lookback_days=30,
            database_type="postgres",
            recommended_tables=[
                TableRecommendation(
                    schema="analytics",
                    table="users",
                    confidence=0.95,
                    reasons=["High usage"],
                )
            ],
            excluded_tables=[],
            total_tables_analyzed=10,
            total_recommended=1,
            total_excluded=0,
        )
        
        output_file = tmp_path / "recommendations.yaml"
        engine.save_recommendations(report, str(output_file))
        
        assert output_file.exists()
        
        # Verify file content
        content = output_file.read_text()
        assert "Baselinr Table Recommendations" in content
        assert "recommended_tables" in content
        assert "users" in content

    def test_auto_mode_confidence_threshold(self, connection_config):
        """Test auto mode applies confidence threshold."""
        smart_config = SmartSelectionConfig(
            enabled=True,
            mode="auto",
        )
        smart_config.auto_apply.confidence_threshold = 0.9
        
        engine = RecommendationEngine(
            connection_config=connection_config,
            smart_config=smart_config,
        )
        
        # Mock the process
        with patch.object(engine, "_create_recommendation") as mock_create:
            with patch("baselinr.smart_selection.recommender.MetadataCollector") as mock_collector_class:
                mock_collector = Mock()
                mock_collector_class.return_value = mock_collector
                
                # Return tables with varying confidence
                sample_metadata = [
                    TableMetadata(
                        database="prod",
                        schema="analytics",
                        table="high_conf",
                        query_count=500,
                        queries_per_day=20.0,
                        row_count=100000,
                    )
                ]
                mock_collector.collect_metadata.return_value = sample_metadata
                
                mock_engine = Mock()
                report = engine.generate_recommendations(engine=mock_engine)
                
                # Verify scorer was called
                assert report is not None

    def test_max_tables_limit(self, connection_config):
        """Test max_tables limit is applied."""
        smart_config = SmartSelectionConfig(
            enabled=True,
            mode="recommend",
        )
        smart_config.auto_apply.max_tables = 5
        
        engine = RecommendationEngine(
            connection_config=connection_config,
            smart_config=smart_config,
        )
        
        with patch("baselinr.smart_selection.recommender.MetadataCollector") as mock_collector_class:
            mock_collector = Mock()
            mock_collector_class.return_value = mock_collector
            
            # Return 10 tables but max_tables is 5
            sample_metadata = [
                TableMetadata(
                    database="prod",
                    schema="analytics",
                    table=f"table_{i}",
                    query_count=100 + i * 10,
                    queries_per_day=5.0 + i,
                    row_count=10000,
                )
                for i in range(10)
            ]
            mock_collector.collect_metadata.return_value = sample_metadata
            
            mock_engine = Mock()
            report = engine.generate_recommendations(engine=mock_engine)
            
            # Should only recommend 5 tables (the top 5 by score)
            assert report.total_recommended <= 5
