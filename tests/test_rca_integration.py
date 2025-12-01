"""
Integration tests for end-to-end RCA workflow.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

from baselinr.rca.analysis.root_cause_analyzer import RootCauseAnalyzer
from baselinr.rca.models import PipelineRun, CodeDeployment
from baselinr.rca.service import RCAService
from baselinr.rca.storage import RCAStorage


@pytest.fixture
def full_rca_engine():
    """Create complete RCA database schema."""
    engine = create_engine("sqlite:///:memory:")
    
    with engine.connect() as conn:
        # Pipeline runs table
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
                metadata TEXT
            )
        """))
        
        # Code deployments table
        conn.execute(text("""
            CREATE TABLE baselinr_code_deployments (
                deployment_id VARCHAR(255) PRIMARY KEY,
                deployed_at TIMESTAMP NOT NULL,
                git_commit_sha VARCHAR(255),
                git_branch VARCHAR(255),
                changed_files TEXT,
                deployment_type VARCHAR(50),
                affected_pipelines TEXT,
                metadata TEXT
            )
        """))
        
        # RCA results table
        conn.execute(text("""
            CREATE TABLE baselinr_rca_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anomaly_id VARCHAR(255) NOT NULL UNIQUE,
                database_name VARCHAR(255),
                table_name VARCHAR(255) NOT NULL,
                schema_name VARCHAR(255),
                column_name VARCHAR(255),
                metric_name VARCHAR(100),
                analyzed_at TIMESTAMP NOT NULL,
                rca_status VARCHAR(50) DEFAULT 'analyzed',
                probable_causes TEXT,
                impact_analysis TEXT,
                metadata TEXT
            )
        """))
        
        # Lineage table
        conn.execute(text("""
            CREATE TABLE baselinr_lineage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                downstream_schema VARCHAR(255) NOT NULL,
                downstream_table VARCHAR(255) NOT NULL,
                upstream_schema VARCHAR(255) NOT NULL,
                upstream_table VARCHAR(255) NOT NULL,
                lineage_type VARCHAR(50) NOT NULL,
                provider VARCHAR(50) NOT NULL,
                confidence_score FLOAT DEFAULT 1.0,
                first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """))
        
        # Events table
        conn.execute(text("""
            CREATE TABLE baselinr_events (
                event_id VARCHAR(36) PRIMARY KEY,
                event_type VARCHAR(100) NOT NULL,
                table_name VARCHAR(255),
                column_name VARCHAR(255),
                metric_name VARCHAR(100),
                current_value FLOAT,
                drift_severity VARCHAR(20),
                timestamp TIMESTAMP NOT NULL,
                metadata TEXT
            )
        """))
        
        conn.commit()
    
    return engine


def test_end_to_end_rca_analysis(full_rca_engine):
    """Test complete RCA workflow from anomaly to results."""
    storage = RCAStorage(full_rca_engine)
    analyzer = RootCauseAnalyzer(
        full_rca_engine,
        lookback_window_hours=24,
        max_depth=5,
        enable_pattern_learning=False  # Disabled for this test
    )
    
    anomaly_time = datetime.utcnow()
    
    # Setup scenario: Pipeline failed 2 hours before anomaly
    failed_run = PipelineRun(
        run_id="etl_failed_001",
        pipeline_name="sales_etl",
        pipeline_type="dbt",
        started_at=anomaly_time - timedelta(hours=2),
        completed_at=anomaly_time - timedelta(hours=1, minutes=50),
        duration_seconds=600,
        status="failed",
        affected_tables=["sales", "orders"],
    )
    storage.write_pipeline_run(failed_run)
    
    # Code deployment 1 hour before anomaly
    deployment = CodeDeployment(
        deployment_id="deploy_001",
        deployed_at=anomaly_time - timedelta(hours=1),
        git_commit_sha="abc123def456",
        git_branch="main",
        changed_files=["models/sales.sql"],
        deployment_type="code",
        affected_pipelines=["dbt"],
    )
    storage.write_code_deployment(deployment)
    
    # Add lineage: raw_sales -> sales
    with full_rca_engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO baselinr_lineage 
            (downstream_schema, downstream_table, upstream_schema, upstream_table,
             lineage_type, provider)
            VALUES ('public', 'sales', 'public', 'raw_sales', 'table', 'dbt')
        """))
        conn.commit()
    
    # Perform RCA analysis
    result = analyzer.analyze(
        anomaly_id="anomaly_001",
        table_name="sales",
        anomaly_timestamp=anomaly_time,
        schema_name="public",
        column_name="amount",
        metric_name="mean"
    )
    
    # Verify results
    assert result.anomaly_id == "anomaly_001"
    assert result.table_name == "sales"
    assert len(result.probable_causes) > 0
    
    # Should find pipeline failure as a probable cause
    pipeline_cause = next(
        (c for c in result.probable_causes if c.get("cause_type") == "pipeline_failure"),
        None
    )
    assert pipeline_cause is not None
    assert "sales_etl" in pipeline_cause.get("description", "")
    
    # Should have impact analysis
    assert result.impact_analysis is not None


def test_rca_service_workflow(full_rca_engine):
    """Test RCA service for managing analyses."""
    service = RCAService(
        full_rca_engine,
        auto_analyze=False,
        lookback_window_hours=24,
        enable_pattern_learning=False
    )
    
    storage = RCAStorage(full_rca_engine)
    anomaly_time = datetime.utcnow()
    
    # Add a pipeline run
    run = PipelineRun(
        run_id="run_001",
        pipeline_name="test_pipeline",
        pipeline_type="dbt",
        started_at=anomaly_time - timedelta(hours=1),
        status="failed",
        affected_tables=["test_table"],
    )
    storage.write_pipeline_run(run)
    
    # Analyze anomaly
    result = service.analyze_anomaly(
        anomaly_id="test_anomaly",
        table_name="test_table",
        anomaly_timestamp=anomaly_time,
        schema_name="public"
    )
    
    # Verify result was stored
    stored_result = service.get_rca_result("test_anomaly")
    assert stored_result is not None
    assert stored_result.anomaly_id == "test_anomaly"
    
    # Get statistics
    stats = service.get_rca_statistics()
    assert stats["total_analyses"] >= 1


def test_filter_and_rank_causes(full_rca_engine):
    """Test cause filtering and ranking."""
    analyzer = RootCauseAnalyzer(
        full_rca_engine,
        min_confidence_threshold=0.4,
        max_causes_to_return=3
    )
    
    # Create test causes with different confidence scores
    causes = [
        {"cause_id": "1", "confidence_score": 0.9, "description": "High"},
        {"cause_id": "2", "confidence_score": 0.6, "description": "Medium"},
        {"cause_id": "3", "confidence_score": 0.3, "description": "Low"},  # Below threshold
        {"cause_id": "4", "confidence_score": 0.7, "description": "Medium-High"},
        {"cause_id": "5", "confidence_score": 0.5, "description": "Medium-Low"},
    ]
    
    filtered = analyzer._filter_and_rank_causes(causes)
    
    # Should filter out cause with score 0.3
    assert len(filtered) == 3  # Limited to max_causes_to_return
    
    # Should be sorted by confidence (highest first)
    assert filtered[0]["confidence_score"] == 0.9
    assert filtered[1]["confidence_score"] == 0.7
    assert filtered[2]["confidence_score"] == 0.6
    
    # Low confidence cause should be filtered out
    assert all(c["confidence_score"] >= 0.4 for c in filtered)


def test_rca_summary_generation(full_rca_engine):
    """Test human-readable RCA summary generation."""
    storage = RCAStorage(full_rca_engine)
    analyzer = RootCauseAnalyzer(full_rca_engine)
    
    anomaly_time = datetime.utcnow()
    
    # Add test data
    run = PipelineRun(
        run_id="summary_test",
        pipeline_name="test_etl",
        pipeline_type="dbt",
        started_at=anomaly_time - timedelta(hours=1),
        status="failed",
        affected_tables=["test_table"],
    )
    storage.write_pipeline_run(run)
    
    # Analyze
    result = analyzer.analyze(
        anomaly_id="summary_test",
        table_name="test_table",
        anomaly_timestamp=anomaly_time
    )
    
    # Generate summary
    summary = analyzer.get_rca_summary(result)
    
    # Verify summary contains key information
    assert "Root Cause Analysis" in summary
    assert "test_table" in summary
    assert "probable causes" in summary.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
