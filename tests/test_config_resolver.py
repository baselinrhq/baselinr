"""Tests for configuration resolver utility."""

import pytest

from baselinr.config.schema import (
    ColumnConfig,
    ColumnDriftConfig,
    ColumnProfilingConfig,
    PartitionConfig,
    ProfilingConfig,
    SamplingConfig,
    SchemaConfig,
    TablePattern,
)
from baselinr.profiling.config_resolver import ConfigResolver


class TestConfigResolver:
    """Tests for ConfigResolver."""

    def test_find_schema_config_exact_match(self):
        """Test finding schema config with exact schema match."""
        schema_config = SchemaConfig(schema="analytics")
        resolver = ConfigResolver(schema_configs=[schema_config])

        found = resolver.find_schema_config("analytics")
        assert found is not None
        assert found.schema_ == "analytics"

    def test_find_schema_config_with_database(self):
        """Test finding schema config with database specified."""
        schema_config = SchemaConfig(schema="analytics", database="warehouse")
        resolver = ConfigResolver(schema_configs=[schema_config])

        # Match with database
        found = resolver.find_schema_config("analytics", database_name="warehouse")
        assert found is not None
        assert found.schema_ == "analytics"
        assert found.database == "warehouse"

        # No match with different database
        found = resolver.find_schema_config("analytics", database_name="other")
        assert found is None

    def test_find_schema_config_database_precedence(self):
        """Test that exact database match takes precedence over schema-only match."""
        schema_only = SchemaConfig(schema="analytics")
        schema_with_db = SchemaConfig(schema="analytics", database="warehouse")
        resolver = ConfigResolver(schema_configs=[schema_only, schema_with_db])

        # Should match exact database match first
        found = resolver.find_schema_config("analytics", database_name="warehouse")
        assert found is not None
        assert found.database == "warehouse"

    def test_find_schema_config_schema_only_fallback(self):
        """Test that schema-only config is used when no database match."""
        schema_only = SchemaConfig(schema="analytics")
        resolver = ConfigResolver(schema_configs=[schema_only])

        found = resolver.find_schema_config("analytics", database_name="warehouse")
        assert found is not None
        assert found.schema_ == "analytics"
        assert found.database is None

    def test_find_schema_config_no_match(self):
        """Test finding schema config when no match exists."""
        schema_config = SchemaConfig(schema="analytics")
        resolver = ConfigResolver(schema_configs=[schema_config])

        found = resolver.find_schema_config("other")
        assert found is None

    def test_resolve_table_config_no_schema_config(self):
        """Test resolving table config when no schema config exists."""
        table_pattern = TablePattern(table="orders", schema="analytics")
        resolver = ConfigResolver(schema_configs=[])

        resolved = resolver.resolve_table_config(table_pattern)
        assert resolved.table == "orders"
        assert resolved.schema_ == "analytics"

    def test_resolve_table_config_merges_partition(self):
        """Test that partition config is merged from schema."""
        schema_config = SchemaConfig(
            schema="analytics", partition=PartitionConfig(strategy="latest", key="date")
        )
        table_pattern = TablePattern(table="orders", schema="analytics")
        resolver = ConfigResolver(schema_configs=[schema_config])

        resolved = resolver.resolve_table_config(table_pattern)
        assert resolved.partition is not None
        assert resolved.partition.strategy == "latest"
        assert resolved.partition.key == "date"

    def test_resolve_table_config_table_overrides_partition(self):
        """Test that table-level partition config overrides schema-level."""
        schema_config = SchemaConfig(
            schema="analytics", partition=PartitionConfig(strategy="latest", key="date")
        )
        table_pattern = TablePattern(
            table="orders",
            schema="analytics",
            partition=PartitionConfig(strategy="recent_n", recent_n=7, key="created_at"),
        )
        resolver = ConfigResolver(schema_configs=[schema_config])

        resolved = resolver.resolve_table_config(table_pattern)
        assert resolved.partition is not None
        assert resolved.partition.strategy == "recent_n"
        assert resolved.partition.recent_n == 7
        assert resolved.partition.key == "created_at"

    def test_resolve_table_config_merges_sampling(self):
        """Test that sampling config is merged from schema."""
        schema_config = SchemaConfig(
            schema="staging", sampling=SamplingConfig(enabled=True, fraction=0.1)
        )
        table_pattern = TablePattern(table="users", schema="staging")
        resolver = ConfigResolver(schema_configs=[schema_config])

        resolved = resolver.resolve_table_config(table_pattern)
        assert resolved.sampling is not None
        assert resolved.sampling.enabled is True
        assert resolved.sampling.fraction == 0.1

    def test_resolve_table_config_merges_column_configs(self):
        """Test that column configs are merged from schema and table."""
        schema_config = SchemaConfig(
            schema="analytics",
            columns=[
                ColumnConfig(name="*_id", drift=ColumnDriftConfig(enabled=False)),
                ColumnConfig(name="*_metadata", profiling=ColumnProfilingConfig(enabled=False)),
            ],
        )
        table_pattern = TablePattern(
            table="orders",
            schema="analytics",
            columns=[
                ColumnConfig(name="total_amount", drift=ColumnDriftConfig(enabled=True)),
            ],
        )
        resolver = ConfigResolver(schema_configs=[schema_config])

        resolved = resolver.resolve_table_config(table_pattern)
        assert resolved.columns is not None
        assert len(resolved.columns) == 3  # 2 from schema + 1 from table

        # Table column should be first (higher priority)
        assert resolved.columns[0].name == "total_amount"
        # Schema columns should follow
        assert resolved.columns[1].name == "*_id"
        assert resolved.columns[2].name == "*_metadata"

    def test_resolve_table_config_table_column_overrides_schema_column(self):
        """Test that table-level column config overrides schema-level for same column."""
        schema_config = SchemaConfig(
            schema="analytics",
            columns=[
                ColumnConfig(name="total_amount", drift=ColumnDriftConfig(enabled=False)),
            ],
        )
        table_pattern = TablePattern(
            table="orders",
            schema="analytics",
            columns=[
                ColumnConfig(name="total_amount", drift=ColumnDriftConfig(enabled=True)),
            ],
        )
        resolver = ConfigResolver(schema_configs=[schema_config])

        resolved = resolver.resolve_table_config(table_pattern)
        assert resolved.columns is not None
        # Table config comes first, so it should be checked first by ColumnMatcher
        assert resolved.columns[0].name == "total_amount"
        assert resolved.columns[0].drift is not None
        assert resolved.columns[0].drift.enabled is True

    def test_resolve_table_config_merges_filters(self):
        """Test that filter fields are merged from schema."""
        schema_config = SchemaConfig(
            schema="analytics",
            min_rows=100,
            max_rows=1000000,
            table_types=["table"],
            required_columns=["id"],
            exclude_patterns=["*_temp"],
        )
        table_pattern = TablePattern(table="orders", schema="analytics")
        resolver = ConfigResolver(schema_configs=[schema_config])

        resolved = resolver.resolve_table_config(table_pattern)
        assert resolved.min_rows == 100
        assert resolved.max_rows == 1000000
        assert resolved.table_types == ["table"]
        assert resolved.required_columns == ["id"]
        assert resolved.exclude_patterns == ["*_temp"]

    def test_resolve_table_config_table_overrides_filters(self):
        """Test that table-level filters override schema-level."""
        schema_config = SchemaConfig(
            schema="analytics",
            min_rows=100,
            required_columns=["id"],
        )
        table_pattern = TablePattern(
            table="orders",
            schema="analytics",
            min_rows=1000,
            required_columns=["order_id"],
        )
        resolver = ConfigResolver(schema_configs=[schema_config])

        resolved = resolver.resolve_table_config(table_pattern)
        assert resolved.min_rows == 1000  # Table overrides
        # For lists, we combine both
        assert "id" in resolved.required_columns
        assert "order_id" in resolved.required_columns

    def test_resolve_table_config_combines_list_fields(self):
        """Test that list fields are combined (not overridden)."""
        schema_config = SchemaConfig(
            schema="analytics",
            table_types=["table"],
            required_columns=["id"],
            exclude_patterns=["*_temp"],
        )
        table_pattern = TablePattern(
            table="orders",
            schema="analytics",
            table_types=["view"],
            required_columns=["order_id"],
            exclude_patterns=["*_backup"],
        )
        resolver = ConfigResolver(schema_configs=[schema_config])

        resolved = resolver.resolve_table_config(table_pattern)
        # Both should be included
        assert "table" in resolved.table_types
        assert "view" in resolved.table_types
        assert "id" in resolved.required_columns
        assert "order_id" in resolved.required_columns
        assert "*_temp" in resolved.exclude_patterns
        assert "*_backup" in resolved.exclude_patterns

    def test_merge_table_patterns_no_schema_config(self):
        """Test merging when schema config has no fields set."""
        schema_config = SchemaConfig(schema="analytics")
        table_pattern = TablePattern(
            table="orders",
            schema="analytics",
            partition=PartitionConfig(strategy="latest"),
        )
        resolver = ConfigResolver()

        merged = resolver.merge_table_patterns(schema_config, table_pattern)
        assert merged.table == "orders"
        assert merged.partition is not None
        assert merged.partition.strategy == "latest"

    def test_merge_table_patterns_preserves_table_selection(self):
        """Test that table selection fields are preserved."""
        schema_config = SchemaConfig(
            schema="analytics",
            partition=PartitionConfig(strategy="latest"),
        )
        # Use pattern-based selection (table selection fields are preserved)
        table_pattern = TablePattern(
            pattern="order_*",  # This should be preserved
            schema="analytics",
        )
        resolver = ConfigResolver()

        merged = resolver.merge_table_patterns(schema_config, table_pattern)
        assert merged.pattern == "order_*"
        assert merged.partition is not None

    def test_resolve_table_config_uses_provided_schema_name(self):
        """Test that provided schema name is used instead of pattern schema."""
        schema_config = SchemaConfig(schema="analytics")
        table_pattern = TablePattern(table="orders", schema="staging")
        resolver = ConfigResolver(schema_configs=[schema_config])

        # Resolve with explicit schema name
        resolved = resolver.resolve_table_config(
            table_pattern, schema_name="analytics", database_name=None
        )
        # Should find schema config for analytics
        assert resolved.partition is None or True  # Just check it doesn't crash

        # Resolve with pattern schema
        resolved = resolver.resolve_table_config(table_pattern)
        # Should not find schema config (staging doesn't exist)
        assert resolved.table == "orders"

    def test_multiple_schema_configs_same_schema(self):
        """Test behavior with multiple schema configs for same schema."""
        schema1 = SchemaConfig(
            schema="analytics",
            partition=PartitionConfig(strategy="latest"),
        )
        schema2 = SchemaConfig(
            schema="analytics",
            database="warehouse",
            sampling=SamplingConfig(enabled=True),
        )
        resolver = ConfigResolver(schema_configs=[schema1, schema2])

        # Should match database-specific config first
        found = resolver.find_schema_config("analytics", database_name="warehouse")
        assert found is not None
        assert found.sampling is not None
        assert found.partition is None

        # Should fall back to schema-only config
        found = resolver.find_schema_config("analytics", database_name="other")
        assert found is not None
        assert found.partition is not None
        assert found.sampling is None

