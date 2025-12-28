"""Tests for BaselinrClient contracts functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from baselinr import BaselinrClient
from baselinr.config.schema import (
    BaselinrConfig,
    ConnectionConfig,
    ContractsConfig,
    DatabaseType,
    StorageConfig,
)


@pytest.fixture
def sample_config_with_contracts():
    """Create a sample BaselinrConfig with contracts directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        contracts_dir = Path(tmpdir) / "contracts"
        contracts_dir.mkdir()

        # Create sample contracts
        contract1 = {
            "kind": "DataContract",
            "apiVersion": "v3.1.0",
            "id": "customers-contract",
            "status": "active",
            "info": {
                "title": "Customers Dataset Contract",
                "owner": "data-team",
                "domain": "analytics",
            },
            "dataset": [
                {
                    "name": "customers",
                    "physicalName": "analytics.customers",
                    "columns": [
                        {
                            "column": "email",
                            "quality": [
                                {
                                    "type": "format",
                                    "rule": "format",
                                    "specification": {
                                        "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
                                    },
                                    "severity": "error",
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        contract2 = {
            "kind": "DataContract",
            "apiVersion": "v3.1.0",
            "id": "orders-contract",
            "status": "active",
            "info": {
                "title": "Orders Dataset Contract",
                "owner": "data-team",
            },
            "dataset": [
                {
                    "name": "orders",
                    "physicalName": "analytics.orders",
                    "columns": [
                        {
                            "column": "order_id",
                            "isPrimaryKey": True,
                            "quality": [
                                {
                                    "type": "not_null",
                                    "rule": "not_null",
                                    "severity": "error",
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        # Write contract files
        contract_file1 = contracts_dir / "customers.odcs.yaml"
        with open(contract_file1, "w") as f:
            yaml.dump(contract1, f)

        contract_file2 = contracts_dir / "orders.odcs.yaml"
        with open(contract_file2, "w") as f:
            yaml.dump(contract2, f)

        config = BaselinrConfig(
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
                runs_table="baselinr_runs",
                results_table="baselinr_results",
                create_tables=True,
            ),
            contracts=ContractsConfig(directory=str(contracts_dir)),
        )

        yield config, contracts_dir


class TestBaselinrClientContracts:
    """Tests for BaselinrClient contracts methods."""

    def test_contracts_property_loads_contracts(self, sample_config_with_contracts):
        """Test that contracts property loads contracts from directory."""
        config, _ = sample_config_with_contracts
        client = BaselinrClient(config=config)

        contracts = client.contracts

        assert len(contracts) == 2
        contract_ids = [c.id for c in contracts]
        assert "customers-contract" in contract_ids
        assert "orders-contract" in contract_ids

    def test_contracts_property_caches(self, sample_config_with_contracts):
        """Test that contracts property caches loaded contracts."""
        config, _ = sample_config_with_contracts
        client = BaselinrClient(config=config)

        contracts1 = client.contracts
        contracts2 = client.contracts

        # Should be the same list instance (cached)
        assert contracts1 is contracts2

    def test_get_contract_by_id(self, sample_config_with_contracts):
        """Test getting contract by contract ID."""
        config, _ = sample_config_with_contracts
        client = BaselinrClient(config=config)

        contract = client.get_contract("customers-contract")

        assert contract is not None
        assert contract.id == "customers-contract"
        assert contract.info.title == "Customers Dataset Contract"

    def test_get_contract_by_dataset_name(self, sample_config_with_contracts):
        """Test getting contract by dataset name."""
        config, _ = sample_config_with_contracts
        client = BaselinrClient(config=config)

        contract = client.get_contract("customers")

        assert contract is not None
        assert contract.id == "customers-contract"

    def test_get_contract_by_physical_name(self, sample_config_with_contracts):
        """Test getting contract by physical name."""
        config, _ = sample_config_with_contracts
        client = BaselinrClient(config=config)

        contract = client.get_contract("analytics.customers")

        assert contract is not None
        assert contract.id == "customers-contract"

    def test_get_contract_not_found(self, sample_config_with_contracts):
        """Test getting contract that doesn't exist."""
        config, _ = sample_config_with_contracts
        client = BaselinrClient(config=config)

        contract = client.get_contract("nonexistent")

        assert contract is None

    def test_get_contract_datasets(self, sample_config_with_contracts):
        """Test getting list of dataset names from contracts."""
        config, _ = sample_config_with_contracts
        client = BaselinrClient(config=config)

        datasets = client.get_contract_datasets()

        assert len(datasets) == 2
        assert "customers" in datasets
        assert "orders" in datasets

    def test_get_validation_rules_from_contracts(self, sample_config_with_contracts):
        """Test extracting validation rules from contracts."""
        config, _ = sample_config_with_contracts
        client = BaselinrClient(config=config)

        rules = client.get_validation_rules_from_contracts()

        assert len(rules) >= 2  # At least 2 rules (email format + order_id not_null)
        rule_types = [r.type for r in rules]
        assert "format" in rule_types or "not_null" in rule_types

        # Check that rules have contract_id
        for rule in rules:
            assert rule.contract_id is not None

    def test_get_profiling_targets_from_contracts(self, sample_config_with_contracts):
        """Test extracting profiling targets from contracts."""
        config, _ = sample_config_with_contracts
        client = BaselinrClient(config=config)

        targets = client.get_profiling_targets_from_contracts()

        assert len(targets) == 2
        target_names = [t.get_full_name() for t in targets]
        assert any("customers" in name for name in target_names)
        assert any("orders" in name for name in target_names)

    def test_get_dataset_metadata_from_contracts(self, sample_config_with_contracts):
        """Test extracting dataset metadata from contracts."""
        config, _ = sample_config_with_contracts
        client = BaselinrClient(config=config)

        metadata = client.get_dataset_metadata_from_contracts()

        assert len(metadata) == 2
        dataset_names = [m.name for m in metadata]
        assert "customers" in dataset_names
        assert "orders" in dataset_names

    def test_validate_contracts_success(self, sample_config_with_contracts):
        """Test validating contracts when all are valid."""
        config, _ = sample_config_with_contracts
        client = BaselinrClient(config=config)

        result = client.validate_contracts()

        assert result["valid"] is True
        assert result["contracts_checked"] == 2
        assert len(result["errors"]) == 0

    def test_validate_contracts_strict_mode(self, sample_config_with_contracts):
        """Test validating contracts in strict mode."""
        config, _ = sample_config_with_contracts
        client = BaselinrClient(config=config)

        result = client.validate_contracts(strict=True)

        assert "valid" in result
        assert "contracts_checked" in result

    def test_contracts_empty_when_no_config(self):
        """Test that contracts property returns empty list when no contracts config."""
        config = BaselinrConfig(
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
                runs_table="baselinr_runs",
                results_table="baselinr_results",
            ),
        )
        client = BaselinrClient(config=config)

        contracts = client.contracts

        assert contracts == []

    def test_contracts_handles_load_error(self):
        """Test that contracts property handles load errors gracefully."""
        config = BaselinrConfig(
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
                runs_table="baselinr_runs",
                results_table="baselinr_results",
            ),
            contracts=ContractsConfig(directory="/nonexistent/directory"),
        )
        client = BaselinrClient(config=config)

        # Should not raise, but return empty list
        contracts = client.contracts

        assert contracts == []

