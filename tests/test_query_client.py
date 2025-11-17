"""Tests for metadata query client."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from profilemesh.query import MetadataQueryClient


@pytest.fixture
def temp_db_engine():
    """Create temporary SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")

    # Create schema
    with engine.connect() as conn:
        conn.execute(
            text(
                """
            CREATE TABLE profilemesh_runs (
                run_id VARCHAR(36),
                dataset_name VARCHAR(255),
                schema_name VARCHAR(255),
                profiled_at TIMESTAMP,
                environment VARCHAR(50),
                status VARCHAR(20),
                row_count INTEGER,
                column_count INTEGER,
                PRIMARY KEY (run_id, dataset_name)
            )
        """
            )
        )

        conn.execute(
            text(
                """
            CREATE TABLE profilemesh_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id VARCHAR(36),
                dataset_name VARCHAR(255),
                schema_name VARCHAR(255),
                column_name VARCHAR(255),
                column_type VARCHAR(100),
                metric_name VARCHAR(100),
                metric_value TEXT,
                profiled_at TIMESTAMP
            )
        """
            )
        )

        conn.execute(
            text(
                """
            CREATE TABLE profilemesh_events (
                event_id VARCHAR(36) PRIMARY KEY,
                event_type VARCHAR(100),
                table_name VARCHAR(255),
                column_name VARCHAR(255),
                metric_name VARCHAR(100),
                baseline_value FLOAT,
                current_value FLOAT,
                change_percent FLOAT,
                drift_severity VARCHAR(20),
                timestamp TIMESTAMP
            )
        """
            )
        )

        conn.commit()

    yield engine
    engine.dispose()


@pytest.fixture
def query_client(temp_db_engine):
    """Create query client."""
    return MetadataQueryClient(temp_db_engine)


@pytest.fixture
def sample_runs(temp_db_engine):
    """Create sample run data."""
    with temp_db_engine.connect() as conn:
        now = datetime.utcnow()

        # Insert sample runs
        runs = [
            (
                "run-1",
                "customers",
                "public",
                now - timedelta(days=1),
                "production",
                "completed",
                1000,
                10,
            ),
            (
                "run-2",
                "customers",
                "public",
                now - timedelta(days=2),
                "production",
                "completed",
                990,
                10,
            ),
            (
                "run-3",
                "orders",
                "public",
                now - timedelta(days=1),
                "production",
                "completed",
                5000,
                15,
            ),
            (
                "run-4",
                "orders",
                "public",
                now - timedelta(days=10),
                "staging",
                "failed",
                None,
                None,
            ),
        ]

        for run in runs:
            conn.execute(
                text(
                    """
                INSERT INTO profilemesh_runs 
                (run_id, dataset_name, schema_name, profiled_at, environment, status, row_count, column_count)
                VALUES (:run_id, :dataset_name, :schema_name, :profiled_at, :environment, :status, :row_count, :column_count)
            """
                ),
                {
                    "run_id": run[0],
                    "dataset_name": run[1],
                    "schema_name": run[2],
                    "profiled_at": run[3],
                    "environment": run[4],
                    "status": run[5],
                    "row_count": run[6],
                    "column_count": run[7],
                },
            )

        conn.commit()


@pytest.fixture
def sample_results(temp_db_engine):
    """Create sample results data."""
    with temp_db_engine.connect() as conn:
        now = datetime.utcnow()

        # Insert sample metrics
        results = [
            ("run-1", "customers", "public", "email", "VARCHAR", "null_count", "10", now),
            ("run-1", "customers", "public", "email", "VARCHAR", "null_percent", "1.0", now),
            ("run-1", "customers", "public", "age", "INTEGER", "null_count", "5", now),
            ("run-1", "customers", "public", "age", "INTEGER", "mean", "35.2", now),
        ]

        for result in results:
            conn.execute(
                text(
                    """
                INSERT INTO profilemesh_results
                (run_id, dataset_name, schema_name, column_name, column_type, metric_name, metric_value, profiled_at)
                VALUES (:run_id, :dataset_name, :schema_name, :column_name, :column_type, :metric_name, :metric_value, :profiled_at)
            """
                ),
                {
                    "run_id": result[0],
                    "dataset_name": result[1],
                    "schema_name": result[2],
                    "column_name": result[3],
                    "column_type": result[4],
                    "metric_name": result[5],
                    "metric_value": result[6],
                    "profiled_at": result[7],
                },
            )

        conn.commit()


@pytest.fixture
def sample_drift(temp_db_engine):
    """Create sample drift events."""
    with temp_db_engine.connect() as conn:
        now = datetime.utcnow()

        events = [
            (
                "event-1",
                "drift_detected",
                "customers",
                "email",
                "null_percent",
                1.0,
                2.5,
                150.0,
                "high",
                now - timedelta(hours=1),
            ),
            (
                "event-2",
                "drift_detected",
                "orders",
                "total",
                "mean",
                100.0,
                120.0,
                20.0,
                "medium",
                now - timedelta(hours=2),
            ),
            (
                "event-3",
                "drift_detected",
                "customers",
                "age",
                "mean",
                35.0,
                35.5,
                1.4,
                "low",
                now - timedelta(days=5),
            ),
        ]

        for event in events:
            conn.execute(
                text(
                    """
                INSERT INTO profilemesh_events
                (event_id, event_type, table_name, column_name, metric_name, baseline_value, current_value, change_percent, drift_severity, timestamp)
                VALUES (:event_id, :event_type, :table_name, :column_name, :metric_name, :baseline_value, :current_value, :change_percent, :drift_severity, :timestamp)
            """
                ),
                {
                    "event_id": event[0],
                    "event_type": event[1],
                    "table_name": event[2],
                    "column_name": event[3],
                    "metric_name": event[4],
                    "baseline_value": event[5],
                    "current_value": event[6],
                    "change_percent": event[7],
                    "drift_severity": event[8],
                    "timestamp": event[9],
                },
            )

        conn.commit()


def test_query_runs_all(query_client, sample_runs):
    """Test querying all runs."""
    runs = query_client.query_runs()
    assert len(runs) == 4


def test_query_runs_by_table(query_client, sample_runs):
    """Test filtering runs by table."""
    runs = query_client.query_runs(table="customers")
    assert len(runs) == 2
    assert all(run.dataset_name == "customers" for run in runs)


def test_query_runs_by_schema(query_client, sample_runs):
    """Test filtering runs by schema."""
    runs = query_client.query_runs(schema="public")
    assert len(runs) == 4


def test_query_runs_by_status(query_client, sample_runs):
    """Test filtering runs by status."""
    runs = query_client.query_runs(status="completed")
    assert len(runs) == 3
    assert all(run.status == "completed" for run in runs)

    failed_runs = query_client.query_runs(status="failed")
    assert len(failed_runs) == 1
    assert failed_runs[0].status == "failed"


def test_query_runs_by_environment(query_client, sample_runs):
    """Test filtering runs by environment."""
    runs = query_client.query_runs(environment="production")
    assert len(runs) == 3
    assert all(run.environment == "production" for run in runs)


def test_query_runs_by_days(query_client, sample_runs):
    """Test filtering runs by days."""
    runs = query_client.query_runs(days=3)
    # Should include runs from last 3 days (not the 10-day old one)
    assert len(runs) == 3


def test_query_runs_pagination(query_client, sample_runs):
    """Test run pagination."""
    # First page
    runs_page1 = query_client.query_runs(limit=2, offset=0)
    assert len(runs_page1) == 2

    # Second page
    runs_page2 = query_client.query_runs(limit=2, offset=2)
    assert len(runs_page2) == 2

    # Verify no overlap
    page1_ids = {run.run_id for run in runs_page1}
    page2_ids = {run.run_id for run in runs_page2}
    assert len(page1_ids & page2_ids) == 0


def test_query_runs_combined_filters(query_client, sample_runs):
    """Test combining multiple filters."""
    runs = query_client.query_runs(
        table="customers", status="completed", environment="production", days=5
    )
    assert len(runs) == 2
    assert all(
        run.dataset_name == "customers"
        and run.status == "completed"
        and run.environment == "production"
        for run in runs
    )


def test_query_run_details(query_client, sample_runs, sample_results):
    """Test querying specific run details."""
    details = query_client.query_run_details("run-1", "customers")

    assert details is not None
    assert details["run_id"] == "run-1"
    assert details["dataset_name"] == "customers"
    assert details["row_count"] == 1000
    assert details["column_count"] == 10
    assert len(details["columns"]) == 2  # email and age


def test_query_run_details_not_found(query_client):
    """Test querying non-existent run."""
    details = query_client.query_run_details("nonexistent")
    assert details is None


def test_query_run_details_metrics_structure(query_client, sample_runs, sample_results):
    """Test run details metrics structure."""
    details = query_client.query_run_details("run-1", "customers")

    # Find email column
    email_col = next(c for c in details["columns"] if c["column_name"] == "email")
    assert email_col["column_type"] == "VARCHAR"
    assert "null_count" in email_col["metrics"]
    assert "null_percent" in email_col["metrics"]
    assert email_col["metrics"]["null_count"] == "10"
    assert email_col["metrics"]["null_percent"] == "1.0"


def test_query_drift_events_all(query_client, sample_drift):
    """Test querying all drift events."""
    events = query_client.query_drift_events()
    assert len(events) == 3


def test_query_drift_by_table(query_client, sample_drift):
    """Test filtering drift by table."""
    events = query_client.query_drift_events(table="customers")
    assert len(events) == 2
    assert all(event.table_name == "customers" for event in events)


def test_query_drift_by_severity(query_client, sample_drift):
    """Test filtering drift by severity."""
    high_events = query_client.query_drift_events(severity="high")
    assert len(high_events) == 1
    assert high_events[0].drift_severity == "high"

    medium_events = query_client.query_drift_events(severity="medium")
    assert len(medium_events) == 1


def test_query_drift_by_days(query_client, sample_drift):
    """Test filtering drift by days."""
    recent = query_client.query_drift_events(days=1)
    # Should only include events from last 24 hours
    assert len(recent) == 2


def test_query_drift_pagination(query_client, sample_drift):
    """Test drift event pagination."""
    events_page1 = query_client.query_drift_events(limit=2, offset=0)
    assert len(events_page1) == 2

    events_page2 = query_client.query_drift_events(limit=2, offset=2)
    assert len(events_page2) == 1


def test_query_table_history(query_client, sample_runs):
    """Test querying table history."""
    history = query_client.query_table_history("customers")

    assert history["table_name"] == "customers"
    assert history["run_count"] == 2
    assert len(history["runs"]) == 2


def test_query_table_history_with_schema(query_client, sample_runs):
    """Test querying table history with schema filter."""
    history = query_client.query_table_history("customers", schema_name="public")

    assert history["schema_name"] == "public"
    assert history["run_count"] == 2


def test_query_table_history_with_days(query_client, sample_runs):
    """Test querying table history with time limit."""
    history = query_client.query_table_history("orders", days=5)

    # Should only include recent run (not 10-day old one)
    assert history["run_count"] == 1


def test_run_summary_to_dict(query_client, sample_runs):
    """Test RunSummary to_dict conversion."""
    runs = query_client.query_runs(limit=1)
    run = runs[0]

    run_dict = run.to_dict()

    assert "run_id" in run_dict
    assert "dataset_name" in run_dict
    assert "profiled_at" in run_dict
    assert isinstance(run_dict["profiled_at"], str)  # ISO format


def test_drift_event_to_dict(query_client, sample_drift):
    """Test DriftEvent to_dict conversion."""
    events = query_client.query_drift_events(limit=1)
    event = events[0]

    event_dict = event.to_dict()

    assert "event_id" in event_dict
    assert "table_name" in event_dict
    assert "baseline_value" in event_dict
    assert "current_value" in event_dict
    assert "drift_severity" in event_dict


def test_query_empty_results(query_client):
    """Test queries on empty database."""
    runs = query_client.query_runs()
    assert len(runs) == 0

    events = query_client.query_drift_events()
    assert len(events) == 0

    history = query_client.query_table_history("nonexistent")
    assert history["run_count"] == 0
    assert len(history["runs"]) == 0
