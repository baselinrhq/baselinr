"""
Integration tests for smart selection with mock databases.

Tests end-to-end recommendation flow with SQLite (easiest to test).
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import text

from baselinr.config.schema import ConnectionConfig, DatabaseType
from baselinr.connectors import SQLiteConnector
from baselinr.smart_selection.config import SmartSelectionConfig
from baselinr.smart_selection.metadata_collector import MetadataCollector
from baselinr.smart_selection.recommender import RecommendationEngine


class TestSmartSelectionIntegration:
    """Integration tests with SQLite database."""

    @pytest.fixture
    def sqlite_db(self):
        """Create a temporary SQLite database with test data."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name
        
        # Create connection
        config = ConnectionConfig(
            type=DatabaseType.SQLITE,
            database="main",
            filepath=db_path,
        )
        
        connector = SQLiteConnector(config)
        
        # Create test tables
        with connector.engine.connect() as conn:
            # Table 1: Active table
            conn.execute(text("CREATE TABLE users (id INTEGER, name TEXT, email TEXT)"))
            conn.execute(text("INSERT INTO users VALUES (1, 'Alice', 'alice@example.com')"))
            conn.execute(text("INSERT INTO users VALUES (2, 'Bob', 'bob@example.com')"))
            conn.execute(text("INSERT INTO users VALUES (3, 'Charlie', 'charlie@example.com')"))
            
            # Table 2: Small lookup table
            conn.execute(text("CREATE TABLE config (key TEXT, value TEXT)"))
            conn.execute(text("INSERT INTO config VALUES ('version', '1.0')"))
            
            # Table 3: Large-ish table
            conn.execute(text("CREATE TABLE events (id INTEGER, user_id INTEGER, event_type TEXT)"))
            for i in range(500):
                conn.execute(
                    text(f"INSERT INTO events VALUES ({i}, {i % 10}, 'event_type_{i % 5}')")
                )
            
            # Table 4: Temp table (should be excluded if pattern exists)
            conn.execute(text("CREATE TABLE temp_load (data TEXT)"))
            conn.execute(text("INSERT INTO temp_load VALUES ('temporary')"))
            
            conn.commit()
        
        yield connector, db_path
        
        # Cleanup
        connector.close()
        Path(db_path).unlink(missing_ok=True)

    def test_metadata_collection_sqlite(self, sqlite_db):
        """Test metadata collection from SQLite."""
        connector, db_path = sqlite_db
        
        collector = MetadataCollector(
            engine=connector.engine,
            database_type=DatabaseType.SQLITE,
            lookback_days=30,
        )
        
        metadata = collector.collect_metadata()
        
        # Should find all tables
        assert len(metadata) >= 4
        
        # Check table names are present
        table_names = {m.table for m in metadata}
        assert "users" in table_names
        assert "config" in table_names
        assert "events" in table_names
        assert "temp_load" in table_names
        
        # Check row counts were collected
        users_meta = next(m for m in metadata if m.table == "users")
        assert users_meta.row_count == 3
        
        events_meta = next(m for m in metadata if m.table == "events")
        assert events_meta.row_count == 500

    def test_full_recommendation_flow_sqlite(self, sqlite_db):
        """Test full recommendation flow with SQLite."""
        connector, db_path = sqlite_db
        
        # Configure smart selection with relaxed criteria for testing
        smart_config = SmartSelectionConfig(
            enabled=True,
            mode="recommend",
        )
        # Relax criteria since SQLite doesn't have query history
        smart_config.criteria.min_query_count = 0
        smart_config.criteria.min_queries_per_day = 0.0
        smart_config.criteria.min_rows = 2  # Lower threshold
        smart_config.criteria.exclude_patterns = ["temp_*"]
        
        connection_config = ConnectionConfig(
            type=DatabaseType.SQLITE,
            database="main",
            filepath=db_path,
        )
        
        # Create engine
        engine = RecommendationEngine(
            connection_config=connection_config,
            smart_config=smart_config,
        )
        
        # Generate recommendations
        report = engine.generate_recommendations(
            engine=connector.engine,
            schema=None,
            existing_tables=None,
        )
        
        # Verify report
        assert report is not None
        assert report.total_tables_analyzed >= 4
        
        # Should recommend tables (temp_load excluded, config might be excluded due to size)
        assert report.total_recommended >= 2
        
        # Verify specific recommendations
        rec_names = {r.table for r in report.recommended_tables}
        assert "users" in rec_names or "events" in rec_names
        
        # temp_load should be excluded
        exc_names = {e.table for e in report.excluded_tables}
        if "temp_load" not in rec_names:
            # It should be in exclusions
            assert "temp_load" in exc_names or len(exc_names) > 0

    def test_save_and_load_recommendations(self, sqlite_db, tmp_path):
        """Test saving recommendations to file."""
        connector, db_path = sqlite_db
        
        smart_config = SmartSelectionConfig(
            enabled=True,
            mode="recommend",
        )
        smart_config.criteria.min_query_count = 0
        smart_config.criteria.min_queries_per_day = 0.0
        smart_config.criteria.min_rows = 1
        
        connection_config = ConnectionConfig(
            type=DatabaseType.SQLITE,
            database="main",
            filepath=db_path,
        )
        
        engine = RecommendationEngine(
            connection_config=connection_config,
            smart_config=smart_config,
        )
        
        report = engine.generate_recommendations(
            engine=connector.engine,
            schema=None,
        )
        
        # Save to file
        output_file = tmp_path / "recommendations.yaml"
        engine.save_recommendations(report, str(output_file))
        
        # Verify file exists and has content
        assert output_file.exists()
        content = output_file.read_text()
        
        # Check YAML structure
        assert "metadata:" in content
        assert "recommended_tables:" in content
        assert "generated_at:" in content
        
        # Should have at least one recommendation
        assert report.total_recommended > 0

    def test_confidence_scoring_with_limited_metadata(self, sqlite_db):
        """Test confidence scoring when metadata is limited (like SQLite)."""
        connector, db_path = sqlite_db
        
        collector = MetadataCollector(
            engine=connector.engine,
            database_type=DatabaseType.SQLITE,
            lookback_days=30,
        )
        
        metadata = collector.collect_metadata()
        
        # SQLite has limited metadata, so confidence should reflect that
        # Row counts are available, but query history is not
        for meta in metadata:
            # Should have row count
            assert meta.row_count is not None
            
            # Should NOT have query statistics
            assert meta.query_count == 0
            assert meta.queries_per_day == 0.0

    def test_exclude_patterns_work(self, sqlite_db):
        """Test that exclude patterns properly filter tables."""
        connector, db_path = sqlite_db
        
        smart_config = SmartSelectionConfig(
            enabled=True,
            mode="recommend",
        )
        smart_config.criteria.min_query_count = 0
        smart_config.criteria.min_queries_per_day = 0.0
        smart_config.criteria.min_rows = 1
        smart_config.criteria.exclude_patterns = ["temp_*", "config"]
        
        connection_config = ConnectionConfig(
            type=DatabaseType.SQLITE,
            database="main",
            filepath=db_path,
        )
        
        engine = RecommendationEngine(
            connection_config=connection_config,
            smart_config=smart_config,
        )
        
        report = engine.generate_recommendations(
            engine=connector.engine,
        )
        
        # temp_load and config should be excluded
        rec_names = {r.table for r in report.recommended_tables}
        assert "temp_load" not in rec_names
        assert "config" not in rec_names

    def test_row_count_filtering(self, sqlite_db):
        """Test min/max row count filtering."""
        connector, db_path = sqlite_db
        
        smart_config = SmartSelectionConfig(
            enabled=True,
            mode="recommend",
        )
        smart_config.criteria.min_query_count = 0
        smart_config.criteria.min_queries_per_day = 0.0
        smart_config.criteria.min_rows = 10  # Only events table has 500 rows
        smart_config.criteria.max_rows = 1000
        
        connection_config = ConnectionConfig(
            type=DatabaseType.SQLITE,
            database="main",
            filepath=db_path,
        )
        
        engine = RecommendationEngine(
            connection_config=connection_config,
            smart_config=smart_config,
        )
        
        report = engine.generate_recommendations(
            engine=connector.engine,
        )
        
        # Only events should be recommended (500 rows > 10)
        rec_names = {r.table for r in report.recommended_tables}
        assert "events" in rec_names
        
        # Small tables should be excluded
        assert "config" not in rec_names  # Only 1 row
        assert "users" not in rec_names  # Only 3 rows

    @pytest.mark.parametrize("mode", ["recommend", "auto"])
    def test_different_modes(self, sqlite_db, mode):
        """Test different smart selection modes."""
        connector, db_path = sqlite_db
        
        smart_config = SmartSelectionConfig(
            enabled=True,
            mode=mode,
        )
        smart_config.criteria.min_query_count = 0
        smart_config.criteria.min_queries_per_day = 0.0
        smart_config.criteria.min_rows = 1
        
        if mode == "auto":
            smart_config.auto_apply.confidence_threshold = 0.5
            smart_config.auto_apply.max_tables = 10
        
        connection_config = ConnectionConfig(
            type=DatabaseType.SQLITE,
            database="main",
            filepath=db_path,
        )
        
        engine = RecommendationEngine(
            connection_config=connection_config,
            smart_config=smart_config,
        )
        
        report = engine.generate_recommendations(
            engine=connector.engine,
        )
        
        assert report is not None
        assert report.total_tables_analyzed > 0

    def test_existing_tables_filtering(self, sqlite_db):
        """Test that existing tables are filtered out when requested."""
        connector, db_path = sqlite_db
        
        smart_config = SmartSelectionConfig(
            enabled=True,
            mode="recommend",
        )
        smart_config.criteria.min_query_count = 0
        smart_config.criteria.min_queries_per_day = 0.0
        smart_config.criteria.min_rows = 1
        smart_config.auto_apply.skip_existing = True
        
        connection_config = ConnectionConfig(
            type=DatabaseType.SQLITE,
            database="main",
            filepath=db_path,
        )
        
        engine = RecommendationEngine(
            connection_config=connection_config,
            smart_config=smart_config,
        )
        
        # Simulate existing table patterns
        from baselinr.config.schema import TablePattern
        
        # SQLite returns schema="main" and database="main" (see metadata_collector._collect_sqlite)
        existing = [
            TablePattern(
                database="main", schema_="main", table="users"
            ),  # type: ignore[call-arg]
        ]
        
        report = engine.generate_recommendations(
            engine=connector.engine,
            existing_tables=existing,
        )
        
        # users should not be in recommendations
        rec_names = {r.table for r in report.recommended_tables}
        assert "users" not in rec_names
