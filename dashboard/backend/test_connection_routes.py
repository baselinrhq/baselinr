"""
Integration tests for connection_routes module.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime

from connection_routes import router
from fastapi import FastAPI
from connection_service import ConnectionService


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
def mock_connection_service():
    """Mock connection service."""
    service = Mock(spec=ConnectionService)
    return service


class TestConnectionRoutes:
    """Test cases for connection routes."""
    
    @patch('connection_routes.get_connection_service')
    def test_list_connections_empty(self, mock_get_service, client, mock_connection_service):
        """Test GET /api/config/connections with no connections."""
        mock_connection_service.list_connections.return_value = []
        mock_get_service.return_value = mock_connection_service
        
        response = client.get("/api/config/connections")
        
        assert response.status_code == 200
        assert response.json()["total"] == 0
        assert response.json()["connections"] == []
    
    @patch('connection_routes.get_connection_service')
    def test_list_connections_with_data(self, mock_get_service, client, mock_connection_service):
        """Test GET /api/config/connections with connections."""
        mock_connection_service.list_connections.return_value = [
            {
                "id": "conn-1",
                "name": "Test Connection",
                "connection": {"type": "postgres", "host": "localhost"},
                "created_at": "2024-01-01T00:00:00",
                "updated_at": None,
                "last_tested": None,
                "is_active": True,
            }
        ]
        mock_get_service.return_value = mock_connection_service
        
        response = client.get("/api/config/connections")
        
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert len(response.json()["connections"]) == 1
        assert response.json()["connections"][0]["name"] == "Test Connection"
    
    @patch('connection_routes.get_connection_service')
    def test_get_connection_success(self, mock_get_service, client, mock_connection_service):
        """Test GET /api/config/connections/{id} success."""
        mock_connection_service.get_connection.return_value = {
            "id": "conn-1",
            "name": "Test Connection",
            "connection": {"type": "postgres"},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": None,
            "last_tested": None,
            "is_active": True,
        }
        mock_get_service.return_value = mock_connection_service
        
        response = client.get("/api/config/connections/conn-1")
        
        assert response.status_code == 200
        assert response.json()["id"] == "conn-1"
        assert response.json()["name"] == "Test Connection"
    
    @patch('connection_routes.get_connection_service')
    def test_get_connection_not_found(self, mock_get_service, client, mock_connection_service):
        """Test GET /api/config/connections/{id} when not found."""
        mock_connection_service.get_connection.return_value = None
        mock_get_service.return_value = mock_connection_service
        
        response = client.get("/api/config/connections/nonexistent")
        
        assert response.status_code == 404
    
    @patch('connection_routes.get_connection_service')
    def test_save_connection_success(self, mock_get_service, client, mock_connection_service):
        """Test POST /api/config/connections success."""
        mock_connection_service.save_connection.return_value = {
            "id": "conn-1",
            "name": "New Connection",
            "connection": {"type": "postgres", "host": "localhost"},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": None,
            "last_tested": None,
            "is_active": True,
        }
        mock_get_service.return_value = mock_connection_service
        
        response = client.post("/api/config/connections", json={
            "name": "New Connection",
            "connection": {"type": "postgres", "host": "localhost", "database": "testdb"}
        })
        
        assert response.status_code == 200
        assert response.json()["id"] == "conn-1"
        assert response.json()["connection"]["name"] == "New Connection"
    
    @patch('connection_routes.get_connection_service')
    def test_update_connection_success(self, mock_get_service, client, mock_connection_service):
        """Test PUT /api/config/connections/{id} success."""
        mock_connection_service.update_connection.return_value = {
            "id": "conn-1",
            "name": "Updated Connection",
            "connection": {"type": "postgres", "host": "localhost"},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
            "last_tested": None,
            "is_active": True,
        }
        mock_get_service.return_value = mock_connection_service
        
        response = client.put("/api/config/connections/conn-1", json={
            "name": "Updated Connection",
            "connection": {"type": "postgres", "host": "localhost", "database": "testdb"}
        })
        
        assert response.status_code == 200
        assert response.json()["connection"]["name"] == "Updated Connection"
    
    @patch('connection_routes.get_connection_service')
    def test_update_connection_not_found(self, mock_get_service, client, mock_connection_service):
        """Test PUT /api/config/connections/{id} when not found."""
        mock_connection_service.update_connection.side_effect = ValueError("Connection not found: conn-1")
        mock_get_service.return_value = mock_connection_service
        
        response = client.put("/api/config/connections/conn-1", json={
            "name": "Updated Connection",
            "connection": {"type": "postgres"}
        })
        
        assert response.status_code == 404
    
    @patch('connection_routes.get_connection_service')
    def test_delete_connection_success(self, mock_get_service, client, mock_connection_service):
        """Test DELETE /api/config/connections/{id} success."""
        mock_connection_service.delete_connection.return_value = True
        mock_get_service.return_value = mock_connection_service
        
        response = client.delete("/api/config/connections/conn-1")
        
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()
    
    @patch('connection_routes.get_connection_service')
    def test_delete_connection_not_found(self, mock_get_service, client, mock_connection_service):
        """Test DELETE /api/config/connections/{id} when not found."""
        mock_connection_service.delete_connection.return_value = False
        mock_get_service.return_value = mock_connection_service
        
        response = client.delete("/api/config/connections/nonexistent")
        
        assert response.status_code == 404


