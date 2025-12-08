"""
Unit tests for discovery_service module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from discovery_service import DiscoveryService


@pytest.fixture
def mock_db_engine():
    """Mock database engine."""
    return Mock()


@pytest.fixture
def mock_connector():
    """Mock connector."""
    connector = Mock()
    connector.list_schemas.return_value = ["public", "schema1"]
    connector.list_tables.return_value = ["users", "orders", "products"]
    connector.engine = Mock()
    return connector


@pytest.fixture
def sample_connection():
    """Sample connection configuration."""
    return {
        "type": "postgres",
        "host": "localhost",
        "database": "testdb",
        "username": "testuser",
        "password": "testpass"
    }


class TestDiscoveryService:
    """Test cases for DiscoveryService."""
    
    @patch('discovery_service.BASELINR_AVAILABLE', True)
    @patch('discovery_service.create_connector')
    @patch('discovery_service.inspect')
    def test_discover_tables_basic(self, mock_inspect, mock_create_connector, mock_db_engine, mock_connector, sample_connection):
        """Test basic table discovery."""
        mock_create_connector.return_value = mock_connector
        
        # Mock inspector
        mock_inspector = Mock()
        mock_inspector.get_view_names.return_value = []
        mock_inspect.return_value = mock_inspector
        
        service = DiscoveryService(mock_db_engine)
        result = service.discover_tables({}, sample_connection)
        
        assert "tables" in result
        assert "total" in result
        assert "schemas" in result
        assert result["total"] > 0
    
    @patch('discovery_service.BASELINR_AVAILABLE', True)
    @patch('discovery_service.create_connector')
    @patch('discovery_service.inspect')
    def test_discover_tables_with_pattern(self, mock_inspect, mock_create_connector, mock_db_engine, mock_connector, sample_connection):
        """Test table discovery with pattern filter."""
        mock_create_connector.return_value = mock_connector
        
        # Mock inspector
        mock_inspector = Mock()
        mock_inspector.get_view_names.return_value = []
        mock_inspect.return_value = mock_inspector
        
        service = DiscoveryService(mock_db_engine)
        filters = {"pattern": "user*", "pattern_type": "wildcard"}
        result = service.discover_tables(filters, sample_connection)
        
        assert "tables" in result
        assert result["total"] >= 0
    
    @patch('discovery_service.BASELINR_AVAILABLE', True)
    @patch('discovery_service.create_connector')
    @patch('discovery_service.inspect')
    def test_discover_tables_with_schema_filter(self, mock_inspect, mock_create_connector, mock_db_engine, mock_connector, sample_connection):
        """Test table discovery with schema filter."""
        mock_create_connector.return_value = mock_connector
        
        # Mock inspector
        mock_inspector = Mock()
        mock_inspector.get_view_names.return_value = []
        mock_inspect.return_value = mock_inspector
        
        service = DiscoveryService(mock_db_engine)
        filters = {"schemas": ["public"]}
        result = service.discover_tables(filters, sample_connection)
        
        assert "tables" in result
        assert "public" in result["schemas"]
    
    @patch('discovery_service.BASELINR_AVAILABLE', True)
    @patch('discovery_service.create_connector')
    def test_discover_tables_connection_error(self, mock_create_connector, mock_db_engine, sample_connection):
        """Test table discovery with connection error."""
        mock_create_connector.side_effect = Exception("Connection failed")
        
        service = DiscoveryService(mock_db_engine)
        
        with pytest.raises(RuntimeError) as exc_info:
            service.discover_tables({}, sample_connection)
        
        assert "Failed to discover tables" in str(exc_info.value)
    
    @patch('discovery_service.BASELINR_AVAILABLE', True)
    @patch('discovery_service.create_connector')
    @patch('discovery_service.inspect')
    def test_preview_pattern_explicit_table(self, mock_inspect, mock_create_connector, mock_db_engine, mock_connector, sample_connection):
        """Test pattern preview with explicit table."""
        mock_create_connector.return_value = mock_connector
        
        # Mock inspector
        mock_inspector = Mock()
        mock_inspector.get_view_names.return_value = []
        mock_inspect.return_value = mock_inspector
        
        service = DiscoveryService(mock_db_engine)
        pattern = {"table": "users", "schema": "public"}
        result = service.preview_pattern(pattern, sample_connection)
        
        assert "tables" in result
        assert "total" in result
        assert "pattern" in result
    
    @patch('discovery_service.BASELINR_AVAILABLE', True)
    @patch('discovery_service.create_connector')
    @patch('discovery_service.inspect')
    def test_preview_pattern_wildcard(self, mock_inspect, mock_create_connector, mock_db_engine, mock_connector, sample_connection):
        """Test pattern preview with wildcard pattern."""
        mock_create_connector.return_value = mock_connector
        
        # Mock inspector
        mock_inspector = Mock()
        mock_inspector.get_view_names.return_value = []
        mock_inspect.return_value = mock_inspector
        
        service = DiscoveryService(mock_db_engine)
        pattern = {"pattern": "user*", "schema": "public", "pattern_type": "wildcard"}
        result = service.preview_pattern(pattern, sample_connection)
        
        assert "tables" in result
        assert "pattern" in result
    
    @patch('discovery_service.BASELINR_AVAILABLE', True)
    @patch('discovery_service.create_connector')
    def test_preview_pattern_connection_error(self, mock_create_connector, mock_db_engine, sample_connection):
        """Test pattern preview with connection error."""
        mock_create_connector.side_effect = Exception("Connection failed")
        
        service = DiscoveryService(mock_db_engine)
        pattern = {"pattern": "user*", "schema": "public"}
        
        with pytest.raises(RuntimeError) as exc_info:
            service.preview_pattern(pattern, sample_connection)
        
        assert "Failed to preview pattern" in str(exc_info.value)
    
    @patch('discovery_service.BASELINR_AVAILABLE', True)
    @patch('discovery_service.create_connector')
    @patch('discovery_service.inspect')
    def test_get_table_metadata_success(self, mock_inspect, mock_create_connector, mock_db_engine, sample_connection):
        """Test getting table metadata successfully."""
        # Mock table object
        mock_table = Mock()
        mock_col1 = Mock()
        mock_col1.name = "id"
        mock_col1.type = "INTEGER"
        mock_col1.nullable = False
        mock_col2 = Mock()
        mock_col2.name = "name"
        mock_col2.type = "VARCHAR"
        mock_col2.nullable = True
        mock_table.columns = [mock_col1, mock_col2]
        
        mock_connector = Mock()
        mock_connector.get_table.return_value = mock_table
        mock_connector.engine = Mock()
        mock_create_connector.return_value = mock_connector
        
        # Mock inspector
        mock_inspector = Mock()
        mock_inspector.get_view_names.return_value = []
        mock_inspect.return_value = mock_inspector
        
        # Mock row count query
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.scalar.return_value = 100
        mock_conn.execute.return_value = mock_result
        mock_connector.engine.connect.return_value.__enter__.return_value = mock_conn
        
        service = DiscoveryService(mock_db_engine)
        result = service.get_table_metadata("public", "users", sample_connection)
        
        assert result["schema"] == "public"
        assert result["table"] == "users"
        assert len(result["columns"]) == 2
        assert result["columns"][0]["name"] == "id"
        assert result["columns"][1]["name"] == "name"
    
    @patch('discovery_service.BASELINR_AVAILABLE', True)
    @patch('discovery_service.create_connector')
    def test_get_table_metadata_not_found(self, mock_create_connector, mock_db_engine, sample_connection):
        """Test getting table metadata when table not found."""
        mock_connector = Mock()
        mock_connector.get_table.side_effect = Exception("Table 'users' does not exist")
        mock_create_connector.return_value = mock_connector
        
        service = DiscoveryService(mock_db_engine)
        
        with pytest.raises(FileNotFoundError):
            service.get_table_metadata("public", "nonexistent", sample_connection)
    
    @patch('discovery_service.BASELINR_AVAILABLE', True)
    @patch('discovery_service.create_connector')
    def test_get_table_metadata_connection_error(self, mock_create_connector, mock_db_engine, sample_connection):
        """Test getting table metadata with connection error."""
        mock_create_connector.side_effect = Exception("Connection failed")
        
        service = DiscoveryService(mock_db_engine)
        
        with pytest.raises(RuntimeError) as exc_info:
            service.get_table_metadata("public", "users", sample_connection)
        
        assert "Failed to get table metadata" in str(exc_info.value)
    
    def test_discover_tables_baselinr_not_available(self, mock_db_engine, sample_connection):
        """Test discovery when baselinr modules not available."""
        with patch('discovery_service.BASELINR_AVAILABLE', False):
            service = DiscoveryService(mock_db_engine)
            
            with pytest.raises(RuntimeError) as exc_info:
                service.discover_tables({}, sample_connection)
            
            assert "Baselinr modules not available" in str(exc_info.value)

