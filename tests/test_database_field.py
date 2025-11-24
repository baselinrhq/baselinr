"""
Tests for database field functionality in TablePattern.

Verifies that the database field works correctly across all components:
- Schema validation
- Table key generation
- State store operations
- Planner expansion
"""

import pytest

from baselinr.config.schema import (
    BaselinrConfig,
    ConnectionConfig,
    ProfilingConfig,
    StorageConfig,
    TablePattern,
)
from baselinr.incremental.state import TableState, TableStateStore
from baselinr.planner import PlanBuilder


class TestDatabaseFieldSchema:
    """Tests for database field in TablePattern schema."""

    def test_database_field_optional(self):
        """Test that database field is optional (backward compatible)."""
        pattern = TablePattern(table="users", schema="public")
        assert pattern.database is None

    def test_database_field_with_explicit_table(self):
        """Test database field with explicit table."""
        pattern = TablePattern(table="users", schema="public", database="analytics_db")
        assert pattern.database == "analytics_db"
        assert pattern.table == "users"
        assert pattern.schema_ == "public"

    def test_database_field_with_pattern(self):
        """Test database field with pattern matching."""
        pattern = TablePattern(pattern="user_*", schema="public", database="warehouse_db")
        assert pattern.database == "warehouse_db"
        assert pattern.pattern == "user_*"

    def test_database_field_with_select_schema(self):
        """Test database field with select_schema."""
        pattern = TablePattern(select_schema=True, schema="analytics", database="production_db")
        assert pattern.database == "production_db"
        assert pattern.select_schema is True

    def test_database_field_with_select_all_schemas(self):
        """Test database field with select_all_schemas."""
        pattern = TablePattern(select_all_schemas=True, database="staging_db")
        assert pattern.database == "staging_db"
        assert pattern.select_all_schemas is True


class TestTableKeyGeneration:
    """Tests for table key generation with database field."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return BaselinrConfig(
            environment="test",
            source=ConnectionConfig(type="postgres", database="default_db"),
            storage=StorageConfig(
                connection=ConnectionConfig(type="sqlite", database=":memory:", filepath=":memory:")
            ),
            profiling=ProfilingConfig(),
        )

    def test_table_key_without_database(self, config):
        """Test table key generation without database (uses source.database)."""
        builder = PlanBuilder(config)
        pattern = TablePattern(table="users", schema="public")
        key = builder._table_key(pattern)
        # Should include source database
        assert "default_db" in key
        assert "public" in key
        assert "users" in key

    def test_table_key_with_database(self, config):
        """Test table key generation with explicit database."""
        builder = PlanBuilder(config)
        pattern = TablePattern(table="users", schema="public", database="analytics_db")
        key = builder._table_key(pattern)
        assert "analytics_db" in key
        assert "public" in key
        assert "users" in key
        assert key == "analytics_db.public.users"

    def test_table_key_without_schema(self, config):
        """Test table key generation without schema but with database."""
        builder = PlanBuilder(config)
        pattern = TablePattern(table="users", database="analytics_db")
        key = builder._table_key(pattern)
        assert "analytics_db" in key
        assert "users" in key
        assert key == "analytics_db.users"

    def test_table_key_format(self, config):
        """Test table key format is correct."""
        builder = PlanBuilder(config)
        
        # Full: database.schema.table
        pattern1 = TablePattern(table="users", schema="public", database="db1")
        assert builder._table_key(pattern1) == "db1.public.users"
        
        # Without schema: database.table
        pattern2 = TablePattern(table="users", database="db1")
        assert builder._table_key(pattern2) == "db1.users"
        
        # Without database: source_db.schema.table
        pattern3 = TablePattern(table="users", schema="public")
        key3 = builder._table_key(pattern3)
        assert key3.startswith("default_db")
        assert "public.users" in key3 or key3 == "default_db.public.users"


class TestStateStoreWithDatabase:
    """Tests for state store operations with database field."""

    @pytest.fixture
    def state_store(self, tmp_path):
        """Create test state store."""
        storage_path = tmp_path / "state.db"
        config = BaselinrConfig(
            environment="test",
            source=ConnectionConfig(type="postgres", database="test"),
            storage=StorageConfig(
                connection=ConnectionConfig(
                    type="sqlite", database=str(storage_path), filepath=str(storage_path)
                )
            ),
        )
        return TableStateStore(
            storage_config=config.storage,
            table_name="test_state",
            create_tables=True,
        )

    def test_table_state_key_with_database(self):
        """Test TableState table_key property with database."""
        state = TableState(
            table_name="users",
            schema_name="public",
            database_name="analytics_db",
        )
        assert state.table_key == "analytics_db.public.users"

    def test_table_state_key_without_database(self):
        """Test TableState table_key property without database."""
        state = TableState(table_name="users", schema_name="public")
        assert state.table_key == "public.users"

    def test_table_state_key_without_schema_or_database(self):
        """Test TableState table_key property without schema or database."""
        state = TableState(table_name="users")
        assert state.table_key == "users"

    def test_load_state_with_database(self, state_store):
        """Test loading state with database field."""
        # Create state with database
        state = TableState(
            table_name="users",
            schema_name="public",
            database_name="analytics_db",
            snapshot_id="snapshot123",
        )
        state_store.upsert_state(state)

        # Load state with database
        loaded = state_store.load_state("users", "public", "analytics_db")
        assert loaded is not None
        assert loaded.database_name == "analytics_db"
        assert loaded.table_name == "users"
        assert loaded.schema_name == "public"

    def test_load_state_without_database(self, state_store):
        """Test loading state without database (backward compatible)."""
        # Create state without database (None = source database)
        state = TableState(
            table_name="users",
            schema_name="public",
            snapshot_id="snapshot123",
        )
        state_store.upsert_state(state)

        # Load state without database
        loaded = state_store.load_state("users", "public", None)
        assert loaded is not None
        assert loaded.database_name is None
        assert loaded.table_name == "users"

    def test_record_decision_with_database(self, state_store):
        """Test recording decision with database field."""
        state_store.record_decision(
            table_name="users",
            schema_name="public",
            decision="skip",
            reason="no_changes",
            snapshot_id="snapshot123",
            database_name="analytics_db",
        )

        # Verify state was saved with database
        loaded = state_store.load_state("users", "public", "analytics_db")
        assert loaded is not None
        assert loaded.database_name == "analytics_db"
        assert loaded.decision == "skip"

    def test_database_isolation(self, state_store):
        """Test that states are isolated by database."""
        # Create state in database1
        state1 = TableState(
            table_name="users",
            schema_name="public",
            database_name="db1",
            snapshot_id="snapshot1",
        )
        state_store.upsert_state(state1)

        # Create state in database2 with same table/schema
        state2 = TableState(
            table_name="users",
            schema_name="public",
            database_name="db2",
            snapshot_id="snapshot2",
        )
        state_store.upsert_state(state2)

        # Verify they are separate
        loaded1 = state_store.load_state("users", "public", "db1")
        loaded2 = state_store.load_state("users", "public", "db2")

        assert loaded1 is not None
        assert loaded2 is not None
        assert loaded1.database_name == "db1"
        assert loaded2.database_name == "db2"
        assert loaded1.snapshot_id == "snapshot1"
        assert loaded2.snapshot_id == "snapshot2"

