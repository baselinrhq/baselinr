"""
Integration tests for hook_routes module.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime

from hook_routes import router
from fastapi import FastAPI
from hook_service import HookService


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
def mock_hook_service():
    """Mock hook service."""
    service = Mock(spec=HookService)
    return service


class TestHookRoutes:
    """Test cases for hook routes."""
    
    @patch('hook_routes.get_hook_service')
    def test_list_hooks_empty(self, mock_get_service, client, mock_hook_service):
        """Test GET /api/config/hooks with no hooks."""
        mock_hook_service.list_hooks.return_value = ([], True)
        mock_get_service.return_value = mock_hook_service
        
        response = client.get("/api/config/hooks")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["hooks"] == []
        assert data["hooks_enabled"] is True
    
    @patch('hook_routes.get_hook_service')
    def test_list_hooks_with_data(self, mock_get_service, client, mock_hook_service):
        """Test GET /api/config/hooks with hooks."""
        mock_hook_service.list_hooks.return_value = (
            [
                {
                    "id": "0",
                    "hook": {"type": "logging", "enabled": True, "log_level": "INFO"}
                },
                {
                    "id": "1",
                    "hook": {"type": "slack", "enabled": True, "webhook_url": "https://hooks.slack.com/test"}
                }
            ],
            True
        )
        mock_get_service.return_value = mock_hook_service
        
        response = client.get("/api/config/hooks")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["hooks"]) == 2
        assert data["hooks"][0]["id"] == "0"
        assert data["hooks"][0]["hook"]["type"] == "logging"
        assert data["hooks"][1]["id"] == "1"
        assert data["hooks"][1]["hook"]["type"] == "slack"
    
    @patch('hook_routes.get_hook_service')
    def test_get_hook_success(self, mock_get_service, client, mock_hook_service):
        """Test GET /api/config/hooks/{id} success."""
        mock_hook_service.get_hook.return_value = {
            "id": "0",
            "hook": {"type": "logging", "enabled": True, "log_level": "INFO"}
        }
        mock_get_service.return_value = mock_hook_service
        
        response = client.get("/api/config/hooks/0")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "0"
        assert data["hook"]["type"] == "logging"
    
    @patch('hook_routes.get_hook_service')
    def test_get_hook_not_found(self, mock_get_service, client, mock_hook_service):
        """Test GET /api/config/hooks/{id} when not found."""
        mock_hook_service.get_hook.return_value = None
        mock_get_service.return_value = mock_hook_service
        
        response = client.get("/api/config/hooks/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @patch('hook_routes.get_hook_service')
    def test_create_hook_success(self, mock_get_service, client, mock_hook_service):
        """Test POST /api/config/hooks success."""
        mock_hook_service.save_hook.return_value = {
            "id": "0",
            "hook": {"type": "logging", "enabled": True, "log_level": "INFO"}
        }
        mock_get_service.return_value = mock_hook_service
        
        response = client.post(
            "/api/config/hooks",
            json={"hook": {"type": "logging", "enabled": True, "log_level": "INFO"}}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "0"
        assert data["hook"]["hook"]["type"] == "logging"
        mock_hook_service.save_hook.assert_called_once_with(None, {"type": "logging", "enabled": True, "log_level": "INFO"})
    
    @patch('hook_routes.get_hook_service')
    def test_create_hook_invalid(self, mock_get_service, client, mock_hook_service):
        """Test POST /api/config/hooks with invalid data."""
        mock_hook_service.save_hook.side_effect = ValueError("Invalid hook configuration")
        mock_get_service.return_value = mock_hook_service
        
        response = client.post(
            "/api/config/hooks",
            json={"hook": {"type": "invalid"}}
        )
        
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()
    
    @patch('hook_routes.get_hook_service')
    def test_update_hook_success(self, mock_get_service, client, mock_hook_service):
        """Test PUT /api/config/hooks/{id} success."""
        mock_hook_service.save_hook.return_value = {
            "id": "0",
            "hook": {"type": "logging", "enabled": True, "log_level": "DEBUG"}
        }
        mock_get_service.return_value = mock_hook_service
        
        response = client.put(
            "/api/config/hooks/0",
            json={"hook": {"type": "logging", "enabled": True, "log_level": "DEBUG"}}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "0"
        assert data["hook"]["hook"]["log_level"] == "DEBUG"
        mock_hook_service.save_hook.assert_called_once_with("0", {"type": "logging", "enabled": True, "log_level": "DEBUG"})
    
    @patch('hook_routes.get_hook_service')
    def test_delete_hook_success(self, mock_get_service, client, mock_hook_service):
        """Test DELETE /api/config/hooks/{id} success."""
        mock_hook_service.delete_hook.return_value = True
        mock_get_service.return_value = mock_hook_service
        
        response = client.delete("/api/config/hooks/0")
        
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()
        mock_hook_service.delete_hook.assert_called_once_with("0")
    
    @patch('hook_routes.get_hook_service')
    def test_delete_hook_not_found(self, mock_get_service, client, mock_hook_service):
        """Test DELETE /api/config/hooks/{id} when not found."""
        mock_hook_service.delete_hook.return_value = False
        mock_get_service.return_value = mock_hook_service
        
        response = client.delete("/api/config/hooks/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @patch('hook_routes.get_hook_service')
    def test_test_hook_success(self, mock_get_service, client, mock_hook_service):
        """Test POST /api/config/hooks/{id}/test success."""
        mock_hook_service.get_hook.return_value = {
            "id": "0",
            "hook": {"type": "logging", "enabled": True, "log_level": "INFO"}
        }
        mock_hook_service.test_hook.return_value = (
            True,
            "Hook test successful",
            None,
            {"event_type": "DataDriftDetected", "timestamp": "2024-01-01T00:00:00"}
        )
        mock_get_service.return_value = mock_hook_service
        
        response = client.post("/api/config/hooks/0/test", json={})
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "successful" in data["message"].lower()
        assert data["error"] is None
        assert data["test_event"] is not None
    
    @patch('hook_routes.get_hook_service')
    def test_test_hook_with_config(self, mock_get_service, client, mock_hook_service):
        """Test POST /api/config/hooks/{id}/test with provided hook config."""
        mock_hook_service.test_hook.return_value = (
            True,
            "Hook test successful",
            None,
            {"event_type": "DataDriftDetected", "timestamp": "2024-01-01T00:00:00"}
        )
        mock_get_service.return_value = mock_hook_service
        
        response = client.post(
            "/api/config/hooks/0/test",
            json={"hook": {"type": "logging", "enabled": True, "log_level": "INFO"}}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_hook_service.test_hook.assert_called_once_with({"type": "logging", "enabled": True, "log_level": "INFO"})
    
    @patch('hook_routes.get_hook_service')
    def test_test_hook_failure(self, mock_get_service, client, mock_hook_service):
        """Test POST /api/config/hooks/{id}/test with failure."""
        mock_hook_service.get_hook.return_value = {
            "id": "0",
            "hook": {"type": "slack", "enabled": True, "webhook_url": "invalid"}
        }
        mock_hook_service.test_hook.return_value = (
            False,
            "Hook test failed: Connection error",
            "Connection error",
            {"event_type": "DataDriftDetected", "timestamp": "2024-01-01T00:00:00"}
        )
        mock_get_service.return_value = mock_hook_service
        
        response = client.post("/api/config/hooks/0/test", json={})
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "failed" in data["message"].lower()
        assert data["error"] is not None
    
    @patch('hook_routes.get_hook_service')
    def test_set_hooks_enabled(self, mock_get_service, client, mock_hook_service):
        """Test PUT /api/config/hooks/enabled."""
        mock_hook_service.set_hooks_enabled.return_value = True
        mock_get_service.return_value = mock_hook_service
        
        response = client.put("/api/config/hooks/enabled?enabled=false")
        
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        mock_hook_service.set_hooks_enabled.assert_called_once_with(False)

