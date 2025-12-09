"""
Tests for enhanced runs functionality.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from database import DatabaseClient
from models import RunHistoryResponse, RunComparisonResponse


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
                run_id VARCHAR(36) NOT NULL,
                dataset_name VARCHAR(255) NOT NULL,
                schema_name VARCHAR(255),
                profiled_at TIMESTAMP NOT NULL,
                environment VARCHAR(50),
                status VARCHAR(20),
                row_count INTEGER,
                column_count INTEGER,
                PRIMARY KEY (run_id, dataset_name)
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE baselinr_events (
                event_id VARCHAR(36) PRIMARY KEY,
                run_id VARCHAR(36),
                event_type VARCHAR(50),
                drift_severity VARCHAR(20),
                timestamp TIMESTAMP NOT NULL
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE baselinr_results (
                id INTEGER PRIMARY KEY,
                run_id VARCHAR(36) NOT NULL,
                dataset_name VARCHAR(255) NOT NULL,
                schema_name VARCHAR(255),
                column_name VARCHAR(255) NOT NULL,
                column_type VARCHAR(100),
                metric_name VARCHAR(100) NOT NULL,
                metric_value TEXT,
                profiled_at TIMESTAMP NOT NULL
            )
        """))
        
        conn.commit()
    
    return client


@pytest.fixture
def sample_runs(db_client):
    """Insert sample runs for testing."""
    now = datetime.utcnow()
    
    runs = [
        ('run1', 'table1', 'public', now - timedelta(days=1), 'completed', 1000, 10),
        ('run2', 'table1', 'public', now - timedelta(days=2), 'completed', 2000, 15),
        ('run3', 'table2', 'public', now - timedelta(days=3), 'failed', 500, 5),
        ('run4', 'table1', 'schema1', now - timedelta(days=4), 'completed', 1500, 12),
    ]
    
    with db_client.engine.connect() as conn:
        for run in runs:
            conn.execute(text("""
                INSERT INTO baselinr_runs 
                (run_id, dataset_name, schema_name, profiled_at, status, row_count, column_count)
                VALUES (:run_id, :dataset_name, :schema_name, :profiled_at, :status, :row_count, :column_count)
            """), {
                'run_id': run[0],
                'dataset_name': run[1],
                'schema_name': run[2],
                'profiled_at': run[3],
                'status': run[4],
                'row_count': run[5],
                'column_count': run[6],
            })
        conn.commit()
    
    return runs


@pytest.mark.asyncio
async def test_get_runs_basic(db_client, sample_runs):
    """Test basic get_runs functionality."""
    runs = await db_client.get_runs()
    
    assert len(runs) == 4
    assert all(isinstance(run, RunHistoryResponse) for run in runs)
    assert runs[0].run_id == 'run1'  # Most recent first


@pytest.mark.asyncio
async def test_get_runs_with_filters(db_client, sample_runs):
    """Test get_runs with various filters."""
    # Filter by schema
    runs = await db_client.get_runs(schema='public')
    assert len(runs) == 3
    
    # Filter by table
    runs = await db_client.get_runs(table='table1')
    assert len(runs) == 3
    
    # Filter by status
    runs = await db_client.get_runs(status='failed')
    assert len(runs) == 1
    assert runs[0].status == 'failed'
    
    # Filter by date range
    start_date = datetime.utcnow() - timedelta(days=2)
    runs = await db_client.get_runs(start_date=start_date)
    assert len(runs) == 2


@pytest.mark.asyncio
async def test_get_runs_date_range(db_client, sample_runs):
    """Test get_runs with date range filtering."""
    now = datetime.utcnow()
    start_date = now - timedelta(days=2)
    end_date = now - timedelta(days=1)
    
    runs = await db_client.get_runs(start_date=start_date, end_date=end_date)
    assert len(runs) == 1
    assert runs[0].run_id == 'run1'


@pytest.mark.asyncio
async def test_get_runs_sorting(db_client, sample_runs):
    """Test get_runs with sorting."""
    # Sort by row_count ascending
    runs = await db_client.get_runs(sort_by='row_count', sort_order='asc')
    assert runs[0].row_count == 500
    
    # Sort by row_count descending
    runs = await db_client.get_runs(sort_by='row_count', sort_order='desc')
    assert runs[0].row_count == 2000
    
    # Sort by status
    runs = await db_client.get_runs(sort_by='status', sort_order='asc')
    assert runs[0].status == 'completed'


@pytest.mark.asyncio
async def test_get_runs_multi_status(db_client, sample_runs):
    """Test get_runs with multiple statuses."""
    runs = await db_client.get_runs(status='completed,failed')
    assert len(runs) == 4  # All runs


@pytest.mark.asyncio
async def test_compare_runs(db_client, sample_runs):
    """Test compare_runs functionality."""
    # Insert metrics for comparison
    with db_client.engine.connect() as conn:
        # Run 1 metrics
        conn.execute(text("""
            INSERT INTO baselinr_results 
            (run_id, dataset_name, column_name, metric_name, metric_value, profiled_at)
            VALUES 
            ('run1', 'table1', 'col1', 'null_count', '10', :now),
            ('run1', 'table1', 'col1', 'mean', '100.5', :now),
            ('run1', 'table1', 'col2', 'null_count', '5', :now)
        """), {'now': datetime.utcnow()})
        
        # Run 2 metrics
        conn.execute(text("""
            INSERT INTO baselinr_results 
            (run_id, dataset_name, column_name, metric_name, metric_value, profiled_at)
            VALUES 
            ('run2', 'table1', 'col1', 'null_count', '20', :now),
            ('run2', 'table1', 'col1', 'mean', '200.5', :now),
            ('run2', 'table1', 'col2', 'null_count', '10', :now)
        """), {'now': datetime.utcnow()})
        
        conn.commit()
    
    comparison = await db_client.compare_runs(['run1', 'run2'])
    
    assert isinstance(comparison, RunComparisonResponse)
    assert len(comparison.runs) == 2
    assert comparison.comparison['row_count_diff'] == 1000  # 2000 - 1000
    assert comparison.comparison['column_count_diff'] == 5  # 15 - 10
    assert 'col1' in comparison.comparison['common_columns']
    assert 'col2' in comparison.comparison['common_columns']


@pytest.mark.asyncio
async def test_compare_runs_too_few(db_client):
    """Test compare_runs with too few runs."""
    with pytest.raises(ValueError, match="At least 2 run IDs required"):
        await db_client.compare_runs(['run1'])


@pytest.mark.asyncio
async def test_compare_runs_too_many(db_client):
    """Test compare_runs with too many runs."""
    with pytest.raises(ValueError, match="Maximum 5 runs"):
        await db_client.compare_runs(['run1', 'run2', 'run3', 'run4', 'run5', 'run6'])


@pytest.mark.asyncio
async def test_compare_runs_not_found(db_client):
    """Test compare_runs with non-existent runs."""
    with pytest.raises(ValueError, match="Could not find at least 2 valid runs"):
        await db_client.compare_runs(['nonexistent1', 'nonexistent2'])

