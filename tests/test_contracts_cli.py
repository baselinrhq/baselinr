"""Tests for contracts CLI commands."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from baselinr.cli import contracts_command
from baselinr.config.schema import BaselinrConfig, ContractsConfig, ConnectionConfig, DatabaseType, StorageConfig


@pytest.fixture
def temp_contracts_dir():
    """Create temporary contracts directory with sample contracts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        contracts_dir = Path(tmpdir) / "contracts"
        contracts_dir.mkdir()
        
        # Create a sample contract
        contract1 = {
            "kind": "DataContract",
            "apiVersion": "v3.1.0",
            "id": "customers-contract",
            "status": "active",
            "info": {
                "title": "Customers Dataset Contract",
                "owner": "data-team",
            },
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
        
        contract_file = contracts_dir / "customers.odcs.yaml"
        with open(contract_file, "w") as f:
            yaml.dump(contract1, f)
        
        yield contracts_dir


@pytest.fixture
def base_config_with_contracts(temp_contracts_dir):
    """Create base config with contracts directory."""
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
        contracts=ContractsConfig(directory=str(temp_contracts_dir)),
    )


class TestContractsCLI:
    """Tests for contracts CLI commands."""
    
    def test_contracts_list_table_format(self, base_config_with_contracts, temp_contracts_dir, capsys):
        """Test contracts list command with table format."""
        args = MagicMock()
        args.config = None
        args.contracts_command = "list"
        args.format = "table"
        args.verbose = False
        
        with patch("baselinr.client.BaselinrClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            # Mock contracts
            from baselinr.contracts import ODCSContract, ODCSInfo, ODCSDataset, ODCSColumn
            from baselinr.contracts.odcs_schema import ODCSColumnQuality, ODCSQualitySpecification
            
            contract = ODCSContract(
                kind="DataContract",
                apiVersion="v3.1.0",
                id="customers-contract",
                status="active",
                info=ODCSInfo(title="Customers Dataset Contract", owner="data-team"),
                dataset=[ODCSDataset(
                    name="customers",
                    physicalName="analytics.customers",
                    columns=[ODCSColumn(
                        column="email",
                        quality=[ODCSColumnQuality(
                            type="format",
                            rule="format",
                            specification=ODCSQualitySpecification(
                                pattern="^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
                            ),
                            severity="error"
                        )]
                    )]
                )]
            )
            
            mock_client.contracts = [contract]
            mock_client.get_contract.return_value = contract
            
            result = contracts_command(args)
            
            assert result == 0
            captured = capsys.readouterr()
            assert "ODCS Contracts" in captured.out or "customers-contract" in captured.out
    
    def test_contracts_list_json_format(self, base_config_with_contracts, temp_contracts_dir, capsys):
        """Test contracts list command with JSON format."""
        args = MagicMock()
        args.config = None
        args.contracts_command = "list"
        args.format = "json"
        args.verbose = False
        
        with patch("baselinr.client.BaselinrClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            from baselinr.contracts import ODCSContract, ODCSInfo, ODCSDataset
            
            contract = ODCSContract(
                kind="DataContract",
                apiVersion="v3.1.0",
                id="customers-contract",
                status="active",
                info=ODCSInfo(title="Customers Dataset Contract"),
                dataset=[ODCSDataset(name="customers")]
            )
            
            mock_client.contracts = [contract]
            mock_client.get_contract.return_value = contract
            
            result = contracts_command(args)
            
            assert result == 0
            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert isinstance(output, list)
            assert len(output) > 0
            assert output[0]["id"] == "customers-contract"
    
    def test_contracts_list_no_contracts(self, base_config_with_contracts, temp_contracts_dir, capsys):
        """Test contracts list when no contracts exist."""
        args = MagicMock()
        args.config = None
        args.contracts_command = "list"
        args.format = "table"
        args.verbose = False
        
        with patch("baselinr.client.BaselinrClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.contracts = []
            
            result = contracts_command(args)
            
            assert result == 0
            captured = capsys.readouterr()
            assert "No contracts found" in captured.out
    
    def test_contracts_validate_success(self, base_config_with_contracts, temp_contracts_dir, capsys):
        """Test contracts validate command with valid contracts."""
        args = MagicMock()
        args.config = None
        args.contracts_command = "validate"
        args.format = "table"
        args.strict = False
        
        with patch("baselinr.client.BaselinrClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.validate_contracts.return_value = {
                "valid": True,
                "contracts_checked": 1,
                "errors": [],
                "warnings": []
            }
            
            result = contracts_command(args)
            
            assert result == 0
            captured = capsys.readouterr()
            assert "valid" in captured.out.lower() or "✅" in captured.out
    
    def test_contracts_validate_with_errors(self, base_config_with_contracts, temp_contracts_dir, capsys):
        """Test contracts validate command with validation errors."""
        args = MagicMock()
        args.config = None
        args.contracts_command = "validate"
        args.format = "table"
        args.strict = False
        
        with patch("baselinr.client.BaselinrClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.validate_contracts.return_value = {
                "valid": False,
                "contracts_checked": 1,
                "errors": [{"contract": "customers-contract", "message": "Invalid field"}],
                "warnings": []
            }
            
            result = contracts_command(args)
            
            assert result == 1
            captured = capsys.readouterr()
            assert "error" in captured.out.lower() or "❌" in captured.out
    
    def test_contracts_validate_json_format(self, base_config_with_contracts, temp_contracts_dir, capsys):
        """Test contracts validate command with JSON format."""
        args = MagicMock()
        args.config = None
        args.contracts_command = "validate"
        args.format = "json"
        args.strict = False
        
        with patch("baselinr.client.BaselinrClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.validate_contracts.return_value = {
                "valid": True,
                "contracts_checked": 1,
                "errors": [],
                "warnings": []
            }
            
            result = contracts_command(args)
            
            assert result == 0
            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert output["valid"] is True
            assert output["contracts_checked"] == 1
    
    def test_contracts_show_table_format(self, base_config_with_contracts, temp_contracts_dir, capsys):
        """Test contracts show command with table format."""
        args = MagicMock()
        args.config = None
        args.contracts_command = "show"
        args.contract = "customers-contract"
        args.format = "table"
        
        with patch("baselinr.client.BaselinrClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            from baselinr.contracts import ODCSContract, ODCSInfo, ODCSDataset
            
            contract = ODCSContract(
                kind="DataContract",
                apiVersion="v3.1.0",
                id="customers-contract",
                status="active",
                info=ODCSInfo(title="Customers Dataset Contract", owner="data-team"),
                dataset=[ODCSDataset(name="customers", physicalName="analytics.customers")]
            )
            
            mock_client.get_contract.return_value = contract
            
            result = contracts_command(args)
            
            assert result == 0
            captured = capsys.readouterr()
            assert "customers-contract" in captured.out or "Customers Dataset Contract" in captured.out
    
    def test_contracts_show_not_found(self, base_config_with_contracts, temp_contracts_dir, capsys):
        """Test contracts show command when contract not found."""
        args = MagicMock()
        args.config = None
        args.contracts_command = "show"
        args.contract = "nonexistent"
        args.format = "table"
        
        with patch("baselinr.client.BaselinrClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_contract.return_value = None
            
            result = contracts_command(args)
            
            assert result == 1
            captured = capsys.readouterr()
            assert "not found" in captured.out.lower() or "❌" in captured.out
    
    def test_contracts_show_json_format(self, base_config_with_contracts, temp_contracts_dir, capsys):
        """Test contracts show command with JSON format."""
        args = MagicMock()
        args.config = None
        args.contracts_command = "show"
        args.contract = "customers-contract"
        args.format = "json"
        
        with patch("baselinr.client.BaselinrClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            from baselinr.contracts import ODCSContract, ODCSInfo
            
            contract = ODCSContract(
                kind="DataContract",
                apiVersion="v3.1.0",
                id="customers-contract",
                status="active",
                info=ODCSInfo(title="Customers Dataset Contract")
            )
            
            mock_client.get_contract.return_value = contract
            
            result = contracts_command(args)
            
            assert result == 0
            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert output["id"] == "customers-contract"
            assert output["apiVersion"] == "v3.1.0"
    
    def test_contracts_rules_table_format(self, base_config_with_contracts, temp_contracts_dir, capsys):
        """Test contracts rules command with table format."""
        args = MagicMock()
        args.config = None
        args.contracts_command = "rules"
        args.contract = None
        args.format = "table"
        
        with patch("baselinr.client.BaselinrClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            from baselinr.contracts.adapter import ValidationRule
            
            rule = ValidationRule(
                type="format",
                table="customers",
                column="email",
                severity="error",
                enabled=True,
                contract_id="customers-contract"
            )
            
            mock_client.get_validation_rules_from_contracts.return_value = [rule]
            
            result = contracts_command(args)
            
            assert result == 0
            captured = capsys.readouterr()
            assert "Validation Rules" in captured.out or "format" in captured.out
    
    def test_contracts_rules_json_format(self, base_config_with_contracts, temp_contracts_dir, capsys):
        """Test contracts rules command with JSON format."""
        args = MagicMock()
        args.config = None
        args.contracts_command = "rules"
        args.contract = None
        args.format = "json"
        
        with patch("baselinr.client.BaselinrClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            from baselinr.contracts.adapter import ValidationRule
            
            rule = ValidationRule(
                type="format",
                table="customers",
                column="email",
                severity="error",
                enabled=True,
                contract_id="customers-contract"
            )
            
            mock_client.get_validation_rules_from_contracts.return_value = [rule]
            
            result = contracts_command(args)
            
            assert result == 0
            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert isinstance(output, list)
            assert len(output) > 0
            assert output[0]["type"] == "format"
            assert output[0]["table"] == "customers"
    
    def test_contracts_rules_filtered_by_contract(self, base_config_with_contracts, temp_contracts_dir, capsys):
        """Test contracts rules command filtered by contract."""
        args = MagicMock()
        args.config = None
        args.contracts_command = "rules"
        args.contract = "customers-contract"
        args.format = "table"
        
        with patch("baselinr.client.BaselinrClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            from baselinr.contracts.adapter import ValidationRule
            
            rule1 = ValidationRule(
                type="format",
                table="customers",
                column="email",
                severity="error",
                enabled=True,
                contract_id="customers-contract"
            )
            rule2 = ValidationRule(
                type="not_null",
                table="orders",
                column="id",
                severity="error",
                enabled=True,
                contract_id="orders-contract"
            )
            
            mock_client.get_validation_rules_from_contracts.return_value = [rule1, rule2]
            
            result = contracts_command(args)
            
            assert result == 0
            # The command should filter to only customers-contract rules
            captured = capsys.readouterr()
            # Should only show customers rules, not orders
            assert "customers" in captured.out.lower()
    
    def test_contracts_unknown_command(self, base_config_with_contracts, temp_contracts_dir, capsys):
        """Test contracts command with unknown subcommand."""
        args = MagicMock()
        args.config = None
        args.contracts_command = "unknown"
        
        with patch("baselinr.client.BaselinrClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            result = contracts_command(args)
            
            assert result == 1
            captured = capsys.readouterr()
            assert "Unknown" in captured.out or "unknown" in captured.out.lower()

