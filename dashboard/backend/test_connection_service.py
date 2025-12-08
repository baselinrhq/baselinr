"""
Unit tests for connection_service module.
"""

import pytest
import json
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from connection_service import ConnectionService


@pytest.fixture
def mock_db_engine():
    """Mock database engine."""
    engine = Mock()
    
    # Mock connection context manager
    conn = Mock()
    conn.execute.return_value.fetchone.return_value = [False]  # Table doesn't exist
    conn.execute.return_value.rowcount = 0
    engine.connect.return_value.__enter__.return_value = conn
    engine.connect.return_value.__exit__.return_value = None
    
    return engine


@pytest.fixture
def mock_fernet():
    """Mock Fernet encryption."""
    with patch('connection_service.Fernet') as mock_fernet_class:
        mock_fernet = Mock()
        mock_fernet.encrypt.return_value = b'encrypted_password'
        mock_fernet.decrypt.return_value = b'plain_password'
        mock_fernet_class.return_value = mock_fernet
        yield mock_fernet


class TestConnectionService:
    """Test cases for ConnectionService."""
    
    @patch('connection_service.CRYPTOGRAPHY_AVAILABLE', True)
    @patch.dict('os.environ', {'BASELINR_ENCRYPTION_KEY': 'test_key'})
    def test_encrypt_password(self, mock_db_engine, mock_fernet):
        """Test password encryption."""
        service = ConnectionService(mock_db_engine)
        encrypted = service._encrypt_password("test_password")
        
        assert encrypted == 'encrypted_password'
        mock_fernet.encrypt.assert_called_once()
    
    @patch('connection_service.CRYPTOGRAPHY_AVAILABLE', True)
    @patch.dict('os.environ', {'BASELINR_ENCRYPTION_KEY': 'test_key'})
    def test_decrypt_password(self, mock_db_engine, mock_fernet):
        """Test password decryption."""
        service = ConnectionService(mock_db_engine)
        decrypted = service._decrypt_password("encrypted_password")
        
        assert decrypted == 'plain_password'
        mock_fernet.decrypt.assert_called_once()
    
    @patch('connection_service.CRYPTOGRAPHY_AVAILABLE', False)
    def test_encrypt_password_no_crypto(self, mock_db_engine):
        """Test password encryption when cryptography not available."""
        service = ConnectionService(mock_db_engine)
        encrypted = service._encrypt_password("test_password")
        
        assert encrypted == "test_password"  # Should return as-is
    
    def test_list_connections_empty(self, mock_db_engine):
        """Test listing connections when none exist."""
        conn = Mock()
        conn.execute.return_value = []
        mock_db_engine.connect.return_value.__enter__.return_value = conn
        
        service = ConnectionService(mock_db_engine)
        connections = service.list_connections()
        
        assert connections == []
    
    def test_list_connections_with_data(self, mock_db_engine):
        """Test listing connections with data."""
        from unittest.mock import MagicMock
        
        conn = Mock()
        row1 = Mock()
        row1.__getitem__.side_effect = lambda x: {
            0: "conn-1",
            1: "Test Connection",
            2: json.dumps({"type": "postgres", "password": "encrypted"}),
            3: datetime(2024, 1, 1),
            4: None,
            5: None,
        }[x]
        row2 = Mock()
        row2.__getitem__.side_effect = lambda x: {
            0: "conn-2",
            1: "Another Connection",
            2: json.dumps({"type": "mysql", "password": "encrypted2"}),
            3: datetime(2024, 1, 2),
            4: None,
            5: None,
        }[x]
        
        result = Mock()
        result.__iter__.return_value = iter([row1, row2])
        conn.execute.return_value = result
        
        mock_db_engine.connect.return_value.__enter__.return_value = conn
        
        service = ConnectionService(mock_db_engine)
        service._decrypt_connection = lambda x: {**x, "password": "decrypted"}
        
        connections = service.list_connections()
        
        assert len(connections) == 2
        assert connections[0]["id"] == "conn-1"
        assert connections[0]["name"] == "Test Connection"
    
    def test_get_connection_not_found(self, mock_db_engine):
        """Test getting connection that doesn't exist."""
        conn = Mock()
        conn.execute.return_value.fetchone.return_value = None
        mock_db_engine.connect.return_value.__enter__.return_value = conn
        
        service = ConnectionService(mock_db_engine)
        connection = service.get_connection("nonexistent")
        
        assert connection is None
    
    def test_save_connection_success(self, mock_db_engine):
        """Test saving a new connection."""
        conn = Mock()
        conn.execute.return_value.rowcount = 1
        mock_db_engine.connect.return_value.__enter__.return_value = conn
        
        service = ConnectionService(mock_db_engine)
        service._encrypt_connection = lambda x: {**x, "password": "encrypted"}
        
        saved = service.save_connection("Test Connection", {
            "type": "postgres",
            "host": "localhost",
            "database": "testdb",
            "password": "plain"
        })
        
        assert saved["name"] == "Test Connection"
        assert "id" in saved
        assert saved["connection"]["type"] == "postgres"
    
    def test_update_connection_not_found(self, mock_db_engine):
        """Test updating connection that doesn't exist."""
        service = ConnectionService(mock_db_engine)
        service.get_connection = lambda x: None
        
        with pytest.raises(ValueError, match="not found"):
            service.update_connection("nonexistent", "New Name", {"type": "postgres"})
    
    def test_delete_connection_success(self, mock_db_engine):
        """Test deleting a connection."""
        conn = Mock()
        conn.execute.return_value.rowcount = 1
        mock_db_engine.connect.return_value.__enter__.return_value = conn
        
        service = ConnectionService(mock_db_engine)
        deleted = service.delete_connection("conn-1")
        
        assert deleted is True
    
    def test_delete_connection_not_found(self, mock_db_engine):
        """Test deleting connection that doesn't exist."""
        conn = Mock()
        conn.execute.return_value.rowcount = 0
        mock_db_engine.connect.return_value.__enter__.return_value = conn
        
        service = ConnectionService(mock_db_engine)
        deleted = service.delete_connection("nonexistent")
        
        assert deleted is False


