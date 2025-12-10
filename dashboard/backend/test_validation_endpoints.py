"""
Tests for validation dashboard endpoints.
"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text
from database import DatabaseClient
from models import (
    ValidationSummaryResponse,
    ValidationResultsListResponse,
    ValidationResultDetailsResponse,
    ValidationFailureSamplesResponse,
)


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
            CREATE TABLE baselinr_validation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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


@pytest.fixture
def sample_validation_data(db_client):
    """Insert sample validation data for testing."""
    now = datetime.now(timezone.utc)
    with db_client.engine.connect() as conn:
        # Insert runs
        conn.execute(text("""
            INSERT INTO baselinr_runs (run_id, dataset_name, profiled_at, warehouse_type, row_count)
            VALUES 
                ('run1', 'users', :timestamp1, 'postgres', 1000),
                ('run2', 'orders', :timestamp2, 'postgres', 2000)
        """), {
            "timestamp1": now - timedelta(days=2),
            "timestamp2": now - timedelta(days=1)
        })

        # Insert validation results
        conn.execute(text("""
            INSERT INTO baselinr_validation_results 
            (run_id, table_name, schema_name, column_name, rule_type, passed,
             failure_reason, total_rows, failed_rows, failure_rate, severity, validated_at)
            VALUES 
                ('run1', 'users', 'public', 'email', 'format', false,
                 'Invalid format', 1000, 5, 0.5, 'high', :timestamp1),
                ('run1', 'users', 'public', 'age', 'range', true,
                 NULL, 1000, 0, 0.0, 'medium', :timestamp1),
                ('run2', 'orders', 'public', 'amount', 'range', false,
                 'Out of range', 2000, 10, 0.5, 'high', :timestamp2)
        """), {
            "timestamp1": now - timedelta(days=1),
            "timestamp2": now
        })

        conn.commit()


@pytest.mark.asyncio
async def test_get_validation_summary_empty(db_client):
    """Test validation summary with no data."""
    summary = await db_client.get_validation_summary(days=30)
    assert isinstance(summary, ValidationSummaryResponse)
    assert summary.total_validations == 0
    assert summary.passed_count == 0
    assert summary.failed_count == 0
    assert summary.pass_rate == 0.0


@pytest.mark.asyncio
async def test_get_validation_summary_with_data(db_client, sample_validation_data):
    """Test validation summary with sample data."""
    summary = await db_client.get_validation_summary(days=30)
    assert isinstance(summary, ValidationSummaryResponse)
    assert summary.total_validations == 3
    assert summary.passed_count == 1
    assert summary.failed_count == 2
    assert summary.pass_rate > 0.0
    assert 'format' in summary.by_rule_type
    assert 'range' in summary.by_rule_type
    assert 'high' in summary.by_severity


@pytest.mark.asyncio
async def test_get_validation_results_empty(db_client):
    """Test validation results with no data."""
    results = await db_client.get_validation_results(page=1, page_size=50)
    assert isinstance(results, ValidationResultsListResponse)
    assert len(results.results) == 0
    assert results.total == 0


@pytest.mark.asyncio
async def test_get_validation_results_with_data(db_client, sample_validation_data):
    """Test validation results with sample data."""
    results = await db_client.get_validation_results(page=1, page_size=50)
    assert isinstance(results, ValidationResultsListResponse)
    assert len(results.results) == 3
    assert results.total == 3
    assert results.page == 1
    assert results.page_size == 50


@pytest.mark.asyncio
async def test_get_validation_results_with_filters(db_client, sample_validation_data):
    """Test validation results with filters."""
    results = await db_client.get_validation_results(
        table='users',
        rule_type='format',
        passed=False,
        page=1,
        page_size=50
    )
    assert isinstance(results, ValidationResultsListResponse)
    assert len(results.results) == 1
    assert results.results[0].table_name == 'users'
    assert results.results[0].rule_type == 'format'
    assert results.results[0].passed is False


@pytest.mark.asyncio
async def test_get_validation_result_details_not_found(db_client):
    """Test validation result details for non-existent result."""
    with pytest.raises(ValueError, match="not found"):
        await db_client.get_validation_result_details(999)


@pytest.mark.asyncio
async def test_get_validation_result_details(db_client, sample_validation_data):
    """Test validation result details."""
    details = await db_client.get_validation_result_details(1)
    assert isinstance(details, ValidationResultDetailsResponse)
    assert details.result.id == 1
    assert details.result.table_name == 'users'
    assert details.result.rule_type == 'format'


@pytest.mark.asyncio
async def test_get_validation_failure_samples_not_found(db_client):
    """Test failure samples for non-existent result."""
    samples = await db_client.get_validation_failure_samples(999)
    assert isinstance(samples, ValidationFailureSamplesResponse)
    assert samples.result_id == 999
    assert samples.total_failures == 0
    assert len(samples.sample_failures) == 0


@pytest.mark.asyncio
async def test_get_validation_failure_samples(db_client, sample_validation_data):
    """Test failure samples retrieval."""
    samples = await db_client.get_validation_failure_samples(1)
    assert isinstance(samples, ValidationFailureSamplesResponse)
    assert samples.result_id == 1
    # Note: sample_failures may be empty if not stored in the database
    # This is expected behavior as failure samples are optional

