"""
Integration tests for discovery_routes module.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock

from discovery_routes import router
from fastapi import FastAPI
from discovery_service import DiscoveryService
from config_service import ConfigService
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
def mock_discovery_service():
    """Mock discovery service."""
    service = Mock(spec=DiscoveryService)
    return service


@pytest.fixture
def mock_config_service():
    """Mock config service."""
    service = Mock(spec=ConfigService)
    return service


@pytest.fixture
def mock_connection_service():
    """Mock connection service."""
    service = Mock(spec=ConnectionService)
    return service


@pytest.fixture
def sample_connection():
    """Sample connection data."""
    return {
        "id": "test-conn-1",
        "name": "Test Connection",
        "connection": {
            "type": "postgres",
            "host": "localhost",
            "database": "testdb"
        }
    }


class TestDiscoveryRoutes:
    """Test cases for discovery routes."""
    
    @patch('discovery_routes.get_discovery_service')
    @patch('discovery_routes.get_connection_service')
    @patch('discovery_routes.get_config_service')
    def test_discover_tables_success(self, mock_get_config, mock_get_conn, mock_get_discovery, 
                                     client, mock_config_service, mock_connection_service, 
                                     mock_discovery_service, sample_connection):
        """Test GET /api/tables/discover success."""
        mock_config_service.load_config.return_value = {"source": sample_connection["connection"]}
        mock_get_config.return_value = mock_config_service
        mock_get_conn.return_value = mock_connection_service
        mock_get_discovery.return_value = mock_discovery_service
        
        mock_discovery_service.discover_tables.return_value = {
            "tables": [
                {
                    "schema": "public",
                    "table": "users",
                    "table_type": "table",
                    "row_count": None,
                    "database": "testdb",
                    "tags": []
                }
            ],
            "total": 1,
            "schemas": ["public"]
        }
        
        response = client.get("/api/tables/discover")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["tables"]) == 1
        assert data["tables"][0]["table"] == "users"
    
    @patch('discovery_routes.get_discovery_service')
    @patch('discovery_routes.get_connection_service')
    @patch('discovery_routes.get_config_service')
    def test_discover_tables_with_connection_id(self, mock_get_config, mock_get_conn, mock_get_discovery,
                                                client, mock_config_service, mock_connection_service,
                                                mock_discovery_service, sample_connection):
        """Test GET /api/tables/discover with connection_id."""
        mock_connection_service.get_connection.return_value = sample_connection
        mock_get_config.return_value = mock_config_service
        mock_get_conn.return_value = mock_connection_service
        mock_get_discovery.return_value = mock_discovery_service
        
        mock_discovery_service.discover_tables.return_value = {
            "tables": [],
            "total": 0,
            "schemas": []
        }
        
        response = client.get("/api/tables/discover?connection_id=test-conn-1")
        
        assert response.status_code == 200
        mock_connection_service.get_connection.assert_called_once_with("test-conn-1")
    
    @patch('discovery_routes.get_discovery_service')
    @patch('discovery_routes.get_connection_service')
    @patch('discovery_routes.get_config_service')
    def test_discover_tables_connection_not_found(self, mock_get_config, mock_get_conn, mock_get_discovery,
                                                  client, mock_config_service, mock_connection_service,
                                                  mock_discovery_service):
        """Test GET /api/tables/discover with invalid connection_id."""
        mock_connection_service.get_connection.return_value = None
        mock_get_config.return_value = mock_config_service
        mock_get_conn.return_value = mock_connection_service
        mock_get_discovery.return_value = mock_discovery_service
        
        response = client.get("/api/tables/discover?connection_id=invalid-id")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @patch('discovery_routes.get_discovery_service')
    @patch('discovery_routes.get_connection_service')
    @patch('discovery_routes.get_config_service')
    def test_discover_tables_no_connection(self, mock_get_config, mock_get_conn, mock_get_discovery,
                                           client, mock_config_service, mock_connection_service,
                                           mock_discovery_service):
        """Test GET /api/tables/discover with no connection available."""
        mock_config_service.load_config.return_value = {}  # No source
        mock_get_config.return_value = mock_config_service
        mock_get_conn.return_value = mock_connection_service
        mock_get_discovery.return_value = mock_discovery_service
        
        response = client.get("/api/tables/discover")
        
        assert response.status_code == 400
        assert "connection" in response.json()["detail"].lower()
    
    @patch('discovery_routes.get_discovery_service')
    @patch('discovery_routes.get_connection_service')
    @patch('discovery_routes.get_config_service')
    def test_preview_pattern_success(self, mock_get_config, mock_get_conn, mock_get_discovery,
                                     client, mock_config_service, mock_connection_service,
                                     mock_discovery_service, sample_connection):
        """Test POST /api/tables/discover success."""
        mock_config_service.load_config.return_value = {"source": sample_connection["connection"]}
        mock_get_config.return_value = mock_config_service
        mock_get_conn.return_value = mock_connection_service
        mock_get_discovery.return_value = mock_discovery_service
        
        mock_discovery_service.preview_pattern.return_value = {
            "tables": [
                {
                    "schema": "public",
                    "table": "users",
                    "table_type": "table",
                    "database": "testdb",
                    "tags": []
                }
            ],
            "total": 1,
            "pattern": "user*"
        }
        
        response = client.post("/api/tables/discover", json={
            "pattern": "user*",
            "schema": "public",
            "pattern_type": "wildcard"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["pattern"] == "user*"
    
    @patch('discovery_routes.get_discovery_service')
    @patch('discovery_routes.get_connection_service')
    @patch('discovery_routes.get_config_service')
    def test_get_table_preview_success(self, mock_get_config, mock_get_conn, mock_get_discovery,
                                      client, mock_config_service, mock_connection_service,
                                      mock_discovery_service, sample_connection):
        """Test GET /api/tables/{schema}/{table}/preview success."""
        mock_config_service.load_config.return_value = {"source": sample_connection["connection"]}
        mock_get_config.return_value = mock_config_service
        mock_get_conn.return_value = mock_connection_service
        mock_get_discovery.return_value = mock_discovery_service
        
        mock_discovery_service.get_table_metadata.return_value = {
            "schema": "public",
            "table": "users",
            "columns": [
                {"name": "id", "type": "INTEGER", "nullable": False},
                {"name": "name", "type": "VARCHAR", "nullable": True}
            ],
            "row_count": 100,
            "table_type": "table"
        }
        
        response = client.get("/api/tables/public/users/preview")
        
        assert response.status_code == 200
        data = response.json()
        assert data["schema"] == "public"
        assert data["table"] == "users"
        assert len(data["columns"]) == 2
        assert data["columns"][0]["name"] == "id"
    
    @patch('discovery_routes.get_discovery_service')
    @patch('discovery_routes.get_connection_service')
    @patch('discovery_routes.get_config_service')
    def test_get_table_preview_not_found(self, mock_get_config, mock_get_conn, mock_get_discovery,
                                        client, mock_config_service, mock_connection_service,
                                        mock_discovery_service, sample_connection):
        """Test GET /api/tables/{schema}/{table}/preview when table not found."""
        mock_config_service.load_config.return_value = {"source": sample_connection["connection"]}
        mock_get_config.return_value = mock_config_service
        mock_get_conn.return_value = mock_connection_service
        mock_get_discovery.return_value = mock_discovery_service
        
        mock_discovery_service.get_table_metadata.side_effect = FileNotFoundError("Table not found")
        
        response = client.get("/api/tables/public/nonexistent/preview")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @patch('discovery_routes.get_discovery_service')
    @patch('discovery_routes.get_connection_service')
    @patch('discovery_routes.get_config_service')
    def test_discover_tables_error(self, mock_get_config, mock_get_conn, mock_get_discovery,
                                   client, mock_config_service, mock_connection_service,
                                   mock_discovery_service, sample_connection):
        """Test GET /api/tables/discover with service error."""
        mock_config_service.load_config.return_value = {"source": sample_connection["connection"]}
        mock_get_config.return_value = mock_config_service
        mock_get_conn.return_value = mock_connection_service
        mock_get_discovery.return_value = mock_discovery_service
        
        mock_discovery_service.discover_tables.side_effect = Exception("Discovery failed")
        
        response = client.get("/api/tables/discover")
        
        assert response.status_code == 500
        assert "failed" in response.json()["detail"].lower()

