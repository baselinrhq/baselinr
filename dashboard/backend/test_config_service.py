"""
Unit tests for config_service module.
"""

import pytest
import os
import tempfile
import yaml
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from config_service import ConfigService


@pytest.fixture
def mock_db_engine():
    """Mock database engine."""
    return Mock()


@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing."""
    config_data = {
        "environment": "test",
        "source": {
            "type": "postgres",
            "host": "localhost",
            "database": "testdb",
        },
        "storage": {
            "connection": {
                "type": "postgres",
                "host": "localhost",
                "database": "baselinr",
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestConfigService:
    """Test cases for ConfigService."""
    
    def test_load_config_file_not_found(self, mock_db_engine):
        """Test loading config when file doesn't exist."""
        with patch.dict(os.environ, {}, clear=True):
            service = ConfigService(mock_db_engine)
            service._config_path = "/nonexistent/config.yml"
            
            with pytest.raises(FileNotFoundError):
                service.load_config()
    
    @patch('config_service.BASELINR_AVAILABLE', True)
    @patch('config_service.ConfigLoader')
    def test_load_config_success(self, mock_loader, mock_db_engine, temp_config_file):
        """Test successful config loading."""
        mock_config = Mock()
        mock_config.model_dump.return_value = {"environment": "test"}
        mock_loader.load_from_file.return_value = mock_config
        
        with patch.dict(os.environ, {'BASELINR_CONFIG': temp_config_file}):
            service = ConfigService(mock_db_engine)
            config = service.load_config()
            
            assert config == {"environment": "test"}
            mock_loader.load_from_file.assert_called_once()
    
    @patch('config_service.BASELINR_AVAILABLE', True)
    @patch('config_service.BaselinrConfig')
    def test_save_config_success(self, mock_config_class, mock_db_engine, temp_config_file):
        """Test successful config saving."""
        mock_config = Mock()
        mock_config.model_dump.return_value = {"environment": "test"}
        mock_config_class.return_value = mock_config
        
        with patch.dict(os.environ, {'BASELINR_CONFIG': temp_config_file}):
            service = ConfigService(mock_db_engine)
            saved = service.save_config({"environment": "test"})
            
            assert saved == {"environment": "test"}
            mock_config_class.assert_called_once()
    
    @patch('config_service.BASELINR_AVAILABLE', True)
    @patch('config_service.BaselinrConfig')
    def test_validate_config_valid(self, mock_config_class, mock_db_engine):
        """Test config validation with valid config."""
        mock_config_class.return_value = Mock()
        
        service = ConfigService(mock_db_engine)
        is_valid, errors = service.validate_config({"environment": "test"})
        
        assert is_valid is True
        assert errors == []
    
    @patch('config_service.BASELINR_AVAILABLE', True)
    @patch('config_service.BaselinrConfig')
    def test_validate_config_invalid(self, mock_config_class, mock_db_engine):
        """Test config validation with invalid config."""
        from pydantic import ValidationError
        
        error = ValidationError.from_exception(Exception("Invalid config"))
        mock_config_class.side_effect = error
        
        service = ConfigService(mock_db_engine)
        is_valid, errors = service.validate_config({"invalid": "config"})
        
        assert is_valid is False
        assert len(errors) > 0
    
    @patch('config_service.BASELINR_AVAILABLE', True)
    @patch('config_service.create_connector')
    def test_test_connection_success(self, mock_create_connector, mock_db_engine):
        """Test successful connection testing."""
        mock_connector = Mock()
        mock_engine = Mock()
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_connector.engine = mock_engine
        mock_create_connector.return_value = mock_connector
        
        service = ConfigService(mock_db_engine)
        success, message = service.test_connection({
            "type": "postgres",
            "host": "localhost",
            "database": "testdb"
        })
        
        assert success is True
        assert "successful" in message.lower()
    
    @patch('config_service.BASELINR_AVAILABLE', True)
    @patch('config_service.create_connector')
    def test_test_connection_failure(self, mock_create_connector, mock_db_engine):
        """Test connection testing with failure."""
        mock_create_connector.side_effect = Exception("Connection failed")
        
        service = ConfigService(mock_db_engine)
        success, message = service.test_connection({
            "type": "postgres",
            "host": "localhost",
            "database": "testdb"
        })
        
        assert success is False
        assert "failed" in message.lower()
    
    def test_get_config_history_no_db(self):
        """Test getting config history when no database."""
        service = ConfigService(None)
        history = service.get_config_history()
        
        assert history == []
    
    def test_get_config_version_no_db(self):
        """Test getting config version when no database."""
        service = ConfigService(None)
        version = service.get_config_version("test-version")
        
        assert version is None


