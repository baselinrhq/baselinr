"""
Unit tests for contracts_service module.
"""

import pytest
import os
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from contracts_service import ContractsService


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
                "domain": "analytics"
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
        
        # Create another contract
        contract2 = {
            "kind": "DataContract",
            "apiVersion": "v3.1.0",
            "id": "orders-contract",
            "status": "active",
            "dataset": [{
                "name": "orders",
                "physicalName": "analytics.orders"
            }]
        }
        
        contract_file2 = contracts_dir / "orders.odcs.yaml"
        with open(contract_file2, "w") as f:
            yaml.dump(contract2, f)
        
        yield contracts_dir


class TestContractsService:
    """Tests for ContractsService class."""
    
    def test_init_with_directory(self, temp_contracts_dir):
        """Test initializing service with contracts directory."""
        service = ContractsService(str(temp_contracts_dir))
        assert service._contracts_dir == str(temp_contracts_dir)
    
    def test_init_without_directory(self):
        """Test initializing service without contracts directory."""
        service = ContractsService()
        assert service._contracts_dir is None
    
    def test_set_contracts_dir(self, temp_contracts_dir):
        """Test setting contracts directory."""
        service = ContractsService()
        service.set_contracts_dir(str(temp_contracts_dir))
        assert service._contracts_dir == str(temp_contracts_dir)
        assert service._contracts_cache == []
        assert service._last_load_time is None
    
    def test_list_contracts(self, temp_contracts_dir):
        """Test listing all contracts."""
        service = ContractsService(str(temp_contracts_dir))
        contracts = service.list_contracts()
        
        assert isinstance(contracts, list)
        assert len(contracts) == 2
        
        # Check contract IDs
        contract_ids = [c["id"] for c in contracts]
        assert "customers-contract" in contract_ids
        assert "orders-contract" in contract_ids
    
    def test_list_contracts_empty_directory(self):
        """Test listing contracts from empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ContractsService(tmpdir)
            contracts = service.list_contracts()
            assert contracts == []
    
    def test_get_contract_by_id(self, temp_contracts_dir):
        """Test getting contract by ID."""
        service = ContractsService(str(temp_contracts_dir))
        contract = service.get_contract("customers-contract")
        
        assert contract is not None
        assert contract["id"] == "customers-contract"
        assert contract["status"] == "active"
        assert contract["info"]["title"] == "Customers Dataset Contract"
    
    def test_get_contract_by_dataset_name(self, temp_contracts_dir):
        """Test getting contract by dataset name."""
        service = ContractsService(str(temp_contracts_dir))
        contract = service.get_contract("customers")
        
        assert contract is not None
        assert contract["id"] == "customers-contract"
    
    def test_get_contract_by_physical_name(self, temp_contracts_dir):
        """Test getting contract by physical name."""
        service = ContractsService(str(temp_contracts_dir))
        contract = service.get_contract("analytics.customers")
        
        assert contract is not None
        assert contract["id"] == "customers-contract"
    
    def test_get_contract_not_found(self, temp_contracts_dir):
        """Test getting non-existent contract."""
        service = ContractsService(str(temp_contracts_dir))
        contract = service.get_contract("nonexistent")
        
        assert contract is None
    
    def test_validate_contracts_success(self, temp_contracts_dir):
        """Test validating valid contracts."""
        service = ContractsService(str(temp_contracts_dir))
        result = service.validate_contracts(strict=False)
        
        assert result["valid"] is True
        assert result["contracts_checked"] == 2
        assert len(result["errors"]) == 0
    
    def test_validate_contracts_with_invalid(self):
        """Test validating contracts with invalid data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            contracts_dir = Path(tmpdir) / "contracts"
            contracts_dir.mkdir()
            
            # Create invalid contract (missing required fields)
            invalid_contract = {
                "kind": "DataContract",
                # Missing apiVersion
            }
            
            contract_file = contracts_dir / "invalid.odcs.yaml"
            with open(contract_file, "w") as f:
                yaml.dump(invalid_contract, f)
            
            service = ContractsService(str(contracts_dir))
            result = service.validate_contracts(strict=False)
            
            # Should have errors
            assert result["valid"] is False or len(result["errors"]) > 0
    
    def test_get_validation_rules(self, temp_contracts_dir):
        """Test getting validation rules from contracts."""
        service = ContractsService(str(temp_contracts_dir))
        rules = service.get_validation_rules()
        
        assert isinstance(rules, list)
        # Should have at least one rule from customers contract (email format)
        assert len(rules) > 0
    
    def test_get_validation_rules_filtered_by_contract(self, temp_contracts_dir):
        """Test getting validation rules filtered by contract ID."""
        service = ContractsService(str(temp_contracts_dir))
        rules = service.get_validation_rules(contract_id="customers-contract")
        
        assert isinstance(rules, list)
        # All rules should be from customers-contract
        for rule in rules:
            assert rule.contract_id == "customers-contract"
    
    def test_create_contract(self, temp_contracts_dir):
        """Test creating a new contract."""
        service = ContractsService(str(temp_contracts_dir))
        
        new_contract = {
            "kind": "DataContract",
            "apiVersion": "v3.1.0",
            "id": "new-contract",
            "status": "active",
            "dataset": [{
                "name": "new_table",
                "physicalName": "analytics.new_table"
            }]
        }
        
        contract = service.create_contract(new_contract)
        
        assert contract is not None
        assert contract["id"] == "new-contract"
        
        # Verify file was created
        contract_file = temp_contracts_dir / "new-contract.odcs.yaml"
        assert contract_file.exists()
    
    def test_update_contract(self, temp_contracts_dir):
        """Test updating an existing contract."""
        service = ContractsService(str(temp_contracts_dir))
        
        updated_data = {
            "kind": "DataContract",
            "apiVersion": "v3.1.0",
            "id": "customers-contract",
            "status": "active",
            "info": {
                "title": "Updated Customers Contract",
                "owner": "data-team"
            },
            "dataset": [{
                "name": "customers",
                "physicalName": "analytics.customers"
            }]
        }
        
        contract = service.update_contract("customers-contract", updated_data)
        
        assert contract is not None
        assert contract["id"] == "customers-contract"
        assert contract["info"]["title"] == "Updated Customers Contract"
    
    def test_update_contract_not_found(self, temp_contracts_dir):
        """Test updating non-existent contract."""
        service = ContractsService(str(temp_contracts_dir))
        
        updated_data = {
            "kind": "DataContract",
            "apiVersion": "v3.1.0",
            "id": "nonexistent",
            "status": "active"
        }
        
        with pytest.raises(ValueError, match="Contract not found"):
            service.update_contract("nonexistent", updated_data)
    
    def test_delete_contract(self, temp_contracts_dir):
        """Test deleting a contract."""
        service = ContractsService(str(temp_contracts_dir))
        
        # Verify file exists
        contract_file = temp_contracts_dir / "customers.odcs.yaml"
        assert contract_file.exists()
        
        service.delete_contract("customers-contract")
        
        # Verify file was deleted
        assert not contract_file.exists()
        
        # Verify contract is no longer accessible
        contract = service.get_contract("customers-contract")
        assert contract is None
    
    def test_delete_contract_not_found(self, temp_contracts_dir):
        """Test deleting non-existent contract."""
        service = ContractsService(str(temp_contracts_dir))
        
        with pytest.raises(ValueError, match="Contract not found"):
            service.delete_contract("nonexistent")
    
    def test_contract_to_summary(self, temp_contracts_dir):
        """Test converting contract to summary."""
        service = ContractsService(str(temp_contracts_dir))
        contracts = service._load_all_contracts()
        
        summary = service._contract_to_summary(contracts[0])
        
        assert "id" in summary
        assert "status" in summary
        assert "title" in summary
        assert summary["id"] == "customers-contract" or summary["id"] == "orders-contract"

