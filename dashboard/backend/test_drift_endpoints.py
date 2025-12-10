"""
Tests for enhanced drift detection endpoints.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from database import DatabaseClient
from models import DriftSummaryResponse, DriftDetailsResponse, DriftImpactResponse


@pytest.fixture
def db_client(monkeypatch):
    """Create a test database client."""
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
                warehouse_type VARCHAR(50),
                environment VARCHAR(50),
                status VARCHAR(20),
                row_count INTEGER,
                column_count INTEGER
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE baselinr_events (
                event_id VARCHAR(36) PRIMARY KEY,
                run_id VARCHAR(36),
                event_type VARCHAR(50),
                table_name VARCHAR(255),
                column_name VARCHAR(255),
                metric_name VARCHAR(255),
                baseline_value REAL,
                current_value REAL,
                change_percent REAL,
                drift_severity VARCHAR(20),
                timestamp TIMESTAMP NOT NULL
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE baselinr_results (
                run_id VARCHAR(36),
                table_name VARCHAR(255),
                column_name VARCHAR(255),
                metric_name VARCHAR(255),
                metric_value REAL
            )
        """))
        
        conn.commit()
    
    return client


@pytest.fixture
def sample_drift_data(db_client):
    """Insert sample drift data for testing."""
    from datetime import timezone
    now = datetime.now(timezone.utc)
    with db_client.engine.connect() as conn:
        # Insert runs
        conn.execute(text("""
            INSERT INTO baselinr_runs (run_id, dataset_name, profiled_at, warehouse_type, row_count)
            VALUES 
                ('run1', 'customers', :timestamp1, 'postgres', 1000),
                ('run2', 'orders', :timestamp2, 'postgres', 2000)
        """), {
            "timestamp1": now - timedelta(days=2),
            "timestamp2": now - timedelta(days=1)
        })
        
        # Insert drift events
        conn.execute(text("""
            INSERT INTO baselinr_events 
            (event_id, run_id, event_type, table_name, column_name, metric_name, 
             baseline_value, current_value, change_percent, drift_severity, timestamp)
            VALUES 
                ('event1', 'run1', 'DataDriftDetected', 'customers', 'age', 'mean', 
                 30.0, 35.0, 16.67, 'high', :timestamp1),
                ('event2', 'run1', 'DataDriftDetected', 'customers', 'email', 'null_percent', 
                 0.0, 5.0, 5.0, 'medium', :timestamp1),
                ('event3', 'run2', 'DataDriftDetected', 'orders', 'amount', 'mean', 
                 100.0, 105.0, 5.0, 'low', :timestamp2)
        """), {
            "timestamp1": now - timedelta(days=1),
            "timestamp2": now
        })
        
        conn.commit()




@pytest.mark.asyncio
async def test_get_drift_summary_empty(db_client):
    """Test drift summary with no data."""
    summary = await db_client.get_drift_summary(days=30)
    assert isinstance(summary, DriftSummaryResponse)
    assert summary.total_events == 0
    assert summary.by_severity["low"] == 0
    assert summary.by_severity["medium"] == 0
    assert summary.by_severity["high"] == 0


@pytest.mark.asyncio
async def test_get_drift_summary_async(db_client, sample_drift_data):
    """Test async drift summary method."""
    summary = await db_client.get_drift_summary(days=30)
    assert isinstance(summary, DriftSummaryResponse)
    assert summary.total_events == 3
    assert summary.by_severity["high"] == 1


@pytest.mark.asyncio
async def test_get_drift_details_not_found(db_client):
    """Test drift details for non-existent event."""
    with pytest.raises(ValueError, match="not found"):
        await db_client.get_drift_details("nonexistent")


@pytest.mark.asyncio
async def test_get_drift_details_async(db_client, sample_drift_data):
    """Test async drift details method."""
    details = await db_client.get_drift_details("event1")
    assert isinstance(details, DriftDetailsResponse)
    assert details.event.event_id == "event1"
    assert details.event.table_name == "customers"


@pytest.mark.asyncio
async def test_get_drift_impact_not_found(db_client):
    """Test drift impact for non-existent event."""
    with pytest.raises(ValueError, match="not found"):
        await db_client.get_drift_impact("nonexistent")


@pytest.mark.asyncio
async def test_get_drift_impact_async(db_client, sample_drift_data):
    """Test async drift impact method."""
    impact = await db_client.get_drift_impact("event1")
    assert isinstance(impact, DriftImpactResponse)
    assert impact.event_id == "event1"
    assert 0.0 <= impact.impact_score <= 1.0

