"""Integration tests for database-level configurations."""

import pytest
from unittest.mock import MagicMock, Mock, patch

from baselinr.config.schema import (
    BaselinrConfig,
    ColumnAnomalyConfig,
    ColumnConfig,
    ColumnDriftConfig,
    ColumnProfilingConfig,
    ConnectionConfig,
    DatabaseConfig,
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


class TestDatabaseLevelConfigResolution:
    """Integration tests for database-level config resolution."""

    def test_database_config_merges_with_table_pattern(self):
        """Test that database configs are merged with table patterns."""
        database_config = DatabaseConfig(
            database="warehouse",
            partition=PartitionConfig(strategy="latest", key="date"),
            sampling=SamplingConfig(enabled=True, fraction=0.1),
        )
        table_pattern = TablePattern(
            table="orders", schema="analytics", database="warehouse"
        )

        resolver = ConfigResolver(database_configs=[database_config])
        resolved = resolver.resolve_table_config(table_pattern)

        assert resolved.partition is not None
        assert resolved.partition.strategy == "latest"
        assert resolved.sampling is not None
        assert resolved.sampling.enabled is True

    def test_table_overrides_database_config(self):
        """Test that table-level configs override database-level configs."""
        database_config = DatabaseConfig(
            database="warehouse",
            partition=PartitionConfig(strategy="latest", key="date"),
            sampling=SamplingConfig(enabled=True, fraction=0.1),
        )
        table_pattern = TablePattern(
            table="orders",
            schema="analytics",
            database="warehouse",
            partition=PartitionConfig(strategy="all"),
            sampling=SamplingConfig(enabled=False),
        )

        resolver = ConfigResolver(database_configs=[database_config])
        resolved = resolver.resolve_table_config(table_pattern)

        assert resolved.partition.strategy == "all"  # Table overrides
        assert resolved.sampling.enabled is False  # Table overrides

    def test_database_column_configs_merge_with_table_column_configs(self):
        """Test that database column configs merge with table column configs."""
        database_config = DatabaseConfig(
            database="warehouse",
            columns=[
                ColumnConfig(name="*_id", drift=ColumnDriftConfig(enabled=False)),
                ColumnConfig(
                    name="*_temp", profiling=ColumnProfilingConfig(enabled=False)
                ),
            ],
        )
        table_pattern = TablePattern(
            table="orders",
            schema="analytics",
            database="warehouse",
            columns=[
                ColumnConfig(name="total_amount", drift=ColumnDriftConfig(enabled=True)),
            ],
        )

        resolver = ConfigResolver(database_configs=[database_config])
        resolved = resolver.resolve_table_config(table_pattern)

        assert resolved.columns is not None
        assert len(resolved.columns) == 3

        # Table column should be first (checked first by ColumnMatcher)
        assert resolved.columns[0].name == "total_amount"
        assert resolved.columns[1].name == "*_id"
        assert resolved.columns[2].name == "*_temp"

    def test_table_column_config_overrides_database_column_config(self):
        """Test that table-level column config overrides database-level for same column."""
        database_config = DatabaseConfig(
            database="warehouse",
            columns=[
                ColumnConfig(name="total_amount", drift=ColumnDriftConfig(enabled=False)),
            ],
        )
        table_pattern = TablePattern(
            table="orders",
            schema="analytics",
            database="warehouse",
            columns=[
                ColumnConfig(name="total_amount", drift=ColumnDriftConfig(enabled=True)),
            ],
        )

        resolver = ConfigResolver(database_configs=[database_config])
        resolved = resolver.resolve_table_config(table_pattern)

        assert resolved.columns is not None
        assert len(resolved.columns) == 2

        # Table column config should be checked first
        column_matcher = ColumnMatcher(column_configs=resolved.columns)
        drift_config = column_matcher.get_column_drift_config("total_amount")
        assert drift_config is not None
        assert drift_config.drift is not None
        assert drift_config.drift.enabled is True  # Table config wins

    def test_database_schema_table_precedence(self):
        """Test that precedence is database → schema → table."""
        database_config = DatabaseConfig(
            database="warehouse",
            partition=PartitionConfig(strategy="all", key="date"),
            columns=[
                ColumnConfig(name="*_id", drift=ColumnDriftConfig(enabled=False)),
            ],
        )
        schema_config = SchemaConfig(
            schema="analytics",
            database="warehouse",
            partition=PartitionConfig(strategy="latest", key="timestamp"),
            columns=[
                ColumnConfig(
                    name="customer_id", drift=ColumnDriftConfig(enabled=True)
                ),  # Override for customer_id
            ],
        )
        table_pattern = TablePattern(
            table="orders",
            schema="analytics",
            database="warehouse",
            partition=PartitionConfig(strategy="all", key="created_at"),
            columns=[
                ColumnConfig(
                    name="customer_id",
                    drift=ColumnDriftConfig(enabled=False, thresholds={"low": 1.0}),
                ),  # Override again at table level
            ],
        )

        resolver = ConfigResolver(
            schema_configs=[schema_config], database_configs=[database_config]
        )
        resolved = resolver.resolve_table_config(table_pattern)

        # Table partition should override both database and schema
        assert resolved.partition.strategy == "all"
        assert resolved.partition.key == "created_at"

        # Column configs should be merged: table → schema → database
        assert resolved.columns is not None
        assert len(resolved.columns) == 3

        # Table column should be first
        assert resolved.columns[0].name == "customer_id"
        assert resolved.columns[0].drift is not None
        assert resolved.columns[0].drift.enabled is False

        # Schema column should be second
        assert resolved.columns[1].name == "customer_id"

        # Database column should be third
        assert resolved.columns[2].name == "*_id"

    def test_schema_overrides_database_config(self):
        """Test that schema-level configs override database-level configs."""
        database_config = DatabaseConfig(
            database="warehouse",
            partition=PartitionConfig(strategy="all", key="date"),
            sampling=SamplingConfig(enabled=True, fraction=0.1),
        )
        schema_config = SchemaConfig(
            schema="analytics",
            database="warehouse",
            partition=PartitionConfig(strategy="latest", key="timestamp"),
            sampling=SamplingConfig(enabled=True, fraction=0.05),
        )
        table_pattern = TablePattern(
            table="orders", schema="analytics", database="warehouse"
        )

        resolver = ConfigResolver(
            schema_configs=[schema_config], database_configs=[database_config]
        )
        resolved = resolver.resolve_table_config(table_pattern)

        # Schema should override database
        assert resolved.partition.strategy == "latest"
        assert resolved.partition.key == "timestamp"
        assert resolved.sampling.fraction == 0.05

    def test_database_config_applies_to_multiple_schemas(self):
        """Test that database config applies to all schemas in the database."""
        database_config = DatabaseConfig(
            database="warehouse",
            columns=[
                ColumnConfig(name="*_id", drift=ColumnDriftConfig(enabled=False)),
            ],
        )
        table_pattern1 = TablePattern(
            table="orders", schema="analytics", database="warehouse"
        )
        table_pattern2 = TablePattern(
            table="users", schema="marketing", database="warehouse"
        )

        resolver = ConfigResolver(database_configs=[database_config])

        resolved1 = resolver.resolve_table_config(table_pattern1)
        resolved2 = resolver.resolve_table_config(table_pattern2)

        # Both should have database-level column config
        assert resolved1.columns is not None
        assert len(resolved1.columns) == 1
        assert resolved1.columns[0].name == "*_id"

        assert resolved2.columns is not None
        assert len(resolved2.columns) == 1
        assert resolved2.columns[0].name == "*_id"

    def test_database_config_only_applies_to_specified_database(self):
        """Test that database config only applies to tables in that database."""
        database_config = DatabaseConfig(
            database="warehouse",
            partition=PartitionConfig(strategy="latest", key="date"),
        )
        table_pattern1 = TablePattern(
            table="orders", schema="analytics", database="warehouse"
        )
        table_pattern2 = TablePattern(
            table="orders", schema="analytics", database="other_db"
        )

        resolver = ConfigResolver(database_configs=[database_config])

        resolved1 = resolver.resolve_table_config(table_pattern1)
        resolved2 = resolver.resolve_table_config(table_pattern2)

        # First should have database config
        assert resolved1.partition is not None
        assert resolved1.partition.strategy == "latest"

        # Second should not have database config (different database)
        assert resolved2.partition is None

    def test_multi_level_column_config_precedence(self):
        """Test that column configs respect database → schema → table precedence."""
        database_config = DatabaseConfig(
            database="warehouse",
            columns=[
                ColumnConfig(
                    name="*_id",
                    drift=ColumnDriftConfig(enabled=False),  # Database: disable drift
                ),
            ],
        )
        schema_config = SchemaConfig(
            schema="analytics",
            database="warehouse",
            columns=[
                ColumnConfig(
                    name="customer_id",
                    drift=ColumnDriftConfig(enabled=True),  # Schema: enable for customer_id
                ),
            ],
        )
        table_pattern = TablePattern(
            table="orders",
            schema="analytics",
            database="warehouse",
            columns=[
                ColumnConfig(
                    name="customer_id",
                    drift=ColumnDriftConfig(
                        enabled=False, thresholds={"low": 1.0}
                    ),  # Table: disable with custom thresholds
                ),
            ],
        )

        resolver = ConfigResolver(
            schema_configs=[schema_config], database_configs=[database_config]
        )
        resolved = resolver.resolve_table_config(table_pattern)

        # Column matcher should check in order: table → schema → database
        column_matcher = ColumnMatcher(column_configs=resolved.columns)

        # Table config should win for customer_id
        drift_config = column_matcher.get_column_drift_config("customer_id")
        assert drift_config is not None
        assert drift_config.drift is not None
        assert drift_config.drift.enabled is False
        assert drift_config.drift.thresholds == {"low": 1.0}

        # Database config should apply to other *_id columns
        drift_config = column_matcher.get_column_drift_config("order_id")
        assert drift_config is not None
        assert drift_config.drift is not None
        assert drift_config.drift.enabled is False

    def test_no_database_config_falls_back_to_schema_table(self):
        """Test that resolution works when no database config exists."""
        schema_config = SchemaConfig(
            schema="analytics",
            partition=PartitionConfig(strategy="latest", key="date"),
        )
        table_pattern = TablePattern(
            table="orders", schema="analytics", database="warehouse"
        )

        resolver = ConfigResolver(schema_configs=[schema_config], database_configs=[])
        resolved = resolver.resolve_table_config(table_pattern)

        # Should still get schema config
        assert resolved.partition is not None
        assert resolved.partition.strategy == "latest"

