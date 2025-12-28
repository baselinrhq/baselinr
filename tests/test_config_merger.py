"""Tests for configuration merger module with ODCS contracts."""

import pytest
import tempfile
import yaml
from pathlib import Path

from baselinr.config.merger import ConfigMerger
from baselinr.config.schema import (
    BaselinrConfig,
    ColumnAnomalyConfig,
    ColumnConfig,
    ColumnDriftConfig,
    ConnectionConfig,
    ContractsConfig,
    DatabaseType,
    DriftDetectionConfig,
    PartitionConfig,
    ProfilingConfig,
    SamplingConfig,
    StorageConfig,
    TablePattern,
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


@pytest.fixture
def contracts_dir(tmp_path):
    """Create a temporary contracts directory."""
    contracts_dir = tmp_path / "contracts"
    contracts_dir.mkdir()
    return contracts_dir


def create_contract_file(contracts_dir: Path, contract_id: str, contract_data: dict):
    """Helper to create a contract file."""
    file_path = contracts_dir / f"{contract_id}.odcs.yaml"
    with open(file_path, "w") as f:
        yaml.dump(contract_data, f)
    return file_path


class TestConfigMergerWithContracts:
    """Tests for ConfigMerger with ODCS contracts."""

    def test_merge_profiling_config_no_contract(self, base_config):
        """Test merging profiling config when no contract matches."""
        table_pattern = TablePattern(table="customers", schema="analytics")
        merger = ConfigMerger(base_config)

        merged = merger.merge_profiling_config(table_pattern)
        # Should return dict with None values when no contract
        assert isinstance(merged, dict)
        assert merged["partition"] is None
        assert merged["sampling"] is None
        assert merged["columns"] is None

    def test_merge_profiling_config_with_contract_partition(self, base_config, contracts_dir):
        """Test merging profiling config with contract partition config."""
        contract = {
            "kind": "DataContract",
            "apiVersion": "v3.1.0",
            "id": "customers_contract",
            "dataset": [{
                "name": "customers",
                "physicalName": "analytics.customers",
                "columns": [{
                    "column": "date",
                    "partitionStatus": True,
                }]
            }],
            "customProperties": [{
                "property": "baselinr.partition.customers",
                "value": {
                    "strategy": "latest",
                }
            }]
        }
        create_contract_file(contracts_dir, "customers", contract)
        
        base_config.contracts = ContractsConfig(directory=str(contracts_dir))
        merger = ConfigMerger(base_config)

        table_pattern = TablePattern(table="customers", schema="analytics")
        merged = merger.merge_profiling_config(table_pattern)

        assert isinstance(merged, dict)
        assert merged["partition"] is not None
        assert merged["partition"].strategy == "latest"
        assert merged["partition"].key == "date"

    def test_merge_profiling_config_with_contract_sampling(self, base_config, contracts_dir):
        """Test merging profiling config with contract sampling config."""
        contract = {
            "kind": "DataContract",
            "apiVersion": "v3.1.0",
            "id": "customers_contract",
            "dataset": [{
                "name": "customers",
                "physicalName": "analytics.customers",
            }],
            "customProperties": [{
                "property": "baselinr.sampling.customers",
                "value": {
                    "enabled": True,
                    "method": "random",
                    "fraction": 0.1,
                }
            }]
        }
        create_contract_file(contracts_dir, "customers", contract)
        
        base_config.contracts = ContractsConfig(directory=str(contracts_dir))
        merger = ConfigMerger(base_config)

        table_pattern = TablePattern(table="customers", schema="analytics")
        merged = merger.merge_profiling_config(table_pattern)

        assert isinstance(merged, dict)
        assert merged["sampling"] is not None
        assert merged["sampling"].enabled is True
        assert merged["sampling"].fraction == 0.1

    def test_merge_drift_config_no_contract(self, base_config):
        """Test merging drift config when no contract matches."""
        merger = ConfigMerger(base_config)

        merged = merger.merge_drift_config("warehouse", "analytics", "customers")
        assert merged is not None
        assert merged.strategy == "absolute_threshold"

    def test_merge_drift_config_with_contract_strategy(self, base_config, contracts_dir):
        """Test merging drift config with contract strategy override."""
        contract = {
            "kind": "DataContract",
            "apiVersion": "v3.1.0",
            "id": "customers_contract",
            "dataset": [{
                "name": "customers",
                "physicalName": "analytics.customers",
            }],
            "customProperties": [{
                "property": "baselinr.drift.strategy.customers",
                "value": "statistical"
            }]
        }
        create_contract_file(contracts_dir, "customers", contract)
        
        base_config.contracts = ContractsConfig(directory=str(contracts_dir))
        merger = ConfigMerger(base_config)

        merged = merger.merge_drift_config("warehouse", "analytics", "customers")
        assert merged is not None
        assert merged.strategy == "statistical"

    def test_merge_drift_config_with_contract_thresholds(self, base_config, contracts_dir):
        """Test merging drift config with contract threshold overrides."""
        contract = {
            "kind": "DataContract",
            "apiVersion": "v3.1.0",
            "id": "customers_contract",
            "dataset": [{
                "name": "customers",
                "physicalName": "analytics.customers",
            }],
            "customProperties": [{
                "property": "baselinr.drift.absolute_threshold.customers",
                "value": {
                    "low_threshold": 3.0,
                    "medium_threshold": 10.0,
                    "high_threshold": 25.0,
                }
            }]
        }
        create_contract_file(contracts_dir, "customers", contract)
        
        base_config.contracts = ContractsConfig(directory=str(contracts_dir))
        merger = ConfigMerger(base_config)

        merged = merger.merge_drift_config("warehouse", "analytics", "customers")
        assert merged is not None
        assert merged.absolute_threshold["low_threshold"] == 3.0
        assert merged.absolute_threshold["medium_threshold"] == 10.0
        assert merged.absolute_threshold["high_threshold"] == 25.0

    def test_get_validation_rules_from_contract(self, base_config, contracts_dir):
        """Test getting validation rules from contract."""
        contract = {
            "kind": "DataContract",
            "apiVersion": "v3.1.0",
            "id": "customers_contract",
            "dataset": [{
                "name": "customers",
                "physicalName": "analytics.customers",
                "columns": [{
                    "column": "email",
                    "quality": [{
                        "type": "format",
                        "rule": "format",
                        "specification": {
                            "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
                        },
                        "severity": "error"
                    }]
                }]
            }]
        }
        create_contract_file(contracts_dir, "customers", contract)
        
        base_config.contracts = ContractsConfig(directory=str(contracts_dir))
        merger = ConfigMerger(base_config)

        rules = merger.get_validation_rules("warehouse", "analytics", "customers")
        # Should have rules from contract
        assert len(rules) > 0
        # Find the email format rule
        email_rules = [r for r in rules if r.column == "email" and r.type == "format"]
        assert len(email_rules) > 0

    def test_get_anomaly_column_configs_from_contract(self, base_config, contracts_dir):
        """Test getting anomaly column configs from contract."""
        contract = {
            "kind": "DataContract",
            "apiVersion": "v3.1.0",
            "id": "customers_contract",
            "dataset": [{
                "name": "customers",
                "physicalName": "analytics.customers",
                "columns": [{
                    "column": "total_amount",
                }]
            }],
            "customProperties": [{
                "property": "baselinr.anomaly.customers.total_amount",
                "value": {
                    "enabled": True,
                    "methods": ["control_limits", "iqr"]
                }
            }]
        }
        create_contract_file(contracts_dir, "customers", contract)
        
        base_config.contracts = ContractsConfig(directory=str(contracts_dir))
        merger = ConfigMerger(base_config)

        configs = merger.get_anomaly_column_configs("warehouse", "analytics", "customers")
        assert len(configs) == 1
        assert configs[0].name == "total_amount"
        assert configs[0].anomaly is not None
        assert configs[0].anomaly.enabled is True

    def test_get_drift_column_configs_from_contract(self, base_config, contracts_dir):
        """Test getting drift column configs from contract."""
        contract = {
            "kind": "DataContract",
            "apiVersion": "v3.1.0",
            "id": "customers_contract",
            "dataset": [{
                "name": "customers",
                "physicalName": "analytics.customers",
                "columns": [{
                    "column": "email",
                }]
            }],
            "customProperties": [{
                "property": "baselinr.drift.customers.email",
                "value": {
                    "enabled": False
                }
            }]
        }
        create_contract_file(contracts_dir, "customers", contract)
        
        base_config.contracts = ContractsConfig(directory=str(contracts_dir))
        merger = ConfigMerger(base_config)

        configs = merger.get_drift_column_configs("warehouse", "analytics", "customers")
        assert len(configs) == 1
        assert configs[0].name == "email"
        assert configs[0].drift is not None
        assert configs[0].drift.enabled is False

    def test_resolve_table_config_with_contract(self, base_config, contracts_dir):
        """Test resolving complete table config with contract."""
        contract = {
            "kind": "DataContract",
            "apiVersion": "v3.1.0",
            "id": "customers_contract",
            "dataset": [{
                "name": "customers",
                "physicalName": "analytics.customers",
                "columns": [{
                    "column": "date",
                    "partitionStatus": True,
                }, {
                    "column": "customer_id",
                    "quality": [{
                        "type": "not_null",
                        "rule": "not_null",
                        "severity": "error"
                    }]
                }]
            }],
            "customProperties": [{
                "property": "baselinr.partition.customers",
                "value": {
                    "strategy": "latest",
                }
            }, {
                "property": "baselinr.drift.strategy.customers",
                "value": "statistical"
            }]
        }
        create_contract_file(contracts_dir, "customers", contract)
        
        base_config.contracts = ContractsConfig(directory=str(contracts_dir))
        merger = ConfigMerger(base_config)

        table_pattern = TablePattern(table="customers", schema="analytics", database="warehouse")
        resolved = merger.resolve_table_config(table_pattern)

        assert resolved["profiling"]["partition"] is not None
        assert resolved["profiling"]["partition"].strategy == "latest"
        assert resolved["drift"].strategy == "statistical"
        assert len(resolved["validation_rules"]) > 0

    def test_merger_without_config(self):
        """Test merger initialization without config."""
        merger = ConfigMerger(None)
        assert merger.config is None

    def test_merger_without_contracts(self, base_config):
        """Test merger with no contracts configured."""
        merger = ConfigMerger(base_config)

        table_pattern = TablePattern(table="customers", schema="analytics")
        merged = merger.merge_profiling_config(table_pattern)
        assert merged["partition"] is None
