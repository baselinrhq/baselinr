"""Integration tests for schema-level configurations using datasets section."""

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


class TestSchemaLevelConfigResolution:
    """Integration tests for schema-level config resolution via datasets section."""

    def test_schema_config_merges_with_table_pattern(self):
        """Test that schema-level dataset configs are merged with table patterns."""
        schema_dataset = DatasetConfig(
            schema="analytics",
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
            datasets=DatasetsConfig(datasets=[schema_dataset]),
        )

        table_pattern = TablePattern(table="orders", schema="analytics")
        merger = ConfigMerger(config)
        merged = merger.merge_profiling_config(table_pattern)

        assert merged["partition"] is not None
        assert merged["partition"].strategy == "latest"
        assert merged["sampling"] is not None
        assert merged["sampling"].enabled is True

    def test_table_dataset_overrides_schema_dataset(self):
        """Test that table-level dataset configs override schema-level dataset configs."""
        schema_dataset = DatasetConfig(
            schema="analytics",
            profiling=DatasetProfilingConfig(
                partition=PartitionConfig(strategy="latest", key="date"),
                sampling=SamplingConfig(enabled=True, fraction=0.1),
            ),
        )
        table_dataset = DatasetConfig(
            table="orders",
            schema="analytics",
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
            datasets=DatasetsConfig(datasets=[schema_dataset, table_dataset]),
        )

        table_pattern = TablePattern(table="orders", schema="analytics")
        merger = ConfigMerger(config)
        merged = merger.merge_profiling_config(table_pattern)

        # Table-level dataset should win (more specific match)
        assert merged["partition"].strategy == "all"
        assert merged["sampling"].enabled is False

    def test_schema_column_configs_merge_with_table_column_configs(self):
        """Test that schema column configs merge with table column configs."""
        schema_dataset = DatasetConfig(
            schema="analytics",
            profiling=DatasetProfilingConfig(
                columns=[
                    ColumnConfig(name="*_id", drift=ColumnDriftConfig(enabled=False)),
                    ColumnConfig(name="*_metadata", profiling=ColumnProfilingConfig(enabled=False)),
                ],
            ),
        )
        table_dataset = DatasetConfig(
            table="orders",
            schema="analytics",
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
            datasets=DatasetsConfig(datasets=[schema_dataset, table_dataset]),
        )

        table_pattern = TablePattern(table="orders", schema="analytics")
        merger = ConfigMerger(config)
        merged = merger.merge_profiling_config(table_pattern)

        assert merged["columns"] is not None
        # Table-level dataset config wins (most specific match)
        assert len(merged["columns"]) == 1
        assert merged["columns"][0].name == "total_amount"

    def test_schema_config_applies_to_all_tables_in_schema(self):
        """Test that schema-level dataset config applies to multiple tables in same schema."""
        schema_dataset = DatasetConfig(
            schema="analytics",
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
            datasets=DatasetsConfig(datasets=[schema_dataset]),
        )

        table1 = TablePattern(table="orders", schema="analytics")
        table2 = TablePattern(table="customers", schema="analytics")

        merger = ConfigMerger(config)

        resolved1 = merger.merge_profiling_config(table1)
        resolved2 = merger.merge_profiling_config(table2)

        # Both should have schema column configs
        assert resolved1["columns"] is not None
        assert resolved2["columns"] is not None
        assert len(resolved1["columns"]) == 1
        assert len(resolved2["columns"]) == 1
        assert resolved1["columns"][0].name == "*_id"
        assert resolved2["columns"][0].name == "*_id"

    def test_schema_config_with_database_specificity(self):
        """Test that database-specific schema configs take precedence."""
        schema_generic = DatasetConfig(
            schema="analytics",
            profiling=DatasetProfilingConfig(
                sampling=SamplingConfig(enabled=True, fraction=0.1),
            ),
        )
        schema_specific = DatasetConfig(
            schema="analytics",
            database="warehouse",
            profiling=DatasetProfilingConfig(
                sampling=SamplingConfig(enabled=True, fraction=0.2),
            ),
        )
        config = BaselinrConfig(
            source=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
            storage=StorageConfig(
                connection=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
                results_table="results",
                runs_table="runs",
            ),
            datasets=DatasetsConfig(datasets=[schema_generic, schema_specific]),
        )

        merger = ConfigMerger(config)

        # With matching database
        table = TablePattern(table="orders", schema="analytics", database="warehouse")
        resolved = merger.merge_profiling_config(table)
        assert resolved["sampling"].fraction == 0.2  # Database-specific wins

        # Without matching database
        table2 = TablePattern(table="orders", schema="analytics", database="other")
        resolved2 = merger.merge_profiling_config(table2)
        assert resolved2["sampling"].fraction == 0.1  # Generic schema config


class TestSchemaLevelProfilingIntegration:
    """Integration tests for schema-level configs in profiling workflow."""

    @patch("baselinr.profiling.core.create_connector")
    def test_profiling_engine_uses_dataset_config(self, mock_create_connector):
        """Test that ProfileEngine uses dataset configs from datasets section."""
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

        # Create config with schema-level dataset config
        schema_dataset = DatasetConfig(
            schema="analytics",
            profiling=DatasetProfilingConfig(
                columns=[
                    ColumnConfig(name="*_metadata", profiling=ColumnProfilingConfig(enabled=False)),
                ],
            ),
        )
        table_pattern = TablePattern(
            table="orders",
            schema="analytics",
        )

        profiling_config = ProfilingConfig(tables=[table_pattern])

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
            datasets=DatasetsConfig(datasets=[schema_dataset]),
        )

        engine = ProfileEngine(config)

        # Verify that datasets are configured
        assert engine.config.datasets is not None
        assert len(engine.config.datasets.datasets) == 1
        assert engine.config.datasets.datasets[0].schema_ == "analytics"
