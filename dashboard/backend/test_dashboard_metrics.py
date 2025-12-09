"""
Tests for enhanced dashboard metrics functionality.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from database import DatabaseClient
from models import MetricsDashboardResponse


@pytest.fixture
def db_client(monkeypatch):
    """Create a test database client."""
    # Use in-memory SQLite for testing
    test_engine = create_engine('sqlite:///:memory:')
    monkeypatch.setenv('BASELINR_DB_URL', 'sqlite:///:memory:')
    
    client = DatabaseClient()
    # Replace the engine with our test engine
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
                column_count INTEGER
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
            CREATE TABLE baselinr_validation_results (
                id INTEGER PRIMARY KEY,
                run_id VARCHAR(36) NOT NULL,
                table_name VARCHAR(255) NOT NULL,
                schema_name VARCHAR(255),
                column_name VARCHAR(255),
                rule_type VARCHAR(50) NOT NULL,
                passed BOOLEAN NOT NULL,
                validated_at TIMESTAMP NOT NULL
            )
        """))
        
        conn.commit()
    
    return client


@pytest.mark.asyncio
async def test_get_dashboard_metrics_basic(db_client):
    """Test basic dashboard metrics calculation."""
    # Insert test data
    with db_client.engine.connect() as conn:
        now = datetime.now()
        conn.execute(text("""
            INSERT INTO baselinr_runs (run_id, dataset_name, profiled_at, row_count, column_count)
            VALUES ('run1', 'table1', :timestamp, 100, 5)
        """), {"timestamp": now})
        conn.commit()
    
    metrics = await db_client.get_dashboard_metrics()
    
    assert isinstance(metrics, MetricsDashboardResponse)
    assert metrics.total_runs == 1
    assert metrics.total_tables == 1
    assert metrics.avg_row_count == 100.0


@pytest.mark.asyncio
async def test_get_dashboard_metrics_with_validation(db_client):
    """Test dashboard metrics with validation data."""
    with db_client.engine.connect() as conn:
        now = datetime.now()
        # Insert run
        conn.execute(text("""
            INSERT INTO baselinr_runs (run_id, dataset_name, profiled_at, row_count)
            VALUES ('run1', 'table1', :timestamp, 100)
        """), {"timestamp": now})
        
        # Insert validation results
        conn.execute(text("""
            INSERT INTO baselinr_validation_results 
            (run_id, table_name, rule_type, passed, validated_at)
            VALUES 
            ('run1', 'table1', 'not_null', true, :timestamp),
            ('run1', 'table1', 'format', true, :timestamp),
            ('run1', 'table1', 'range', false, :timestamp)
        """), {"timestamp": now})
        conn.commit()
    
    metrics = await db_client.get_dashboard_metrics()
    
    assert metrics.total_validation_rules == 3
    assert metrics.failed_validation_rules == 1
    assert metrics.validation_pass_rate is not None
    assert abs(metrics.validation_pass_rate - 66.67) < 1.0  # 2/3 passed


@pytest.mark.asyncio
async def test_get_dashboard_metrics_data_freshness(db_client):
    """Test data freshness calculation."""
    with db_client.engine.connect() as conn:
        # Insert run from 2 hours ago
        two_hours_ago = datetime.now() - timedelta(hours=2)
        conn.execute(text("""
            INSERT INTO baselinr_runs (run_id, dataset_name, profiled_at, row_count)
            VALUES ('run1', 'table1', :timestamp, 100)
        """), {"timestamp": two_hours_ago})
        conn.commit()
    
    metrics = await db_client.get_dashboard_metrics()
    
    assert metrics.data_freshness_hours is not None
    assert 1.5 < metrics.data_freshness_hours < 2.5  # Approximately 2 hours


@pytest.mark.asyncio
async def test_get_dashboard_metrics_run_trend(db_client):
    """Test run trend calculation."""
    with db_client.engine.connect() as conn:
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        # Insert runs on different days
        for i in range(3):
            date = base_date - timedelta(days=i)
            conn.execute(text("""
                INSERT INTO baselinr_runs (run_id, dataset_name, profiled_at, row_count)
                VALUES (:run_id, 'table1', :timestamp, 100)
            """), {"run_id": f"run{i}", "timestamp": date})
        conn.commit()
    
    metrics = await db_client.get_dashboard_metrics()
    
    assert len(metrics.run_trend) == 3
    assert all(trend.value > 0 for trend in metrics.run_trend)


@pytest.mark.asyncio
async def test_get_dashboard_metrics_drift_trend(db_client):
    """Test drift trend calculation."""
    with db_client.engine.connect() as conn:
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        # Insert drift events
        for i in range(2):
            date = base_date - timedelta(days=i)
            conn.execute(text("""
                INSERT INTO baselinr_events (event_id, run_id, event_type, drift_severity, timestamp)
                VALUES (:event_id, 'run1', 'DataDriftDetected', 'high', :timestamp)
            """), {"event_id": f"event{i}", "timestamp": date})
        conn.commit()
    
    metrics = await db_client.get_dashboard_metrics()
    
    assert len(metrics.drift_trend) == 2
    assert metrics.total_drift_events == 2


@pytest.mark.asyncio
async def test_get_dashboard_metrics_active_alerts(db_client):
    """Test active alerts calculation."""
    with db_client.engine.connect() as conn:
        now = datetime.now()
        # Insert failed validation
        conn.execute(text("""
            INSERT INTO baselinr_validation_results 
            (run_id, table_name, rule_type, passed, validated_at)
            VALUES ('run1', 'table1', 'not_null', false, :timestamp)
        """), {"timestamp": now})
        
        # Insert high severity drift
        conn.execute(text("""
            INSERT INTO baselinr_events (event_id, run_id, event_type, drift_severity, timestamp)
            VALUES ('event1', 'run1', 'DataDriftDetected', 'high', :timestamp)
        """), {"timestamp": now})
        conn.commit()
    
    metrics = await db_client.get_dashboard_metrics()
    
    assert metrics.active_alerts == 2  # 1 failed validation + 1 high severity drift


@pytest.mark.asyncio
async def test_get_dashboard_metrics_handles_missing_tables(db_client):
    """Test that metrics calculation handles missing tables gracefully."""
    # Don't create validation_results table
    with db_client.engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS baselinr_validation_results"))
        conn.commit()
    
    # Should not raise an error
    metrics = await db_client.get_dashboard_metrics()
    
    assert metrics.total_validation_rules == 0
    assert metrics.validation_pass_rate is None

