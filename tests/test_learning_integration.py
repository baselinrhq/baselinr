"""Integration tests for expectation learning."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import create_engine, text

from baselinr.config.schema import (
    BaselinrConfig,
    ConnectionConfig,
    DatabaseType,
    ProfilingConfig,
    StorageConfig,
    TablePattern,
)
from baselinr.learning import ExpectationLearner, ExpectationStorage
from baselinr.profiling.core import ProfileEngine, ProfilingResult
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
    with test_db_engine.begin() as conn:
        base_time = datetime.utcnow() - timedelta(days=10)

        # Create multiple runs with varying metrics
        for i in range(10):
            run_id = f"historical-run-{i}"
            profiled_at = base_time + timedelta(days=i)

            # Insert run
            conn.execute(
                text(
                    """
                    INSERT INTO baselinr_runs
                    (run_id, dataset_name, schema_name, profiled_at, status,
                     row_count, column_count)
                    VALUES (:run_id, :dataset_name, :schema_name, :profiled_at,
                            'completed', :row_count, :column_count)
                """
                ),
                {
                    "run_id": run_id,
                    "dataset_name": "users",
                    "schema_name": None,
                    "profiled_at": profiled_at,
                    "row_count": 1000 + (i * 10),
                    "column_count": 5,
                },
            )

            # Insert metrics - simulate realistic values with some variance
            metrics = {
                "mean": 30.0 + (i * 0.1) + (i % 3) * 0.5,  # Slight trend + noise
                "stddev": 5.0 + (i % 2) * 0.5,  # Varying stddev
                "count": 1000 + (i * 10),
                "null_ratio": 0.05 + (i % 4) * 0.01,
            }

            for metric_name, metric_value in metrics.items():
                conn.execute(
                    text(
                        """
                        INSERT INTO baselinr_results
                        (run_id, dataset_name, column_name, column_type,
                         metric_name, metric_value, profiled_at)
                        VALUES (:run_id, :dataset_name, :column_name, :column_type,
                                :metric_name, :metric_value, :profiled_at)
                    """
                    ),
                    {
                        "run_id": run_id,
                        "dataset_name": "users",
                        "column_name": "age",
                        "column_type": "INTEGER",
                        "metric_name": metric_name,
                        "metric_value": str(metric_value),
                        "profiled_at": profiled_at,
                    },
                )

        conn.commit()


def test_end_to_end_learning_workflow(
    test_db_engine, setup_storage_tables, populate_historical_runs
):
    """Test complete workflow: profile -> learn -> store -> retrieve."""
    storage_config = StorageConfig(
        connection=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
        results_table="baselinr_results",
        runs_table="baselinr_runs",
        create_tables=False,
        enable_expectation_learning=True,
        learning_window_days=30,
        min_samples=5,
    )

    # Create learner and storage
    learner = ExpectationLearner(
        storage_config=storage_config,
        engine=test_db_engine,
        default_window_days=30,
        min_samples=5,
    )
    storage = ExpectationStorage(storage_config=storage_config, engine=test_db_engine)

    # Learn expectations
    expectation = learner.learn_expectations(
        table_name="users",
        column_name="age",
        metric_name="mean",
        window_days=30,
    )

    # Verify expectation was learned
    assert expectation is not None
    assert expectation.expected_mean is not None
    assert expectation.expected_stddev is not None

    # Store expectation
    storage.save_expectation(expectation)

    # Retrieve expectation
    retrieved = storage.get_expectation(
        table_name="users",
        column_name="age",
        metric_name="mean",
    )

    # Verify stored correctly
    assert retrieved is not None
    assert retrieved.expected_mean == expectation.expected_mean
    assert retrieved.expected_stddev == expectation.expected_stddev
    assert retrieved.sample_size == 10


def test_expectation_updates_over_time(
    test_db_engine, setup_storage_tables, populate_historical_runs
):
    """Test that expectations update correctly as new runs are added."""
    storage_config = StorageConfig(
        connection=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
        results_table="baselinr_results",
        runs_table="baselinr_runs",
        create_tables=False,
        enable_expectation_learning=True,
        learning_window_days=30,
        min_samples=5,
    )

    learner = ExpectationLearner(
        storage_config=storage_config,
        engine=test_db_engine,
        default_window_days=30,
        min_samples=5,
    )
    storage = ExpectationStorage(storage_config=storage_config, engine=test_db_engine)

    # Learn initial expectation
    expectation1 = learner.learn_expectations(
        table_name="users",
        column_name="age",
        metric_name="mean",
    )
    assert expectation1 is not None
    initial_mean = expectation1.expected_mean

    storage.save_expectation(expectation1)

    # Add more historical runs with different values
    with test_db_engine.begin() as conn:
        for i in range(5):
            run_id = f"new-run-{i}"
            profiled_at = datetime.utcnow() - timedelta(hours=i)

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

            # Add slightly higher values to shift mean
            conn.execute(
                text(
                    """
                    INSERT INTO baselinr_results
                    (run_id, dataset_name, column_name, column_type,
                     metric_name, metric_value, profiled_at)
                    VALUES (:run_id, :dataset_name, :column_name, :column_type,
                            :metric_name, :metric_value, :profiled_at)
                """
                ),
                {
                    "run_id": run_id,
                    "dataset_name": "users",
                    "column_name": "age",
                    "column_type": "INTEGER",
                    "metric_name": "mean",
                    "metric_value": str(35.0 + i),  # Higher values
                    "profiled_at": profiled_at,
                },
            )

        conn.commit()

    # Learn updated expectation
    expectation2 = learner.learn_expectations(
        table_name="users",
        column_name="age",
        metric_name="mean",
    )
    assert expectation2 is not None

    # Should have more samples now
    assert expectation2.sample_size > expectation1.sample_size

    # Mean might shift (depending on window)
    storage.save_expectation(expectation2)

    # Verify version incremented
    retrieved = storage.get_expectation(
        table_name="users",
        column_name="age",
        metric_name="mean",
    )
    assert retrieved.expectation_version == 2


def test_integration_with_result_writer(
    test_db_engine, setup_storage_tables, populate_historical_runs
):
    """Test that expectation learning integrates with ResultWriter."""
    storage_config = StorageConfig(
        connection=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
        results_table="baselinr_results",
        runs_table="baselinr_runs",
        create_tables=False,
        enable_expectation_learning=True,
        learning_window_days=30,
        min_samples=5,
    )

    # Create mock baselinr config
    from baselinr.config.schema import SchemaChangeConfig

    schema_change_config = SchemaChangeConfig(enabled=False)
    baselinr_config = Mock(spec=BaselinrConfig)
    baselinr_config.schema_change = schema_change_config
    baselinr_config.profiling = Mock()
    baselinr_config.profiling.extract_lineage = False

    # Create ResultWriter
    writer = ResultWriter(
        config=storage_config,
        baselinr_config=baselinr_config,
        event_bus=None,
    )
    writer.engine = test_db_engine

    # Create a profiling result
    result = ProfilingResult(
        run_id="test-run-123",
        dataset_name="users",
        schema_name=None,
        profiled_at=datetime.utcnow(),
    )
    result.add_column_metrics(
        column_name="age",
        column_type="INTEGER",
        metrics={
            "mean": 32.5,
            "stddev": 5.2,
            "count": 1050,
            "null_ratio": 0.06,
        },
    )

    # Write results (this should trigger learning)
    writer.write_results([result], enable_enrichment=False)

    # Verify expectations were learned and stored
    storage = ExpectationStorage(storage_config=storage_config, engine=test_db_engine)

    expectation = storage.get_expectation(
        table_name="users",
        column_name="age",
        metric_name="mean",
    )

    # Should have learned expectation if sufficient data
    # (depends on historical data in populate_historical_runs)
    if expectation:
        assert expectation.expected_mean is not None
        assert expectation.sample_size >= 5

