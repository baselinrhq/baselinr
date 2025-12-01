"""
Tests for temporal correlation analyzer.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

from baselinr.rca.analysis.temporal_correlator import TemporalCorrelator
from baselinr.rca.models import PipelineRun, CodeDeployment
from baselinr.rca.storage import RCAStorage


@pytest.fixture
def sqlite_engine():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    
    # Create RCA tables
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE baselinr_pipeline_runs (
                run_id VARCHAR(255) PRIMARY KEY,
                pipeline_name VARCHAR(255) NOT NULL,
                pipeline_type VARCHAR(100),
                started_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                duration_seconds REAL,
                status VARCHAR(50) NOT NULL,
                input_row_count INTEGER,
                output_row_count INTEGER,
                git_commit_sha VARCHAR(255),
                git_branch VARCHAR(255),
                affected_tables TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE baselinr_code_deployments (
                deployment_id VARCHAR(255) PRIMARY KEY,
                deployed_at TIMESTAMP NOT NULL,
                git_commit_sha VARCHAR(255),
                git_branch VARCHAR(255),
                changed_files TEXT,
                deployment_type VARCHAR(50),
                affected_pipelines TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        conn.commit()
    
    return engine


def test_temporal_proximity_score(sqlite_engine):
    """Test temporal proximity score calculation."""
    correlator = TemporalCorrelator(sqlite_engine, lookback_window_hours=24)
    
    anomaly_time = datetime.utcnow()
    
    # Event 1 hour before anomaly
    event_time_1h = anomaly_time - timedelta(hours=1)
    score_1h = correlator._calculate_temporal_proximity(event_time_1h, anomaly_time)
    assert 0.7 < score_1h <= 1.0  # Should be high
    
    # Event 6 hours before anomaly
    event_time_6h = anomaly_time - timedelta(hours=6)
    score_6h = correlator._calculate_temporal_proximity(event_time_6h, anomaly_time)
    assert 0.3 < score_6h < score_1h  # Should be lower than 1h
    
    # Event 24 hours before anomaly
    event_time_24h = anomaly_time - timedelta(hours=24)
    score_24h = correlator._calculate_temporal_proximity(event_time_24h, anomaly_time)
    assert 0 < score_24h < score_6h  # Should be very low
    
    # Event after anomaly
    event_time_after = anomaly_time + timedelta(hours=1)
    score_after = correlator._calculate_temporal_proximity(event_time_after, anomaly_time)
    assert score_after >= 0  # Should handle future events


def test_find_correlated_pipeline_runs(sqlite_engine):
    """Test finding correlated pipeline runs."""
    storage = RCAStorage(sqlite_engine)
    correlator = TemporalCorrelator(sqlite_engine, lookback_window_hours=24)
    
    anomaly_time = datetime.utcnow()
    
    # Add a failed pipeline run 2 hours before anomaly
    failed_run = PipelineRun(
        run_id="run_failed",
        pipeline_name="transform_sales",
        pipeline_type="dbt",
        started_at=anomaly_time - timedelta(hours=2),
        completed_at=anomaly_time - timedelta(hours=1, minutes=50),
        duration_seconds=600,
        status="failed",
        affected_tables=["sales", "orders"],
    )
    storage.write_pipeline_run(failed_run)
    
    # Add a successful pipeline run 10 hours before anomaly
    success_run = PipelineRun(
        run_id="run_success",
        pipeline_name="load_data",
        pipeline_type="dbt",
        started_at=anomaly_time - timedelta(hours=10),
        completed_at=anomaly_time - timedelta(hours=9, minutes=50),
        duration_seconds=600,
        status="success",
        affected_tables=["raw_data"],
    )
    storage.write_pipeline_run(success_run)
    
    # Find correlated runs for sales table
    causes = correlator.find_correlated_pipeline_runs(
        anomaly_timestamp=anomaly_time,
        table_name="sales",
        schema_name="public"
    )
    
    assert len(causes) > 0
    
    # Failed run should have higher confidence
    failed_cause = next((c for c in causes if c.cause_id == "run_failed"), None)
    assert failed_cause is not None
    assert failed_cause.cause_type == "pipeline_failure"
    assert failed_cause.confidence_score > 0.5


def test_find_correlated_deployments(sqlite_engine):
    """Test finding correlated code deployments."""
    storage = RCAStorage(sqlite_engine)
    correlator = TemporalCorrelator(sqlite_engine, lookback_window_hours=24)
    
    anomaly_time = datetime.utcnow()
    
    # Add a schema deployment 3 hours before anomaly
    schema_deployment = CodeDeployment(
        deployment_id="deploy_schema",
        deployed_at=anomaly_time - timedelta(hours=3),
        git_commit_sha="abc123",
        git_branch="main",
        changed_files=["models/sales.sql", "schema/migration_001.sql"],
        deployment_type="schema",
        affected_pipelines=["dbt"],
    )
    storage.write_code_deployment(schema_deployment)
    
    # Add a code deployment 20 hours before anomaly
    old_deployment = CodeDeployment(
        deployment_id="deploy_old",
        deployed_at=anomaly_time - timedelta(hours=20),
        git_commit_sha="xyz789",
        git_branch="main",
        changed_files=["utils/helpers.py"],
        deployment_type="code",
        affected_pipelines=[],
    )
    storage.write_code_deployment(old_deployment)
    
    # Find correlated deployments
    causes = correlator.find_correlated_deployments(
        anomaly_timestamp=anomaly_time,
        table_name="sales",
        schema_name="public"
    )
    
    assert len(causes) > 0
    
    # Schema deployment should have higher confidence
    schema_cause = next((c for c in causes if c.cause_id == "deploy_schema"), None)
    assert schema_cause is not None
    assert schema_cause.cause_type == "code_change"


def test_table_relevance_score(sqlite_engine):
    """Test table relevance calculation."""
    correlator = TemporalCorrelator(sqlite_engine)
    
    # Exact match
    score_exact = correlator._calculate_table_relevance("sales", ["sales", "orders"])
    assert score_exact == 1.0
    
    # Partial match
    score_partial = correlator._calculate_table_relevance(
        "user_sales", ["sales", "user_events"]
    )
    assert 0.5 < score_partial < 1.0
    
    # No match
    score_none = correlator._calculate_table_relevance("sales", ["orders", "customers"])
    assert 0.3 <= score_none < 0.5
    
    # Empty list
    score_empty = correlator._calculate_table_relevance("sales", [])
    assert score_empty == 0.3


def test_find_all_correlated_events(sqlite_engine):
    """Test finding all correlated events together."""
    storage = RCAStorage(sqlite_engine)
    correlator = TemporalCorrelator(sqlite_engine, lookback_window_hours=24)
    
    anomaly_time = datetime.utcnow()
    
    # Add pipeline run
    run = PipelineRun(
        run_id="test_run",
        pipeline_name="etl",
        pipeline_type="dbt",
        started_at=anomaly_time - timedelta(hours=1),
        status="failed",
        affected_tables=["sales"],
    )
    storage.write_pipeline_run(run)
    
    # Add deployment
    deployment = CodeDeployment(
        deployment_id="test_deploy",
        deployed_at=anomaly_time - timedelta(hours=2),
        git_commit_sha="abc",
        git_branch="main",
        changed_files=["test.py"],
        deployment_type="code",
    )
    storage.write_code_deployment(deployment)
    
    # Find all events
    pipeline_causes, deployment_causes = correlator.find_all_correlated_events(
        anomaly_timestamp=anomaly_time,
        table_name="sales"
    )
    
    assert len(pipeline_causes) > 0
    assert len(deployment_causes) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
