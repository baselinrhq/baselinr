"""Integration tests for database-level configurations using datasets section."""

import pytest
from unittest.mock import MagicMock, Mock, patch

from baselinr.config.merger import ConfigMerger
from baselinr.config.schema import (
    BaselinrConfig,
    ColumnAnomalyConfig,
    ColumnConfig,
    ColumnDriftConfig,
    ColumnProfilingConfig,
    ConnectionConfig,
    DatabaseType,
    DatasetConfig,
    DatasetProfilingConfig,
    DatasetsConfig,
    PartitionConfig,
    ProfilingConfig,
    SamplingConfig,
    StorageConfig,
    TablePattern,
)
from baselinr.profiling.column_matcher import ColumnMatcher


class TestDatabaseLevelConfigResolution:
    """Integration tests for database-level config resolution via datasets section."""

    def test_database_config_merges_with_table_pattern(self):
        """Test that database-level dataset configs are merged with table patterns."""
        database_dataset = DatasetConfig(
            database="warehouse",
            profiling=DatasetProfilingConfig(
                partition=PartitionConfig(strategy="latest", key="date"),
                sampling=SamplingConfig(enabled=True, fraction=0.1),
            ),
        )
        config = BaselinrConfig(
            source=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
            storage=StorageConfig(
                connection=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
                results_table="results",
                runs_table="runs",
            ),
            datasets=DatasetsConfig(datasets=[database_dataset]),
        )

        table_pattern = TablePattern(
            table="orders", schema="analytics", database="warehouse"
        )
        merger = ConfigMerger(config)
        merged = merger.merge_profiling_config(table_pattern)

        assert merged["partition"] is not None
        assert merged["partition"].strategy == "latest"
        assert merged["sampling"] is not None
        assert merged["sampling"].enabled is True

    def test_table_dataset_overrides_database_dataset(self):
        """Test that table-level dataset configs override database-level dataset configs."""
        database_dataset = DatasetConfig(
            database="warehouse",
            profiling=DatasetProfilingConfig(
                partition=PartitionConfig(strategy="latest", key="date"),
                sampling=SamplingConfig(enabled=True, fraction=0.1),
            ),
        )
        table_dataset = DatasetConfig(
            table="orders",
            schema="analytics",
            database="warehouse",
            profiling=DatasetProfilingConfig(
                partition=PartitionConfig(strategy="all"),
                sampling=SamplingConfig(enabled=False),
            ),
        )
        config = BaselinrConfig(
            source=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
            storage=StorageConfig(
                connection=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
                results_table="results",
                runs_table="runs",
            ),
            datasets=DatasetsConfig(datasets=[database_dataset, table_dataset]),
        )

        table_pattern = TablePattern(
            table="orders",
            schema="analytics",
            database="warehouse",
        )
        merger = ConfigMerger(config)
        merged = merger.merge_profiling_config(table_pattern)

        # Table-level dataset should win (more specific match)
        assert merged["partition"].strategy == "all"
        assert merged["sampling"].enabled is False

    def test_database_column_configs_merge_with_table_column_configs(self):
        """Test that database column configs merge with table column configs."""
        database_dataset = DatasetConfig(
            database="warehouse",
            profiling=DatasetProfilingConfig(
                columns=[
                    ColumnConfig(name="*_id", drift=ColumnDriftConfig(enabled=False)),
                    ColumnConfig(
                        name="*_temp", profiling=ColumnProfilingConfig(enabled=False)
                    ),
                ],
            ),
        )
        table_dataset = DatasetConfig(
            table="orders",
            schema="analytics",
            database="warehouse",
            profiling=DatasetProfilingConfig(
                columns=[
                    ColumnConfig(name="total_amount", drift=ColumnDriftConfig(enabled=True)),
                ],
            ),
        )
        config = BaselinrConfig(
            source=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
            storage=StorageConfig(
                connection=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
                results_table="results",
                runs_table="runs",
            ),
            datasets=DatasetsConfig(datasets=[database_dataset, table_dataset]),
        )

        table_pattern = TablePattern(
            table="orders",
            schema="analytics",
            database="warehouse",
        )
        merger = ConfigMerger(config)
        merged = merger.merge_profiling_config(table_pattern)

        assert merged["columns"] is not None
        assert len(merged["columns"]) == 1  # Table dataset columns only (table-level wins)

        # Table dataset columns should be returned
        assert merged["columns"][0].name == "total_amount"

    def test_database_schema_table_precedence(self):
        """Test that precedence is database → schema → table (most specific wins)."""
        database_dataset = DatasetConfig(
            database="warehouse",
            profiling=DatasetProfilingConfig(
                partition=PartitionConfig(strategy="all", key="date"),
                columns=[
                    ColumnConfig(name="*_id", drift=ColumnDriftConfig(enabled=False)),
                ],
            ),
        )
        schema_dataset = DatasetConfig(
            schema="analytics",
            database="warehouse",
            profiling=DatasetProfilingConfig(
                partition=PartitionConfig(strategy="latest", key="timestamp"),
                columns=[
                    ColumnConfig(
                        name="customer_id", drift=ColumnDriftConfig(enabled=True)
                    ),
                ],
            ),
        )
        table_dataset = DatasetConfig(
            table="orders",
            schema="analytics",
            database="warehouse",
            profiling=DatasetProfilingConfig(
                partition=PartitionConfig(strategy="all", key="created_at"),
                columns=[
                    ColumnConfig(
                        name="customer_id",
                        drift=ColumnDriftConfig(enabled=False, thresholds={"low": 1.0}),
                    ),
                ],
            ),
        )
        config = BaselinrConfig(
            source=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
            storage=StorageConfig(
                connection=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
                results_table="results",
                runs_table="runs",
            ),
            datasets=DatasetsConfig(datasets=[database_dataset, schema_dataset, table_dataset]),
        )

        table_pattern = TablePattern(
            table="orders",
            schema="analytics",
            database="warehouse",
        )
        merger = ConfigMerger(config)
        merged = merger.merge_profiling_config(table_pattern)

        # Table-level dataset should win (most specific match)
        assert merged["partition"].strategy == "all"
        assert merged["partition"].key == "created_at"

        # Table dataset columns should be returned
        assert merged["columns"] is not None
        assert len(merged["columns"]) == 1
        assert merged["columns"][0].name == "customer_id"
        assert merged["columns"][0].drift.enabled is False

    def test_schema_dataset_overrides_database_dataset(self):
        """Test that schema-level dataset configs override database-level dataset configs."""
        database_dataset = DatasetConfig(
            database="warehouse",
            profiling=DatasetProfilingConfig(
                partition=PartitionConfig(strategy="all", key="date"),
                sampling=SamplingConfig(enabled=True, fraction=0.1),
            ),
        )
        schema_dataset = DatasetConfig(
            schema="analytics",
            database="warehouse",
            profiling=DatasetProfilingConfig(
                partition=PartitionConfig(strategy="latest", key="timestamp"),
                sampling=SamplingConfig(enabled=True, fraction=0.05),
            ),
        )
        config = BaselinrConfig(
            source=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
            storage=StorageConfig(
                connection=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
                results_table="results",
                runs_table="runs",
            ),
            datasets=DatasetsConfig(datasets=[database_dataset, schema_dataset]),
        )

        table_pattern = TablePattern(
            table="orders", schema="analytics", database="warehouse"
        )
        merger = ConfigMerger(config)
        merged = merger.merge_profiling_config(table_pattern)

        # Schema-level dataset should win (more specific than database)
        assert merged["partition"].strategy == "latest"
        assert merged["partition"].key == "timestamp"
        assert merged["sampling"].fraction == 0.05

    def test_database_config_applies_to_multiple_schemas(self):
        """Test that database-level dataset config applies to all schemas in the database."""
        database_dataset = DatasetConfig(
            database="warehouse",
            profiling=DatasetProfilingConfig(
                columns=[
                    ColumnConfig(name="*_id", drift=ColumnDriftConfig(enabled=False)),
                ],
            ),
        )
        config = BaselinrConfig(
            source=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
            storage=StorageConfig(
                connection=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
                results_table="results",
                runs_table="runs",
            ),
            datasets=DatasetsConfig(datasets=[database_dataset]),
        )

        table_pattern1 = TablePattern(
            table="orders", schema="analytics", database="warehouse"
        )
        table_pattern2 = TablePattern(
            table="users", schema="marketing", database="warehouse"
        )

        merger = ConfigMerger(config)

        merged1 = merger.merge_profiling_config(table_pattern1)
        merged2 = merger.merge_profiling_config(table_pattern2)

        # Both should have database-level column config
        assert merged1["columns"] is not None
        assert len(merged1["columns"]) == 1
        assert merged1["columns"][0].name == "*_id"

        assert merged2["columns"] is not None
        assert len(merged2["columns"]) == 1
        assert merged2["columns"][0].name == "*_id"

    def test_database_config_only_applies_to_specified_database(self):
        """Test that database-level dataset config only applies to tables in that database."""
        database_dataset = DatasetConfig(
            database="warehouse",
            profiling=DatasetProfilingConfig(
                partition=PartitionConfig(strategy="latest", key="date"),
            ),
        )
        config = BaselinrConfig(
            source=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
            storage=StorageConfig(
                connection=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
                results_table="results",
                runs_table="runs",
            ),
            datasets=DatasetsConfig(datasets=[database_dataset]),
        )

        table_pattern1 = TablePattern(
            table="orders", schema="analytics", database="warehouse"
        )
        table_pattern2 = TablePattern(
            table="orders", schema="analytics", database="other_db"
        )

        merger = ConfigMerger(config)

        merged1 = merger.merge_profiling_config(table_pattern1)
        merged2 = merger.merge_profiling_config(table_pattern2)

        # First should have database config
        assert merged1["partition"] is not None
        assert merged1["partition"].strategy == "latest"

        # Second should not have database config (different database)
        assert merged2["partition"] is None

    def test_no_database_config_falls_back_to_schema(self):
        """Test that resolution works when no database-level dataset config exists."""
        schema_dataset = DatasetConfig(
            schema="analytics",
            profiling=DatasetProfilingConfig(
                partition=PartitionConfig(strategy="latest", key="date"),
            ),
        )
        config = BaselinrConfig(
            source=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
            storage=StorageConfig(
                connection=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
                results_table="results",
                runs_table="runs",
            ),
            datasets=DatasetsConfig(datasets=[schema_dataset]),
        )

        table_pattern = TablePattern(
            table="orders", schema="analytics", database="warehouse"
        )
        merger = ConfigMerger(config)
        merged = merger.merge_profiling_config(table_pattern)

        # Should still get schema config
        assert merged["partition"] is not None
        assert merged["partition"].strategy == "latest"
