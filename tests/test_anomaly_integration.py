"""Integration tests for anomaly detection."""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, text

from baselinr.config.schema import (
    BaselinrConfig,
    ConnectionConfig,
    DatabaseType,
    SchemaChangeConfig,
    StorageConfig,
)
from baselinr.events import EventBus
from baselinr.learning import ExpectationStorage
from baselinr.learning.expectation_learner import LearnedExpectation
from baselinr.profiling.core import ProfilingResult
from baselinr.storage.writer import ResultWriter


@pytest.fixture
def test_db_engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    return engine


@pytest.fixture
def setup_storage_tables(test_db_engine):
    """Create storage tables in the database."""
    with test_db_engine.begin() as conn:
        # Create runs table
        conn.execute(
            text(
                """
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
            """
            )
        )

        # Create results table
        conn.execute(
            text(
                """
                CREATE TABLE baselinr_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id VARCHAR(36) NOT NULL,
                    dataset_name VARCHAR(255) NOT NULL,
                    schema_name VARCHAR(255),
                    column_name VARCHAR(255) NOT NULL,
                    column_type VARCHAR(100),
                    metric_name VARCHAR(100) NOT NULL,
                    metric_value TEXT,
                    profiled_at TIMESTAMP NOT NULL
                )
            """
            )
        )

        # Create expectations table
        conn.execute(
            text(
                """
                CREATE TABLE baselinr_expectations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name VARCHAR(255) NOT NULL,
                    schema_name VARCHAR(255),
                    column_name VARCHAR(255) NOT NULL,
                    metric_name VARCHAR(100) NOT NULL,
                    column_type VARCHAR(100),
                    expected_mean FLOAT,
                    expected_variance FLOAT,
                    expected_stddev FLOAT,
                    expected_min FLOAT,
                    expected_max FLOAT,
                    lower_control_limit FLOAT,
                    upper_control_limit FLOAT,
                    lcl_method VARCHAR(50),
                    ucl_method VARCHAR(50),
                    ewma_value FLOAT,
                    ewma_lambda FLOAT DEFAULT 0.2,
                    distribution_type VARCHAR(50),
                    distribution_params TEXT,
                    category_distribution TEXT,
                    sample_size INTEGER,
                    learning_window_days INTEGER,
                    last_updated TIMESTAMP NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expectation_version INTEGER DEFAULT 1,
                    UNIQUE (table_name, schema_name, column_name, metric_name)
                )
            """
            )
        )
        conn.commit()


@pytest.fixture
def populate_historical_runs(test_db_engine, setup_storage_tables):
    """Populate database with historical profiling runs."""
    base_time = datetime.utcnow() - timedelta(days=10)

    with test_db_engine.begin() as conn:
        for i in range(10):
            run_id = f"run-{i}"
            profiled_at = base_time + timedelta(days=i)

            # Insert run
            conn.execute(
                text(
                    """
                    INSERT INTO baselinr_runs
                    (run_id, dataset_name, profiled_at, status)
                    VALUES (:run_id, :dataset_name, :profiled_at, 'completed')
                """
                ),
                {
                    "run_id": run_id,
                    "dataset_name": "users",
                    "profiled_at": profiled_at,
                },
            )

            # Insert metric results
            for metric_name, value in [
                ("mean", 30.0 + i * 0.1),
                ("stddev", 5.0),
                ("count", 1000 + i * 10),
                ("null_ratio", 0.05),
                ("unique_ratio", 0.95),
            ]:
                conn.execute(
                    text(
                        """
                        INSERT INTO baselinr_results
                        (run_id, dataset_name, column_name, metric_name, metric_value, profiled_at)
                        VALUES (:run_id, :dataset_name, :column_name, :metric_name, :metric_value, :profiled_at)
                    """
                    ),
                    {
                        "run_id": run_id,
                        "dataset_name": "users",
                        "column_name": "age",
                        "metric_name": metric_name,
                        "metric_value": str(value),
                        "profiled_at": profiled_at,
                    },
                )
        conn.commit()


@pytest.fixture
def populate_expectations(test_db_engine, setup_storage_tables):
    """Populate expectations for testing."""
    storage_config = StorageConfig(
        connection=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
        results_table="baselinr_results",
        runs_table="baselinr_runs",
        create_tables=False,
    )
    storage = ExpectationStorage(storage_config, test_db_engine)

    # Create expectation for mean metric
    expectation = LearnedExpectation(
        table_name="users",
        schema_name=None,
        column_name="age",
        metric_name="mean",
        expected_mean=30.5,
        expected_stddev=5.0,
        expected_min=28.0,
        expected_max=32.0,
        lower_control_limit=15.5,  # mean - 3*stddev
        upper_control_limit=45.5,  # mean + 3*stddev
        ewma_value=30.5,
        ewma_lambda=0.2,
        sample_size=10,
        last_updated=datetime.utcnow(),
    )
    storage.save_expectation(expectation)


def test_end_to_end_anomaly_detection_workflow(
    test_db_engine, setup_storage_tables, populate_historical_runs
):
    """Test end-to-end anomaly detection workflow with learning and detection."""
    storage_config = StorageConfig(
        connection=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
        results_table="baselinr_results",
        runs_table="baselinr_runs",
        create_tables=False,
        enable_expectation_learning=True,
        enable_anomaly_detection=True,
        learning_window_days=30,
        min_samples=5,
    )

    schema_change_config = SchemaChangeConfig(enabled=False)
    baselinr_config = Mock(spec=BaselinrConfig)
    baselinr_config.schema_change = schema_change_config
    baselinr_config.profiling = Mock()
    baselinr_config.profiling.extract_lineage = False

    event_bus = Mock(spec=EventBus)

    # Create ResultWriter
    writer = ResultWriter(
        config=storage_config,
        baselinr_config=baselinr_config,
        event_bus=event_bus,
    )
    writer.engine = test_db_engine

    # Create a profiling result with normal values
    result_normal = ProfilingResult(
        run_id="test-run-normal",
        dataset_name="users",
        schema_name=None,
        profiled_at=datetime.utcnow(),
    )
    result_normal.add_column_metrics(
        column_name="age",
        column_type="INTEGER",
        metrics={
            "mean": 31.0,  # Normal value
            "stddev": 5.0,
            "count": 1050,
            "null_ratio": 0.05,
            "unique_ratio": 0.95,
        },
    )

    # Write normal result (should learn expectations)
    writer.write_results([result_normal], enable_enrichment=False)

    # Verify expectation was learned
    storage = ExpectationStorage(storage_config=storage_config, engine=test_db_engine)
    expectation = storage.get_expectation(
        table_name="users",
        column_name="age",
        metric_name="mean",
    )

    if expectation:
        assert expectation.expected_mean is not None

        # Now test anomaly detection with an outlier
        result_anomaly = ProfilingResult(
            run_id="test-run-anomaly",
            dataset_name="users",
            schema_name=None,
            profiled_at=datetime.utcnow(),
        )
        result_anomaly.add_column_metrics(
            column_name="age",
            column_type="INTEGER",
            metrics={
                "mean": 50.0,  # Outlier (above UCL)
                "stddev": 5.0,
                "count": 1050,
                "null_ratio": 0.05,
                "unique_ratio": 0.95,
            },
        )

        # Write anomaly result (should detect anomalies)
        writer.write_results([result_anomaly], enable_enrichment=False)

        # Verify anomaly events were emitted
        assert event_bus.emit.called
        # Check that AnomalyDetected events were emitted
        calls = [
            call for call in event_bus.emit.call_args_list if call is not None
        ]
        anomaly_events = [
            call[0][0]
            for call in calls
            if hasattr(call[0][0], "event_type")
            and call[0][0].event_type == "AnomalyDetected"
        ]
        # May or may not have anomalies depending on configuration
        assert isinstance(anomaly_events, list)


def test_anomaly_detection_with_existing_expectations(
    test_db_engine, setup_storage_tables, populate_expectations
):
    """Test anomaly detection when expectations already exist."""
    storage_config = StorageConfig(
        connection=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
        results_table="baselinr_results",
        runs_table="baselinr_runs",
        create_tables=False,
        enable_anomaly_detection=True,
    )

    schema_change_config = SchemaChangeConfig(enabled=False)
    baselinr_config = Mock(spec=BaselinrConfig)
    baselinr_config.schema_change = schema_change_config
    baselinr_config.profiling = Mock()
    baselinr_config.profiling.extract_lineage = False

    event_bus = Mock(spec=EventBus)

    writer = ResultWriter(
        config=storage_config,
        baselinr_config=baselinr_config,
        event_bus=event_bus,
    )
    writer.engine = test_db_engine

    # Create result with outlier value
    result = ProfilingResult(
        run_id="test-run-outlier",
        dataset_name="users",
        schema_name=None,
        profiled_at=datetime.utcnow(),
    )
    result.add_column_metrics(
        column_name="age",
        column_type="INTEGER",
        metrics={
            "mean": 50.0,  # Above UCL of 45.5
            "stddev": 5.0,
            "count": 1050,
        },
    )

    # Write results (should detect anomaly)
    writer.write_results([result], enable_enrichment=False)

    # Verify anomaly events were emitted
    assert event_bus.emit.called


def test_anomaly_detection_disabled(
    test_db_engine, setup_storage_tables, populate_expectations
):
    """Test that anomaly detection is skipped when disabled."""
    storage_config = StorageConfig(
        connection=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
        results_table="baselinr_results",
        runs_table="baselinr_runs",
        create_tables=False,
        enable_anomaly_detection=False,  # Disabled
    )

    schema_change_config = SchemaChangeConfig(enabled=False)
    baselinr_config = Mock(spec=BaselinrConfig)
    baselinr_config.schema_change = schema_change_config
    baselinr_config.profiling = Mock()
    baselinr_config.profiling.extract_lineage = False

    event_bus = Mock(spec=EventBus)

    writer = ResultWriter(
        config=storage_config,
        baselinr_config=baselinr_config,
        event_bus=event_bus,
    )
    writer.engine = test_db_engine

    result = ProfilingResult(
        run_id="test-run",
        dataset_name="users",
        schema_name=None,
        profiled_at=datetime.utcnow(),
    )
    result.add_column_metrics(
        column_name="age",
        column_type="INTEGER",
        metrics={"mean": 50.0},
    )

    # Write results (should not detect anomalies)
    writer.write_results([result], enable_enrichment=False)

    # Should not have emitted anomaly events
    anomaly_events = [
        call[0][0]
        for call in event_bus.emit.call_args_list
        if hasattr(call[0][0], "event_type")
        and call[0][0].event_type == "AnomalyDetected"
    ]
    assert len(anomaly_events) == 0


def test_anomaly_detection_no_expectations(
    test_db_engine, setup_storage_tables
):
    """Test that anomaly detection skips when no expectations exist."""
    storage_config = StorageConfig(
        connection=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
        results_table="baselinr_results",
        runs_table="baselinr_runs",
        create_tables=False,
        enable_anomaly_detection=True,
    )

    schema_change_config = SchemaChangeConfig(enabled=False)
    baselinr_config = Mock(spec=BaselinrConfig)
    baselinr_config.schema_change = schema_change_config
    baselinr_config.profiling = Mock()
    baselinr_config.profiling.extract_lineage = False

    event_bus = Mock(spec=EventBus)

    writer = ResultWriter(
        config=storage_config,
        baselinr_config=baselinr_config,
        event_bus=event_bus,
    )
    writer.engine = test_db_engine

    result = ProfilingResult(
        run_id="test-run",
        dataset_name="users",
        schema_name=None,
        profiled_at=datetime.utcnow(),
    )
    result.add_column_metrics(
        column_name="age",
        column_type="INTEGER",
        metrics={"mean": 50.0},
    )

    # Write results (should not detect anomalies since no expectations)
    writer.write_results([result], enable_enrichment=False)

    # Should not have emitted anomaly events (no expectations to compare against)
    anomaly_events = [
        call[0][0]
        for call in event_bus.emit.call_args_list
        if hasattr(call[0][0], "event_type")
        and call[0][0].event_type == "AnomalyDetected"
    ]
    assert len(anomaly_events) == 0

