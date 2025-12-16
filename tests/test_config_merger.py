"""Tests for configuration merger module."""

import pytest

from baselinr.config.merger import ConfigMerger
from baselinr.config.schema import (
    BaselinrConfig,
    ColumnAnomalyConfig,
    ColumnConfig,
    ColumnDriftConfig,
    ColumnProfilingConfig,
    ColumnValidationConfig,
    ConnectionConfig,
    DatabaseType,
    DatasetAnomalyConfig,
    DatasetConfig,
    DatasetDriftConfig,
    DatasetProfilingConfig,
    DatasetValidationConfig,
    DatasetsConfig,
    DriftDetectionConfig,
    PartitionConfig,
    ProfilingConfig,
    SamplingConfig,
    StorageConfig,
    TablePattern,
    ValidationConfig,
    ValidationRuleConfig,
)


@pytest.fixture
def base_config():
    """Create a base BaselinrConfig for testing."""
    return BaselinrConfig(
        environment="test",
        source=ConnectionConfig(
            type=DatabaseType.SQLITE,
            database=":memory:",
            filepath=":memory:",
        ),
        storage=StorageConfig(
            connection=ConnectionConfig(
                type=DatabaseType.SQLITE,
                database=":memory:",
                filepath=":memory:",
            ),
            results_table="baselinr_results",
            runs_table="baselinr_runs",
        ),
        profiling=ProfilingConfig(),
        drift_detection=DriftDetectionConfig(strategy="absolute_threshold"),
    )


class TestConfigMerger:
    """Tests for ConfigMerger."""

    def test_find_matching_dataset_exact_match(self, base_config):
        """Test finding dataset with exact match."""
        dataset = DatasetConfig(
            database="warehouse",
            schema="analytics",
            table="customers",
            profiling=DatasetProfilingConfig(
                partition=PartitionConfig(strategy="latest", key="date")
            ),
        )
        base_config.datasets = DatasetsConfig(datasets=[dataset])
        merger = ConfigMerger(base_config)

        found = merger.find_matching_dataset("warehouse", "analytics", "customers")
        assert found is not None
        assert found.table == "customers"

    def test_find_matching_dataset_no_match(self, base_config):
        """Test finding dataset when no match exists."""
        dataset = DatasetConfig(
            database="warehouse",
            schema="analytics",
            table="customers",
        )
        base_config.datasets = DatasetsConfig(datasets=[dataset])
        merger = ConfigMerger(base_config)

        found = merger.find_matching_dataset("warehouse", "analytics", "orders")
        assert found is None

    def test_find_matching_dataset_wildcard_database(self, base_config):
        """Test finding dataset with None database (wildcard)."""
        dataset = DatasetConfig(
            database=None,
            schema="analytics",
            table="customers",
        )
        base_config.datasets = DatasetsConfig(datasets=[dataset])
        merger = ConfigMerger(base_config)

        # Should match any database
        found = merger.find_matching_dataset("warehouse", "analytics", "customers")
        assert found is not None
        found = merger.find_matching_dataset("other_db", "analytics", "customers")
        assert found is not None

    def test_find_matching_dataset_wildcard_schema(self, base_config):
        """Test finding dataset with None schema (wildcard)."""
        dataset = DatasetConfig(
            database="warehouse",
            schema=None,
            table="customers",
        )
        base_config.datasets = DatasetsConfig(datasets=[dataset])
        merger = ConfigMerger(base_config)

        # Should match any schema
        found = merger.find_matching_dataset("warehouse", "analytics", "customers")
        assert found is not None
        found = merger.find_matching_dataset("warehouse", "public", "customers")
        assert found is not None

    def test_find_matching_dataset_wildcard_table(self, base_config):
        """Test finding dataset with None table (wildcard)."""
        dataset = DatasetConfig(
            database="warehouse",
            schema="analytics",
            table=None,
        )
        base_config.datasets = DatasetsConfig(datasets=[dataset])
        merger = ConfigMerger(base_config)

        # Should match any table in that schema
        found = merger.find_matching_dataset("warehouse", "analytics", "customers")
        assert found is not None
        found = merger.find_matching_dataset("warehouse", "analytics", "orders")
        assert found is not None

    def test_merge_profiling_config_no_dataset(self, base_config):
        """Test merging profiling config when no dataset matches."""
        table_pattern = TablePattern(table="customers", schema="analytics")
        merger = ConfigMerger(base_config)

        merged = merger.merge_profiling_config(table_pattern)
        # Should return dict with None values
        assert isinstance(merged, dict)
        assert merged["partition"] is None
        assert merged["sampling"] is None
        assert merged["columns"] is None

    def test_merge_profiling_config_with_dataset_partition(self, base_config):
        """Test merging profiling config with dataset partition override."""
        dataset = DatasetConfig(
            database="warehouse",
            schema="analytics",
            table="customers",
            profiling=DatasetProfilingConfig(
                partition=PartitionConfig(strategy="latest", key="date")
            ),
        )
        base_config.datasets = DatasetsConfig(datasets=[dataset])
        merger = ConfigMerger(base_config)

        table_pattern = TablePattern(table="customers", schema="analytics", database="warehouse")
        merged = merger.merge_profiling_config(table_pattern)

        assert isinstance(merged, dict)
        assert merged["partition"] is not None
        assert merged["partition"].strategy == "latest"
        assert merged["partition"].key == "date"

    def test_merge_profiling_config_table_overrides_dataset(self, base_config):
        """Test that dataset config is returned (table pattern no longer has profiling fields)."""
        dataset = DatasetConfig(
            database="warehouse",
            schema="analytics",
            table="customers",
            profiling=DatasetProfilingConfig(
                partition=PartitionConfig(strategy="latest", key="date")
            ),
        )
        base_config.datasets = DatasetsConfig(datasets=[dataset])
        merger = ConfigMerger(base_config)

        # Table pattern no longer has partition field
        table_pattern = TablePattern(
            table="customers",
            schema="analytics",
            database="warehouse",
        )
        merged = merger.merge_profiling_config(table_pattern)

        # Dataset config should be returned
        assert isinstance(merged, dict)
        assert merged["partition"] is not None
        assert merged["partition"].strategy == "latest"
        assert merged["partition"].key == "date"

    def test_merge_profiling_config_with_dataset_sampling(self, base_config):
        """Test merging profiling config with dataset sampling override."""
        dataset = DatasetConfig(
            database="warehouse",
            schema="analytics",
            table="customers",
            profiling=DatasetProfilingConfig(
                sampling=SamplingConfig(enabled=True, fraction=0.1)
            ),
        )
        base_config.datasets = DatasetsConfig(datasets=[dataset])
        merger = ConfigMerger(base_config)

        table_pattern = TablePattern(table="customers", schema="analytics", database="warehouse")
        merged = merger.merge_profiling_config(table_pattern)

        assert isinstance(merged, dict)
        assert merged["sampling"] is not None
        assert merged["sampling"].enabled is True
        assert merged["sampling"].fraction == 0.1

    def test_merge_profiling_config_with_dataset_columns(self, base_config):
        """Test merging profiling config with dataset column configs."""
        dataset = DatasetConfig(
            database="warehouse",
            schema="analytics",
            table="customers",
            columns=[
                ColumnConfig(name="email", drift=ColumnDriftConfig(enabled=False)),
            ],
        )
        base_config.datasets = DatasetsConfig(datasets=[dataset])
        merger = ConfigMerger(base_config)

        # Table pattern no longer has columns field
        table_pattern = TablePattern(
            table="customers",
            schema="analytics",
            database="warehouse",
        )
        merged = merger.merge_profiling_config(table_pattern)

        assert isinstance(merged, dict)
        assert merged["columns"] is not None
        assert len(merged["columns"]) == 1
        # Dataset columns are returned
        assert merged["columns"][0].name == "email"

    def test_merge_drift_config_no_dataset(self, base_config):
        """Test merging drift config when no dataset matches."""
        merger = ConfigMerger(base_config)

        merged = merger.merge_drift_config("warehouse", "analytics", "customers")
        assert merged is not None
        assert merged.strategy == "absolute_threshold"

    def test_merge_drift_config_with_dataset_strategy(self, base_config):
        """Test merging drift config with dataset strategy override."""
        dataset = DatasetConfig(
            database="warehouse",
            schema="analytics",
            table="customers",
            drift=DatasetDriftConfig(strategy="statistical"),
        )
        base_config.datasets = DatasetsConfig(datasets=[dataset])
        merger = ConfigMerger(base_config)

        merged = merger.merge_drift_config("warehouse", "analytics", "customers")
        assert merged is not None
        assert merged.strategy == "statistical"

    def test_merge_drift_config_with_dataset_thresholds(self, base_config):
        """Test merging drift config with dataset threshold overrides."""
        dataset = DatasetConfig(
            database="warehouse",
            schema="analytics",
            table="customers",
            drift=DatasetDriftConfig(
                absolute_threshold={"low_threshold": 3.0, "medium_threshold": 10.0, "high_threshold": 25.0}
            ),
        )
        base_config.datasets = DatasetsConfig(datasets=[dataset])
        merger = ConfigMerger(base_config)

        merged = merger.merge_drift_config("warehouse", "analytics", "customers")
        assert merged is not None
        assert merged.absolute_threshold["low_threshold"] == 3.0
        assert merged.absolute_threshold["medium_threshold"] == 10.0
        assert merged.absolute_threshold["high_threshold"] == 25.0

    def test_get_validation_rules_no_dataset(self, base_config):
        """Test getting validation rules when no dataset matches."""
        # Rules must be in datasets section, not validation.rules[]
        # Global rules can be in a dataset with no table/schema/database (all None)
        # Column-specific rules should be in columns[].validation.rules (Phase 3.5)
        global_dataset = DatasetConfig(
            columns=[
                ColumnConfig(
                    name="customer_id",
                    validation=ColumnValidationConfig(
                        rules=[
                            ValidationRuleConfig(
                                type="not_null", severity="high"
                            )
                        ]
                    )
                )
            ]
        )
        base_config.datasets = DatasetsConfig(datasets=[global_dataset])
        merger = ConfigMerger(base_config)

        rules = merger.get_validation_rules("warehouse", "analytics", "customers")
        # Global column rules should be returned
        assert len(rules) == 1
        assert rules[0].type == "not_null"
        assert rules[0].column == "customer_id"

    def test_get_validation_rules_with_dataset(self, base_config):
        """Test getting validation rules with dataset-specific rules."""
        # Global rules in a dataset with no table/schema/database (all None)
        # Column-specific rules should be in columns[].validation.rules (Phase 3.5)
        global_dataset = DatasetConfig(
            columns=[
                ColumnConfig(
                    name="customer_id",
                    validation=ColumnValidationConfig(
                        rules=[
                            ValidationRuleConfig(
                                type="not_null", severity="high"
                            )
                        ]
                    )
                )
            ]
        )
        # Dataset-specific rules
        dataset = DatasetConfig(
            database="warehouse",
            schema="analytics",
            table="customers",
            columns=[
                ColumnConfig(
                    name="email",
                    validation=ColumnValidationConfig(
                        rules=[
                            ValidationRuleConfig(
                                type="format",
                                pattern="^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
                                severity="high",
                            )
                        ]
                    )
                )
            ],
        )
        base_config.datasets = DatasetsConfig(datasets=[global_dataset, dataset])
        merger = ConfigMerger(base_config)

        rules = merger.get_validation_rules("warehouse", "analytics", "customers")
        # Should have both global and dataset rules
        assert len(rules) == 2
        rule_types = [r.type for r in rules]
        assert "not_null" in rule_types
        assert "format" in rule_types

    def test_get_validation_rules_dataset_sets_table(self, base_config):
        """Test that dataset validation rules get table name set if not provided."""
        dataset = DatasetConfig(
            database="warehouse",
            schema="analytics",
            table="customers",
            validation=DatasetValidationConfig(
                rules=[
                    ValidationRuleConfig(
                        type="format",
                        column="email",
                        pattern="^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
                        severity="high",
                    )
                ]
            ),
        )
        base_config.datasets = DatasetsConfig(datasets=[dataset])
        merger = ConfigMerger(base_config)

        rules = merger.get_validation_rules("warehouse", "analytics", "customers")
        assert len(rules) == 1
        assert rules[0].table == "customers"  # Should be set from dataset

    def test_get_anomaly_column_configs(self, base_config):
        """Test getting anomaly column configs from dataset."""
        dataset = DatasetConfig(
            database="warehouse",
            schema="analytics",
            table="customers",
            columns=[
                ColumnConfig(
                    name="total_amount",
                    anomaly=ColumnAnomalyConfig(
                        enabled=True, methods=["control_limits", "iqr"]
                    ),
                )
            ],
        )
        base_config.datasets = DatasetsConfig(datasets=[dataset])
        merger = ConfigMerger(base_config)

        configs = merger.get_anomaly_column_configs("warehouse", "analytics", "customers")
        assert len(configs) == 1
        assert configs[0].name == "total_amount"

    def test_get_drift_column_configs(self, base_config):
        """Test getting drift column configs from dataset."""
        dataset = DatasetConfig(
            database="warehouse",
            schema="analytics",
            table="customers",
            columns=[
                ColumnConfig(
                    name="email",
                    drift=ColumnDriftConfig(enabled=False),
                )
            ],
        )
        base_config.datasets = DatasetsConfig(datasets=[dataset])
        merger = ConfigMerger(base_config)

        configs = merger.get_drift_column_configs("warehouse", "analytics", "customers")
        assert len(configs) == 1
        assert configs[0].name == "email"
        assert configs[0].drift is not None
        assert configs[0].drift.enabled is False

    def test_resolve_table_config_complete(self, base_config):
        """Test resolving complete table config with all features."""
        dataset = DatasetConfig(
            database="warehouse",
            schema="analytics",
            table="customers",
            profiling=DatasetProfilingConfig(
                partition=PartitionConfig(strategy="latest", key="date")
            ),
            drift=DatasetDriftConfig(strategy="statistical"),
            validation=DatasetValidationConfig(
                rules=[
                    ValidationRuleConfig(
                        type="not_null", table="customers", column="customer_id", severity="high"
                    )
                ]
            ),
        )
        base_config.datasets = DatasetsConfig(datasets=[dataset])
        merger = ConfigMerger(base_config)

        table_pattern = TablePattern(table="customers", schema="analytics", database="warehouse")
        resolved = merger.resolve_table_config(table_pattern)

        assert resolved["profiling"]["partition"] is not None
        assert resolved["profiling"]["partition"].strategy == "latest"
        assert resolved["drift"].strategy == "statistical"
        assert len(resolved["validation_rules"]) == 1

    def test_merger_without_config(self):
        """Test merger initialization without config."""
        merger = ConfigMerger(None)
        assert merger.config is None
        assert merger.datasets == []

    def test_merger_with_empty_datasets(self, base_config):
        """Test merger with empty datasets."""
        base_config.datasets = DatasetsConfig(datasets=[])
        merger = ConfigMerger(base_config)

        found = merger.find_matching_dataset("warehouse", "analytics", "customers")
        assert found is None

    def test_dataset_config_validation_requires_identifier(self):
        """Test that DatasetConfig requires at least one identifier."""
        with pytest.raises(ValueError, match="must specify at least one of"):
            DatasetConfig()

    def test_dataset_config_validation_allows_database_only(self):
        """Test that DatasetConfig allows database-only identifier."""
        dataset = DatasetConfig(database="warehouse")
        assert dataset.database == "warehouse"
        assert dataset.schema_ is None
        assert dataset.table is None

    def test_dataset_config_validation_allows_schema_only(self):
        """Test that DatasetConfig allows schema-only identifier."""
        dataset = DatasetConfig(schema="analytics")
        assert dataset.schema_ == "analytics"
        assert dataset.database is None
        assert dataset.table is None

    def test_dataset_config_validation_allows_table_only(self):
        """Test that DatasetConfig allows table-only identifier."""
        dataset = DatasetConfig(table="customers")
        assert dataset.table == "customers"
        assert dataset.database is None
        assert dataset.schema_ is None


