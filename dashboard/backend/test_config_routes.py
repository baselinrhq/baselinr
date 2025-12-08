"""
Integration tests for config_routes module.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock

from config_routes import router
from fastapi import FastAPI
from config_service import ConfigService


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_config_service():
    """Mock config service."""
    service = Mock(spec=ConfigService)
    return service


class TestConfigRoutes:
    """Test cases for config routes."""
    
    @patch('config_routes.get_config_service')
    def test_get_config_success(self, mock_get_service, client, mock_config_service):
        """Test GET /api/config success."""
        mock_config_service.load_config.return_value = {"environment": "test"}
        mock_get_service.return_value = mock_config_service
        
        response = client.get("/api/config")
        
        assert response.status_code == 200
        assert response.json()["config"]["environment"] == "test"
    
    @patch('config_routes.get_config_service')
    def test_get_config_not_found(self, mock_get_service, client, mock_config_service):
        """Test GET /api/config when file not found."""
        mock_config_service.load_config.side_effect = FileNotFoundError("Config not found")
        mock_get_service.return_value = mock_config_service
        
        response = client.get("/api/config")
        
        assert response.status_code == 404
    
    @patch('config_routes.get_config_service')
    def test_save_config_success(self, mock_get_service, client, mock_config_service):
        """Test POST /api/config success."""
        mock_config_service.save_config.return_value = {"environment": "test"}
        mock_get_service.return_value = mock_config_service
        
        response = client.post("/api/config", json={"config": {"environment": "test"}})
        
        assert response.status_code == 200
        assert response.json()["config"]["environment"] == "test"
    
    @patch('config_routes.get_config_service')
    def test_save_config_invalid(self, mock_get_service, client, mock_config_service):
        """Test POST /api/config with invalid config."""
        mock_config_service.save_config.side_effect = ValueError("Invalid config")
        mock_get_service.return_value = mock_config_service
        
        response = client.post("/api/config", json={"config": {"invalid": "config"}})
        
        assert response.status_code == 400
    
    @patch('config_routes.get_config_service')
    def test_validate_config_valid(self, mock_get_service, client, mock_config_service):
        """Test POST /api/config/validate with valid config."""
        mock_config_service.validate_config.return_value = (True, [])
        mock_get_service.return_value = mock_config_service
        
        response = client.post("/api/config/validate", json={"config": {"environment": "test"}})
        
        assert response.status_code == 200
        assert response.json()["valid"] is True
        assert response.json()["errors"] == []
    
    @patch('config_routes.get_config_service')
    def test_validate_config_invalid(self, mock_get_service, client, mock_config_service):
        """Test POST /api/config/validate with invalid config."""
        mock_config_service.validate_config.return_value = (False, ["Error 1", "Error 2"])
        mock_get_service.return_value = mock_config_service
        
        response = client.post("/api/config/validate", json={"config": {"invalid": "config"}})
        
        assert response.status_code == 200
        assert response.json()["valid"] is False
        assert len(response.json()["errors"]) == 2
    
    @patch('config_routes.get_config_service')
    def test_test_connection_success(self, mock_get_service, client, mock_config_service):
        """Test POST /api/config/test-connection success."""
        mock_config_service.test_connection.return_value = (True, "Connection successful")
        mock_get_service.return_value = mock_config_service
        
        response = client.post("/api/config/test-connection", json={
            "connection": {"type": "postgres", "host": "localhost"}
        })
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "successful" in response.json()["message"].lower()
    
    @patch('config_routes.get_config_service')
    def test_test_connection_failure(self, mock_get_service, client, mock_config_service):
        """Test POST /api/config/test-connection failure."""
        mock_config_service.test_connection.return_value = (False, "Connection failed")
        mock_get_service.return_value = mock_config_service
        
        response = client.post("/api/config/test-connection", json={
            "connection": {"type": "postgres", "host": "invalid"}
        })
        
        assert response.status_code == 200
        assert response.json()["success"] is False
        assert "failed" in response.json()["message"].lower()
    
    @patch('config_routes.get_config_service')
    def test_get_config_history(self, mock_get_service, client, mock_config_service):
        """Test GET /api/config/history."""
        mock_config_service.get_config_history.return_value = [
            {"version_id": "v1", "created_at": "2024-01-01T00:00:00", "created_by": None, "comment": None}
        ]
        mock_get_service.return_value = mock_config_service
        
        response = client.get("/api/config/history")
        
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert len(response.json()["versions"]) == 1
    
    @patch('config_routes.get_config_service')
    def test_get_config_version_not_found(self, mock_get_service, client, mock_config_service):
        """Test GET /api/config/history/{version_id} when not found."""
        mock_config_service.get_config_version.return_value = None
        mock_get_service.return_value = mock_config_service
        
        response = client.get("/api/config/history/nonexistent")
        
        assert response.status_code == 404


