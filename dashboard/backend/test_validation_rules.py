"""
Tests for validation rules API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import json

from main import app
from database import DatabaseClient


@pytest.fixture
def db_engine():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    
    # Create validation_rules table
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE baselinr_validation_rules (
                id VARCHAR(255) PRIMARY KEY,
                rule_type VARCHAR(50) NOT NULL,
                table_name VARCHAR(255) NOT NULL,
                schema_name VARCHAR(255),
                column_name VARCHAR(255),
                config TEXT NOT NULL DEFAULT '{}',
                severity VARCHAR(20) NOT NULL DEFAULT 'medium',
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                last_tested TIMESTAMP,
                last_test_result BOOLEAN
            )
        """))
        conn.commit()
    
    return engine


@pytest.fixture
def client(db_engine):
    """Create test client with mocked database."""
    # Override the database client to use our test engine
    from validation_service import ValidationService
    from validation_routes import get_validation_service
    
    original_service = None
    
    def override_service():
        return ValidationService(db_engine)
    
    app.dependency_overrides[get_validation_service] = override_service
    
    client = TestClient(app)
    yield client
    
    # Cleanup
    app.dependency_overrides.clear()


def test_list_validation_rules_empty(client):
    """Test listing validation rules when none exist."""
    response = client.get("/api/validation/rules")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["rules"] == []


def test_create_validation_rule(client, db_engine):
    """Test creating a validation rule."""
    rule_data = {
        "rule_type": "format",
        "table": "users",
        "schema": "public",
        "column": "email",
        "config": {"pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"},
        "severity": "high",
        "enabled": True
    }
    
    response = client.post("/api/validation/rules", json=rule_data)
    assert response.status_code == 200
    data = response.json()
    assert data["rule_type"] == "format"
    assert data["table"] == "users"
    assert data["schema"] == "public"
    assert data["column"] == "email"
    assert data["severity"] == "high"
    assert data["enabled"] is True
    assert "id" in data
    assert "created_at" in data


def test_create_validation_rule_invalid_type(client):
    """Test creating a validation rule with invalid rule type."""
    rule_data = {
        "rule_type": "invalid_type",
        "table": "users",
        "column": "email",
        "config": {},
        "severity": "high"
    }
    
    response = client.post("/api/validation/rules", json=rule_data)
    assert response.status_code == 400
    assert "Invalid rule type" in response.json()["detail"]


def test_create_validation_rule_invalid_severity(client):
    """Test creating a validation rule with invalid severity."""
    rule_data = {
        "rule_type": "format",
        "table": "users",
        "column": "email",
        "config": {},
        "severity": "invalid"
    }
    
    response = client.post("/api/validation/rules", json=rule_data)
    assert response.status_code == 400
    assert "Invalid severity" in response.json()["detail"]


def test_list_validation_rules_with_data(client, db_engine):
    """Test listing validation rules with filters."""
    # Create a few rules
    rule1 = {
        "rule_type": "format",
        "table": "users",
        "column": "email",
        "config": {"pattern": "email"},
        "severity": "high"
    }
    rule2 = {
        "rule_type": "range",
        "table": "orders",
        "column": "amount",
        "config": {"min_value": 0, "max_value": 10000},
        "severity": "medium"
    }
    
    client.post("/api/validation/rules", json=rule1)
    client.post("/api/validation/rules", json=rule2)
    
    # List all rules
    response = client.get("/api/validation/rules")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    
    # Filter by table
    response = client.get("/api/validation/rules?table=users")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["rules"][0]["table"] == "users"
    
    # Filter by rule_type
    response = client.get("/api/validation/rules?rule_type=range")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["rules"][0]["rule_type"] == "range"


def test_get_validation_rule(client, db_engine):
    """Test getting a specific validation rule."""
    rule_data = {
        "rule_type": "format",
        "table": "users",
        "column": "email",
        "config": {"pattern": "email"},
        "severity": "high"
    }
    
    create_response = client.post("/api/validation/rules", json=rule_data)
    rule_id = create_response.json()["id"]
    
    # Get the rule
    response = client.get(f"/api/validation/rules/{rule_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == rule_id
    assert data["rule_type"] == "format"
    assert data["table"] == "users"


def test_get_validation_rule_not_found(client):
    """Test getting a non-existent validation rule."""
    response = client.get("/api/validation/rules/non-existent-id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_validation_rule(client, db_engine):
    """Test updating a validation rule."""
    rule_data = {
        "rule_type": "format",
        "table": "users",
        "column": "email",
        "config": {"pattern": "email"},
        "severity": "high"
    }
    
    create_response = client.post("/api/validation/rules", json=rule_data)
    rule_id = create_response.json()["id"]
    
    # Update the rule
    update_data = {
        "severity": "medium",
        "enabled": False
    }
    
    response = client.put(f"/api/validation/rules/{rule_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["severity"] == "medium"
    assert data["enabled"] is False
    assert data["updated_at"] is not None


def test_update_validation_rule_not_found(client):
    """Test updating a non-existent validation rule."""
    update_data = {"severity": "low"}
    response = client.put("/api/validation/rules/non-existent-id", json=update_data)
    assert response.status_code == 404


def test_delete_validation_rule(client, db_engine):
    """Test deleting a validation rule."""
    rule_data = {
        "rule_type": "format",
        "table": "users",
        "column": "email",
        "config": {"pattern": "email"},
        "severity": "high"
    }
    
    create_response = client.post("/api/validation/rules", json=rule_data)
    rule_id = create_response.json()["id"]
    
    # Delete the rule
    response = client.delete(f"/api/validation/rules/{rule_id}")
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]
    
    # Verify it's deleted
    response = client.get(f"/api/validation/rules/{rule_id}")
    assert response.status_code == 404


def test_delete_validation_rule_not_found(client):
    """Test deleting a non-existent validation rule."""
    response = client.delete("/api/validation/rules/non-existent-id")
    assert response.status_code == 404


def test_test_validation_rule(client, db_engine):
    """Test testing a validation rule."""
    rule_data = {
        "rule_type": "format",
        "table": "users",
        "column": "email",
        "config": {"pattern": "email"},
        "severity": "high"
    }
    
    create_response = client.post("/api/validation/rules", json=rule_data)
    rule_id = create_response.json()["id"]
    
    # Test the rule
    response = client.post(f"/api/validation/rules/{rule_id}/test")
    assert response.status_code == 200
    data = response.json()
    assert data["rule_id"] == rule_id
    assert "passed" in data
    assert "tested_at" in data


def test_test_validation_rule_not_found(client):
    """Test testing a non-existent validation rule."""
    response = client.post("/api/validation/rules/non-existent-id/test")
    assert response.status_code == 404


def test_test_validation_rule_invalid_config(client, db_engine):
    """Test testing a validation rule with invalid configuration."""
    # Create a rule with invalid rule type (should fail structure validation)
    rule_data = {
        "rule_type": "format",
        "table": "",  # Empty table name should fail
        "column": "email",
        "config": {},
        "severity": "high"
    }
    
    # This should still create the rule (validation happens in test)
    create_response = client.post("/api/validation/rules", json=rule_data)
    rule_id = create_response.json()["id"]
    
    # Test should fail
    response = client.post(f"/api/validation/rules/{rule_id}/test")
    assert response.status_code == 200
    data = response.json()
    # The test should fail because table name is empty
    assert data["passed"] is False
    assert data["failure_reason"] is not None

