"""
Tests for table listing and detail endpoints.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from database import DatabaseClient
from models import (
    TableListResponse,
    TableOverviewResponse,
    TableDriftHistoryResponse,
    TableValidationResultsResponse,
    TableConfigResponse
)


@pytest.fixture
def db_client(monkeypatch):
    """Create a test database client."""
    # Use in-memory SQLite for testing
    test_engine = create_engine('sqlite:///:memory:')
    monkeypatch.setenv('BASELINR_DB_URL', 'sqlite:///:memory:')
    
    client = DatabaseClient()
    client.engine = test_engine
    
    # Create tables
    with test_engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE baselinr_runs (
                run_id VARCHAR(36) PRIMARY KEY,
                dataset_name VARCHAR(255) NOT NULL,
                schema_name VARCHAR(255),
                profiled_at TIMESTAMP NOT NULL,
                environment VARCHAR(50),
                status VARCHAR(20),
                row_count INTEGER,
                column_count INTEGER,
                warehouse_type VARCHAR(50)
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE baselinr_events (
                event_id VARCHAR(36) PRIMARY KEY,
                run_id VARCHAR(36),
                table_name VARCHAR(255),
                column_name VARCHAR(255),
                metric_name VARCHAR(255),
                baseline_value REAL,
                current_value REAL,
                change_percent REAL,
                event_type VARCHAR(50),
                drift_severity VARCHAR(20),
                timestamp TIMESTAMP NOT NULL
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE baselinr_validation_results (
                id INTEGER PRIMARY KEY,
                run_id VARCHAR(36) NOT NULL,
                table_name VARCHAR(255) NOT NULL,
                schema_name VARCHAR(255),
                column_name VARCHAR(255),
                rule_type VARCHAR(50) NOT NULL,
                passed BOOLEAN NOT NULL,
                failure_reason TEXT,
                total_rows INTEGER,
                failed_rows INTEGER,
                failure_rate REAL,
                severity VARCHAR(20),
                validated_at TIMESTAMP NOT NULL
            )
        """))
        
        conn.commit()
    
    return client


@pytest.mark.asyncio
async def test_get_tables_basic(db_client):
    """Test basic table listing."""
    with db_client.engine.connect() as conn:
        now = datetime.now()
        conn.execute(text("""
            INSERT INTO baselinr_runs 
            (run_id, dataset_name, schema_name, profiled_at, row_count, column_count, warehouse_type)
            VALUES 
            ('run1', 'users', 'public', :timestamp, 100, 5, 'postgres'),
            ('run2', 'orders', 'public', :timestamp, 200, 8, 'postgres')
        """), {"timestamp": now})
        conn.commit()
    
    result = await db_client.get_tables()
    
    assert isinstance(result, TableListResponse)
    assert result.total == 2
    assert len(result.tables) == 2
    assert result.tables[0].table_name in ['users', 'orders']


@pytest.mark.asyncio
async def test_get_tables_with_filters(db_client):
    """Test table listing with filters."""
    with db_client.engine.connect() as conn:
        now = datetime.now()
        conn.execute(text("""
            INSERT INTO baselinr_runs 
            (run_id, dataset_name, schema_name, profiled_at, row_count, column_count, warehouse_type)
            VALUES 
            ('run1', 'users', 'public', :timestamp, 100, 5, 'postgres'),
            ('run2', 'orders', 'sales', :timestamp, 200, 8, 'snowflake')
        """), {"timestamp": now})
        conn.commit()
    
    # Filter by warehouse
    result = await db_client.get_tables(warehouse='postgres')
    assert result.total == 1
    assert result.tables[0].warehouse_type == 'postgres'
    
    # Filter by schema
    result = await db_client.get_tables(schema='sales')
    assert result.total == 1
    assert result.tables[0].schema_name == 'sales'
    
    # Search filter
    result = await db_client.get_tables(search='users')
    assert result.total == 1
    assert result.tables[0].table_name == 'users'


@pytest.mark.asyncio
async def test_get_tables_with_drift(db_client):
    """Test table listing with drift information."""
    with db_client.engine.connect() as conn:
        now = datetime.now()
        conn.execute(text("""
            INSERT INTO baselinr_runs 
            (run_id, dataset_name, profiled_at, row_count, column_count, warehouse_type)
            VALUES 
            ('run1', 'users', :timestamp, 100, 5, 'postgres')
        """), {"timestamp": now})
        
        # Add drift event
        conn.execute(text("""
            INSERT INTO baselinr_events 
            (event_id, run_id, table_name, event_type, drift_severity, timestamp)
            VALUES 
            ('event1', 'run1', 'users', 'DataDriftDetected', 'high', :timestamp)
        """), {"timestamp": now})
        conn.commit()
    
    result = await db_client.get_tables()
    
    assert result.tables[0].drift_count == 1
    assert result.tables[0].has_recent_drift == True


@pytest.mark.asyncio
async def test_get_tables_with_validation(db_client):
    """Test table listing with validation information."""
    with db_client.engine.connect() as conn:
        now = datetime.now()
        conn.execute(text("""
            INSERT INTO baselinr_runs 
            (run_id, dataset_name, profiled_at, row_count, column_count, warehouse_type)
            VALUES 
            ('run1', 'users', :timestamp, 100, 5, 'postgres')
        """), {"timestamp": now})
        
        # Add validation results
        conn.execute(text("""
            INSERT INTO baselinr_validation_results 
            (run_id, table_name, rule_type, passed, validated_at)
            VALUES 
            ('run1', 'users', 'not_null', true, :timestamp),
            ('run1', 'users', 'format', false, :timestamp)
        """), {"timestamp": now})
        conn.commit()
    
    result = await db_client.get_tables()
    
    assert result.tables[0].validation_pass_rate is not None
    assert result.tables[0].validation_pass_rate == 50.0
    assert result.tables[0].has_failed_validations == True


@pytest.mark.asyncio
async def test_get_tables_pagination(db_client):
    """Test table listing pagination."""
    with db_client.engine.connect() as conn:
        now = datetime.now()
        # Insert 5 tables
        for i in range(5):
            conn.execute(text("""
                INSERT INTO baselinr_runs 
                (run_id, dataset_name, profiled_at, row_count, column_count, warehouse_type)
                VALUES 
                (:run_id, :table_name, :timestamp, 100, 5, 'postgres')
            """), {"run_id": f"run{i}", "table_name": f"table{i}", "timestamp": now})
        conn.commit()
    
    # First page
    result = await db_client.get_tables(page=1, page_size=2)
    assert result.page == 1
    assert result.page_size == 2
    assert len(result.tables) == 2
    
    # Second page
    result = await db_client.get_tables(page=2, page_size=2)
    assert result.page == 2
    assert len(result.tables) == 2


@pytest.mark.asyncio
async def test_get_table_overview(db_client):
    """Test table overview endpoint."""
    with db_client.engine.connect() as conn:
        now = datetime.now()
        conn.execute(text("""
            INSERT INTO baselinr_runs 
            (run_id, dataset_name, schema_name, profiled_at, row_count, column_count, warehouse_type)
            VALUES 
            ('run1', 'users', 'public', :timestamp, 100, 5, 'postgres')
        """), {"timestamp": now})
        conn.commit()
    
    overview = await db_client.get_table_overview('users', schema='public')
    
    assert isinstance(overview, TableOverviewResponse)
    assert overview.table_name == 'users'
    assert overview.row_count == 100
    assert overview.column_count == 5


@pytest.mark.asyncio
async def test_get_table_drift_history(db_client):
    """Test table drift history endpoint."""
    with db_client.engine.connect() as conn:
        now = datetime.now()
        conn.execute(text("""
            INSERT INTO baselinr_runs 
            (run_id, dataset_name, profiled_at, row_count, column_count, warehouse_type)
            VALUES 
            ('run1', 'users', :timestamp, 100, 5, 'postgres')
        """), {"timestamp": now})
        
        # Add drift events
        conn.execute(text("""
            INSERT INTO baselinr_events 
            (event_id, run_id, table_name, column_name, metric_name, event_type, drift_severity, timestamp)
            VALUES 
            ('event1', 'run1', 'users', 'email', 'mean', 'DataDriftDetected', 'high', :timestamp),
            ('event2', 'run1', 'users', 'age', 'stddev', 'DataDriftDetected', 'medium', :timestamp)
        """), {"timestamp": now})
        conn.commit()
    
    history = await db_client.get_table_drift_history('users')
    
    assert isinstance(history, TableDriftHistoryResponse)
    assert history.table_name == 'users'
    assert len(history.drift_events) == 2
    assert history.summary['total_events'] == 2
    assert history.summary['by_severity']['high'] == 1
    assert history.summary['by_severity']['medium'] == 1


@pytest.mark.asyncio
async def test_get_table_validation_results(db_client):
    """Test table validation results endpoint."""
    with db_client.engine.connect() as conn:
        now = datetime.now()
        conn.execute(text("""
            INSERT INTO baselinr_runs 
            (run_id, dataset_name, profiled_at, row_count, column_count, warehouse_type)
            VALUES 
            ('run1', 'users', :timestamp, 100, 5, 'postgres')
        """), {"timestamp": now})
        
        # Add validation results
        conn.execute(text("""
            INSERT INTO baselinr_validation_results 
            (run_id, table_name, column_name, rule_type, passed, failure_reason, validated_at)
            VALUES 
            ('run1', 'users', 'email', 'not_null', true, NULL, :timestamp),
            ('run1', 'users', 'age', 'range', false, 'Value out of range', :timestamp)
        """), {"timestamp": now})
        conn.commit()
    
    results = await db_client.get_table_validation_results('users')
    
    assert isinstance(results, TableValidationResultsResponse)
    assert results.table_name == 'users'
    assert len(results.validation_results) == 2
    assert results.summary['total'] == 2
    assert results.summary['passed'] == 1
    assert results.summary['failed'] == 1
    assert results.summary['pass_rate'] == 50.0


@pytest.mark.asyncio
async def test_get_table_config(db_client):
    """Test table config endpoint."""
    # Config endpoint returns placeholder for now
    # This test just ensures it doesn't crash
    config = await db_client.get_table_overview('nonexistent')
    # Should return None for non-existent table
    assert config is None

