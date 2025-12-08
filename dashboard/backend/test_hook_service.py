"""
Unit tests for hook_service module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from hook_service import HookService
from config_service import ConfigService


@pytest.fixture
def mock_config_service():
    """Mock config service."""
    service = Mock(spec=ConfigService)
    return service


@pytest.fixture
def hook_service(mock_config_service):
    """Create HookService instance with mocked config service."""
    return HookService(mock_config_service)


class TestHookService:
    """Test cases for HookService."""
    
    def test_list_hooks_empty(self, hook_service, mock_config_service):
        """Test listing hooks when none exist."""
        mock_config_service.load_config.return_value = {
            "hooks": {
                "enabled": True,
                "hooks": []
            }
        }
        
        hooks_list, hooks_enabled = hook_service.list_hooks()
        
        assert hooks_list == []
        assert hooks_enabled is True
    
    def test_list_hooks_with_data(self, hook_service, mock_config_service):
        """Test listing hooks with data."""
        mock_config_service.load_config.return_value = {
            "hooks": {
                "enabled": True,
                "hooks": [
                    {"type": "logging", "enabled": True, "log_level": "INFO"},
                    {"type": "slack", "enabled": True, "webhook_url": "https://hooks.slack.com/test"},
                ]
            }
        }
        
        hooks_list, hooks_enabled = hook_service.list_hooks()
        
        assert len(hooks_list) == 2
        assert hooks_list[0]["id"] == "0"
        assert hooks_list[0]["hook"]["type"] == "logging"
        assert hooks_list[1]["id"] == "1"
        assert hooks_list[1]["hook"]["type"] == "slack"
        assert hooks_enabled is True
    
    def test_get_hook_success(self, hook_service, mock_config_service):
        """Test getting a specific hook."""
        mock_config_service.load_config.return_value = {
            "hooks": {
                "enabled": True,
                "hooks": [
                    {"type": "logging", "enabled": True},
                    {"type": "slack", "enabled": True},
                ]
            }
        }
        
        hook_data = hook_service.get_hook("0")
        
        assert hook_data is not None
        assert hook_data["id"] == "0"
        assert hook_data["hook"]["type"] == "logging"
    
    def test_get_hook_not_found(self, hook_service, mock_config_service):
        """Test getting a hook that doesn't exist."""
        mock_config_service.load_config.return_value = {
            "hooks": {
                "enabled": True,
                "hooks": []
            }
        }
        
        hook_data = hook_service.get_hook("0")
        
        assert hook_data is None
    
    def test_get_hook_invalid_id(self, hook_service, mock_config_service):
        """Test getting a hook with invalid ID."""
        mock_config_service.load_config.return_value = {
            "hooks": {
                "enabled": True,
                "hooks": []
            }
        }
        
        hook_data = hook_service.get_hook("invalid")
        
        assert hook_data is None
    
    @patch('hook_service.BASELINR_AVAILABLE', True)
    @patch('hook_service.HookConfig')
    def test_save_hook_create_new(self, mock_hook_config, hook_service, mock_config_service):
        """Test creating a new hook."""
        mock_config_service.load_config.return_value = {
            "hooks": {
                "enabled": True,
                "hooks": []
            }
        }
        
        # Mock HookConfig validation
        mock_hook = Mock()
        mock_hook.model_dump.return_value = {"type": "logging", "enabled": True, "log_level": "INFO"}
        mock_hook_config.return_value = mock_hook
        
        # Mock save_config
        mock_config_service.save_config.return_value = {
            "hooks": {
                "enabled": True,
                "hooks": [
                    {"type": "logging", "enabled": True, "log_level": "INFO"}
                ]
            }
        }
        
        saved = hook_service.save_hook(None, {"type": "logging", "enabled": True, "log_level": "INFO"})
        
        assert saved["id"] == "0"
        assert saved["hook"]["type"] == "logging"
        mock_config_service.save_config.assert_called_once()
    
    @patch('hook_service.BASELINR_AVAILABLE', True)
    @patch('hook_service.HookConfig')
    def test_save_hook_update_existing(self, mock_hook_config, hook_service, mock_config_service):
        """Test updating an existing hook."""
        mock_config_service.load_config.return_value = {
            "hooks": {
                "enabled": True,
                "hooks": [
                    {"type": "logging", "enabled": True, "log_level": "INFO"}
                ]
            }
        }
        
        # Mock HookConfig validation
        mock_hook = Mock()
        mock_hook.model_dump.return_value = {"type": "logging", "enabled": True, "log_level": "DEBUG"}
        mock_hook_config.return_value = mock_hook
        
        # Mock save_config
        mock_config_service.save_config.return_value = {
            "hooks": {
                "enabled": True,
                "hooks": [
                    {"type": "logging", "enabled": True, "log_level": "DEBUG"}
                ]
            }
        }
        
        saved = hook_service.save_hook("0", {"type": "logging", "enabled": True, "log_level": "DEBUG"})
        
        assert saved["id"] == "0"
        assert saved["hook"]["log_level"] == "DEBUG"
        mock_config_service.save_config.assert_called_once()
    
    @patch('hook_service.BASELINR_AVAILABLE', True)
    @patch('hook_service.HookConfig')
    def test_save_hook_invalid_config(self, mock_hook_config, hook_service, mock_config_service):
        """Test saving hook with invalid configuration."""
        mock_hook_config.side_effect = ValueError("Invalid hook type")
        
        with pytest.raises(ValueError, match="Invalid hook configuration"):
            hook_service.save_hook(None, {"type": "invalid"})
    
    def test_delete_hook_success(self, hook_service, mock_config_service):
        """Test deleting a hook."""
        mock_config_service.load_config.return_value = {
            "hooks": {
                "enabled": True,
                "hooks": [
                    {"type": "logging", "enabled": True},
                    {"type": "slack", "enabled": True},
                ]
            }
        }
        
        mock_config_service.save_config.return_value = {
            "hooks": {
                "enabled": True,
                "hooks": [
                    {"type": "slack", "enabled": True},
                ]
            }
        }
        
        result = hook_service.delete_hook("0")
        
        assert result is True
        mock_config_service.save_config.assert_called_once()
    
    def test_delete_hook_not_found(self, hook_service, mock_config_service):
        """Test deleting a hook that doesn't exist."""
        mock_config_service.load_config.return_value = {
            "hooks": {
                "enabled": True,
                "hooks": []
            }
        }
        
        result = hook_service.delete_hook("0")
        
        assert result is False
    
    def test_set_hooks_enabled(self, hook_service, mock_config_service):
        """Test setting hooks enabled status."""
        mock_config_service.load_config.return_value = {
            "hooks": {
                "enabled": True,
                "hooks": []
            }
        }
        
        mock_config_service.save_config.return_value = {
            "hooks": {
                "enabled": False,
                "hooks": []
            }
        }
        
        result = hook_service.set_hooks_enabled(False)
        
        assert result is True
        mock_config_service.save_config.assert_called_once()
        # Verify the config was saved with enabled=False
        call_args = mock_config_service.save_config.call_args[0][0]
        assert call_args["hooks"]["enabled"] is False
    
    @patch('hook_service.BASELINR_AVAILABLE', True)
    @patch('hook_service._create_hook')
    @patch('hook_service.DataDriftDetected')
    def test_test_hook_success(self, mock_event_class, mock_create_hook, hook_service, mock_config_service):
        """Test hook testing with success."""
        # Mock hook instance
        mock_hook = Mock()
        mock_hook.handle_event.return_value = None
        mock_create_hook.return_value = mock_hook
        
        # Mock event
        mock_event = Mock()
        mock_event.to_dict.return_value = {"event_type": "DataDriftDetected", "timestamp": "2024-01-01T00:00:00"}
        mock_event_class.return_value = mock_event
        
        success, message, error, test_event = hook_service.test_hook({
            "type": "logging",
            "enabled": True,
            "log_level": "INFO"
        })
        
        assert success is True
        assert "successful" in message.lower()
        assert error is None
        assert test_event is not None
        mock_hook.handle_event.assert_called_once()
    
    @patch('hook_service.BASELINR_AVAILABLE', True)
    @patch('hook_service._create_hook')
    @patch('hook_service.DataDriftDetected')
    def test_test_hook_failure(self, mock_event_class, mock_create_hook, hook_service, mock_config_service):
        """Test hook testing with failure."""
        # Mock hook instance that raises an error
        mock_hook = Mock()
        mock_hook.handle_event.side_effect = Exception("Connection failed")
        mock_create_hook.return_value = mock_hook
        
        # Mock event
        mock_event = Mock()
        mock_event.to_dict.return_value = {"event_type": "DataDriftDetected", "timestamp": "2024-01-01T00:00:00"}
        mock_event_class.return_value = mock_event
        
        success, message, error, test_event = hook_service.test_hook({
            "type": "slack",
            "enabled": True,
            "webhook_url": "https://invalid-url"
        })
        
        assert success is False
        assert "failed" in message.lower()
        assert error is not None
        assert test_event is not None
    
    @patch('hook_service.BASELINR_AVAILABLE', True)
    @patch('hook_service.HookConfig')
    def test_test_hook_invalid_config(self, mock_hook_config, hook_service, mock_config_service):
        """Test hook testing with invalid configuration."""
        mock_hook_config.side_effect = ValueError("Invalid hook type")
        
        success, message, error, test_event = hook_service.test_hook({
            "type": "invalid"
        })
        
        assert success is False
        assert "invalid" in message.lower()
        assert error is not None
        assert test_event is None

