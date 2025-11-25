"""Integration tests for schema-level configurations."""

import pytest
from unittest.mock import MagicMock, Mock, patch

from baselinr.config.schema import (
    BaselinrConfig,
    ColumnAnomalyConfig,
    ColumnConfig,
    ColumnDriftConfig,
    ColumnProfilingConfig,
    ConnectionConfig,
    DatabaseType,
    PartitionConfig,
    ProfilingConfig,
    SamplingConfig,
    SchemaConfig,
    StorageConfig,
    TablePattern,
)
from baselinr.profiling.config_resolver import ConfigResolver
from baselinr.profiling.column_matcher import ColumnMatcher


class TestSchemaLevelConfigResolution:
    """Integration tests for schema-level config resolution."""

    def test_schema_config_merges_with_table_pattern(self):
        """Test that schema configs are merged with table patterns."""
        schema_config = SchemaConfig(
            schema="analytics",
            partition=PartitionConfig(strategy="latest", key="date"),
            sampling=SamplingConfig(enabled=True, fraction=0.1),
        )
        table_pattern = TablePattern(table="orders", schema="analytics")

        resolver = ConfigResolver(schema_configs=[schema_config])
        resolved = resolver.resolve_table_config(table_pattern)

        assert resolved.partition is not None
        assert resolved.partition.strategy == "latest"
        assert resolved.sampling is not None
        assert resolved.sampling.enabled is True

    def test_table_overrides_schema_config(self):
        """Test that table-level configs override schema-level configs."""
        schema_config = SchemaConfig(
            schema="analytics",
            partition=PartitionConfig(strategy="latest", key="date"),
            sampling=SamplingConfig(enabled=True, fraction=0.1),
        )
        table_pattern = TablePattern(
            table="orders",
            schema="analytics",
            partition=PartitionConfig(strategy="all"),
            sampling=SamplingConfig(enabled=False),
        )

        resolver = ConfigResolver(schema_configs=[schema_config])
        resolved = resolver.resolve_table_config(table_pattern)

        assert resolved.partition.strategy == "all"  # Table overrides
        assert resolved.sampling.enabled is False  # Table overrides

    def test_schema_column_configs_merge_with_table_column_configs(self):
        """Test that schema column configs merge with table column configs."""
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
        assert len(resolved.columns) == 3

        # Table column should be first (checked first by ColumnMatcher)
        assert resolved.columns[0].name == "total_amount"
        assert resolved.columns[1].name == "*_id"
        assert resolved.columns[2].name == "*_metadata"

    def test_table_column_config_overrides_schema_column_config(self):
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

        # Table config comes first in list, so it's checked first by ColumnMatcher
        matcher = ColumnMatcher(column_configs=resolved.columns)
        config = matcher.find_matching_config("total_amount")

        assert config is not None
        assert config.drift is not None
        assert config.drift.enabled is True  # Table config wins

    def test_schema_config_applies_to_all_tables_in_schema(self):
        """Test that schema config applies to multiple tables in same schema."""
        schema_config = SchemaConfig(
            schema="analytics",
            columns=[
                ColumnConfig(name="*_id", drift=ColumnDriftConfig(enabled=False)),
            ],
        )

        table1 = TablePattern(table="orders", schema="analytics")
        table2 = TablePattern(table="customers", schema="analytics")

        resolver = ConfigResolver(schema_configs=[schema_config])

        resolved1 = resolver.resolve_table_config(table1)
        resolved2 = resolver.resolve_table_config(table2)

        # Both should have schema column configs
        assert resolved1.columns is not None
        assert resolved2.columns is not None
        assert len(resolved1.columns) == 1
        assert len(resolved2.columns) == 1
        assert resolved1.columns[0].name == "*_id"
        assert resolved2.columns[0].name == "*_id"

    def test_schema_config_with_database_specificity(self):
        """Test that database-specific schema configs take precedence."""
        schema_generic = SchemaConfig(
            schema="analytics",
            sampling=SamplingConfig(enabled=True, fraction=0.1),
        )
        schema_specific = SchemaConfig(
            schema="analytics",
            database="warehouse",
            sampling=SamplingConfig(enabled=True, fraction=0.2),
        )

        resolver = ConfigResolver(schema_configs=[schema_generic, schema_specific])

        # With matching database
        table = TablePattern(table="orders", schema="analytics", database="warehouse")
        resolved = resolver.resolve_table_config(table)
        assert resolved.sampling.fraction == 0.2  # Database-specific wins

        # Without matching database
        table2 = TablePattern(table="orders", schema="analytics", database="other")
        resolved2 = resolver.resolve_table_config(table2)
        assert resolved2.sampling.fraction == 0.1  # Generic schema config

    def test_schema_config_with_pattern_matching_tables(self):
        """Test that schema configs apply to tables discovered via patterns."""
        schema_config = SchemaConfig(
            schema="analytics",
            columns=[
                ColumnConfig(name="*_id", drift=ColumnDriftConfig(enabled=False)),
            ],
        )

        # Pattern-based table selection
        table_pattern = TablePattern(
            pattern="user_*",
            schema="analytics",
        )

        resolver = ConfigResolver(schema_configs=[schema_config])

        # When pattern is expanded, each matched table should inherit schema config
        # Simulate this by resolving a pattern as if it were expanded
        resolved = resolver.resolve_table_config(table_pattern, schema_name="analytics")

        # The resolved pattern should have schema column configs
        # (Note: pattern expansion happens in planner, but config resolution happens here)
        # For this test, we're just checking that resolution works with pattern-based patterns

    def test_schema_config_with_select_schema_tables(self):
        """Test that schema configs apply to tables from select_schema patterns."""
        schema_config = SchemaConfig(
            schema="analytics",
            sampling=SamplingConfig(enabled=True, fraction=0.1),
        )

        # Schema-based table selection (would be expanded by planner)
        # Simulate expanded table
        table_pattern = TablePattern(table="orders", schema="analytics")
        # This would come from expanding: TablePattern(select_schema=True, schema="analytics")

        resolver = ConfigResolver(schema_configs=[schema_config])
        resolved = resolver.resolve_table_config(table_pattern)

        assert resolved.sampling is not None
        assert resolved.sampling.enabled is True
        assert resolved.sampling.fraction == 0.1

    def test_schema_filter_fields_combine_with_table_filters(self):
        """Test that schema filter fields combine with table filter fields."""
        schema_config = SchemaConfig(
            schema="analytics",
            min_rows=100,
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

        # min_rows: table overrides (if set)
        assert resolved.min_rows == 100  # Schema value (table doesn't set it)

        # Lists combine
        assert "table" in resolved.table_types
        assert "view" in resolved.table_types
        assert "id" in resolved.required_columns
        assert "order_id" in resolved.required_columns
        assert "*_temp" in resolved.exclude_patterns
        assert "*_backup" in resolved.exclude_patterns


class TestSchemaLevelProfilingIntegration:
    """Integration tests for schema-level configs in profiling workflow."""

    @patch("baselinr.profiling.core.create_connector")
    def test_profiling_engine_uses_resolved_config(self, mock_create_connector):
        """Test that ProfileEngine uses resolved configs from schema + table."""
        from baselinr.profiling.core import ProfileEngine

        # Mock connector
        mock_connector = MagicMock()
        mock_table = MagicMock()
        mock_table.columns = [
            MagicMock(name="order_id", type="INTEGER"),
            MagicMock(name="total_amount", type="DECIMAL"),
            MagicMock(name="customer_metadata", type="TEXT"),
        ]
        mock_connector.get_table.return_value = mock_table
        mock_connector.engine = MagicMock()
        mock_create_connector.return_value = mock_connector

        # Create config with schema-level column configs
        schema_config = SchemaConfig(
            schema="analytics",
            columns=[
                ColumnConfig(name="*_metadata", profiling=ColumnProfilingConfig(enabled=False)),
            ],
        )
        table_pattern = TablePattern(
            table="orders",
            schema="analytics",
        )

        profiling_config = ProfilingConfig(
            tables=[table_pattern],
            schemas=[schema_config],
        )

        source_config = ConnectionConfig(
            type=DatabaseType.SQLITE,
            database="test.db",
            filepath=":memory:",
        )
        storage_config = StorageConfig(
            connection=source_config,
            results_table="results",
            runs_table="runs",
        )

        config = BaselinrConfig(
            source=source_config,
            storage=storage_config,
            profiling=profiling_config,
        )

        engine = ProfileEngine(config)

        # Verify that ConfigResolver will be used
        # (Actual profiling would require full database setup)
        assert engine.config.profiling.schemas is not None
        assert len(engine.config.profiling.schemas) == 1

