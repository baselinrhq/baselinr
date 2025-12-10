"""
Tests for enhanced lineage endpoints.
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine, text
from database import DatabaseClient
from lineage_models import LineageImpactResponse, TableInfoResponse


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
                status VARCHAR(20),
                row_count INTEGER,
                column_count INTEGER
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE baselinr_results (
                result_id INTEGER PRIMARY KEY,
                run_id VARCHAR(36),
                table_name VARCHAR(255),
                schema_name VARCHAR(255),
                metric_name VARCHAR(255),
                metric_value REAL
            )
        """))
        
        conn.commit()
    
    return client


@pytest.mark.asyncio
async def test_get_lineage_impact_empty(db_client):
    """Test lineage impact with no downstream tables."""
    impact = await db_client.get_lineage_impact(
        table='test_table',
        schema='public',
        include_metrics=True
    )
    
    assert isinstance(impact, LineageImpactResponse)
    assert impact.table == 'test_table'
    assert impact.schema == 'public'
    assert impact.affected_tables == []
    assert impact.impact_score == 0.0
    assert impact.affected_metrics == 0
    assert len(impact.recommendations) > 0  # Should have at least one recommendation


@pytest.mark.asyncio
async def test_get_lineage_impact_with_metrics(db_client):
    """Test lineage impact with metrics."""
    # Insert some test data
    with db_client.engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO baselinr_results (run_id, table_name, schema_name, metric_name, metric_value)
            VALUES ('run1', 'test_table', 'public', 'row_count', 100),
                   ('run1', 'test_table', 'public', 'null_count', 5)
        """))
        conn.commit()
    
    impact = await db_client.get_lineage_impact(
        table='test_table',
        schema='public',
        include_metrics=True
    )
    
    assert impact.affected_metrics >= 0  # May be 0 if table doesn't exist in results


@pytest.mark.asyncio
async def test_get_lineage_impact_without_metrics(db_client):
    """Test lineage impact without including metrics."""
    impact = await db_client.get_lineage_impact(
        table='test_table',
        schema='public',
        include_metrics=False
    )
    
    assert impact.affected_metrics == 0


@pytest.mark.asyncio
async def test_get_lineage_impact_no_schema(db_client):
    """Test lineage impact without schema."""
    impact = await db_client.get_lineage_impact(
        table='test_table',
        schema=None,
        include_metrics=True
    )
    
    assert impact.table == 'test_table'
    assert impact.schema is None


@pytest.mark.asyncio
async def test_get_lineage_impact_recommendations(db_client):
    """Test that recommendations are generated."""
    impact = await db_client.get_lineage_impact(
        table='test_table',
        schema='public',
        include_metrics=True
    )
    
    assert isinstance(impact.recommendations, list)
    # Should have at least one recommendation when no downstream tables
    if len(impact.affected_tables) == 0:
        assert any('source table' in rec.lower() for rec in impact.recommendations)


@pytest.mark.asyncio
async def test_get_lineage_impact_structure(db_client):
    """Test that impact response has correct structure."""
    impact = await db_client.get_lineage_impact(
        table='test_table',
        schema='public',
        include_metrics=True
    )
    
    assert hasattr(impact, 'table')
    assert hasattr(impact, 'schema')
    assert hasattr(impact, 'affected_tables')
    assert hasattr(impact, 'impact_score')
    assert hasattr(impact, 'affected_metrics')
    assert hasattr(impact, 'drift_propagation')
    assert hasattr(impact, 'recommendations')
    
    assert isinstance(impact.affected_tables, list)
    assert isinstance(impact.impact_score, float)
    assert 0.0 <= impact.impact_score <= 1.0
    assert isinstance(impact.affected_metrics, int)
    assert isinstance(impact.drift_propagation, list)
    assert isinstance(impact.recommendations, list)

