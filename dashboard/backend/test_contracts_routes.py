"""
Unit tests for contracts_routes module.
"""

import pytest
import os
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Import the main app to get the router
import sys
sys.path.insert(0, os.path.dirname(__file__))

from contracts_routes import router, set_contracts_directory
from fastapi import FastAPI


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
                "owner": "data-team"
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
def app(temp_contracts_dir):
    """Create FastAPI app with contracts router."""
    app = FastAPI()
    app.include_router(router)
    
    # Set contracts directory for testing
    set_contracts_directory(str(temp_contracts_dir))
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestContractsRoutes:
    """Tests for contracts API routes."""
    
    def test_list_contracts(self, client):
        """Test listing all contracts."""
        response = client.get("/api/contracts")
        
        assert response.status_code == 200
        data = response.json()
        assert "contracts" in data
        assert isinstance(data["contracts"], list)
        assert len(data["contracts"]) > 0
    
    def test_list_contracts_empty(self, app):
        """Test listing contracts when directory is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            set_contracts_directory(tmpdir)
            client = TestClient(app)
            
            response = client.get("/api/contracts")
            
            assert response.status_code == 200
            data = response.json()
            assert "contracts" in data
            assert data["contracts"] == []
    
    def test_get_contract_by_id(self, client):
        """Test getting contract by ID."""
        response = client.get("/api/contracts/customers-contract")
        
        assert response.status_code == 200
        data = response.json()
        assert data["contract"]["id"] == "customers-contract"
        assert data["contract"]["status"] == "active"
    
    def test_get_contract_by_dataset_name(self, client):
        """Test getting contract by dataset name."""
        response = client.get("/api/contracts/customers")
        
        assert response.status_code == 200
        data = response.json()
        assert data["contract"]["id"] == "customers-contract"
    
    def test_get_contract_not_found(self, client):
        """Test getting non-existent contract."""
        response = client.get("/api/contracts/nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_validate_contracts(self, client):
        """Test validating all contracts."""
        response = client.post("/api/contracts/validate")
        
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert "contracts_checked" in data
        assert "errors" in data
        assert "warnings" in data
    
    def test_validate_contracts_strict(self, client):
        """Test validating contracts in strict mode."""
        response = client.post("/api/contracts/validate?strict=true")
        
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
    
    def test_get_validation_rules(self, client):
        """Test getting validation rules from contracts."""
        response = client.get("/api/contracts/rules")
        
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert isinstance(data["rules"], list)
    
    def test_get_validation_rules_filtered(self, client):
        """Test getting validation rules filtered by contract."""
        response = client.get("/api/contracts/rules?contract_id=customers-contract")
        
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        # All rules should be from customers-contract
        for rule in data["rules"]:
            assert rule["contract_id"] == "customers-contract"
    
    def test_create_contract(self, client, temp_contracts_dir):
        """Test creating a new contract."""
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
        
        response = client.post(
            "/api/contracts",
            json={"contract": new_contract}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["contract"]["id"] == "new-contract"
        
        # Verify file was created
        contract_file = temp_contracts_dir / "new-contract.odcs.yaml"
        assert contract_file.exists()
    
    def test_update_contract(self, client):
        """Test updating an existing contract."""
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
        
        response = client.put(
            "/api/contracts/customers-contract",
            json={"contract": updated_data}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["contract"]["id"] == "customers-contract"
        assert data["contract"]["info"]["title"] == "Updated Customers Contract"
    
    def test_update_contract_not_found(self, client):
        """Test updating non-existent contract."""
        updated_data = {
            "kind": "DataContract",
            "apiVersion": "v3.1.0",
            "id": "nonexistent",
            "status": "active"
        }
        
        response = client.put(
            "/api/contracts/nonexistent",
            json={"contract": updated_data}
        )
        
        assert response.status_code == 404
    
    def test_delete_contract(self, client, temp_contracts_dir):
        """Test deleting a contract."""
        # Verify file exists
        contract_file = temp_contracts_dir / "customers.odcs.yaml"
        assert contract_file.exists()
        
        response = client.delete("/api/contracts/customers-contract")
        
        assert response.status_code == 204
        
        # Verify file was deleted
        assert not contract_file.exists()
    
    def test_delete_contract_not_found(self, client):
        """Test deleting non-existent contract."""
        response = client.delete("/api/contracts/nonexistent")
        
        assert response.status_code == 404

