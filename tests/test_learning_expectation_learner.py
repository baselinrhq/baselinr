"""Tests for expectation learner."""

import statistics
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy import create_engine, text

from baselinr.config.schema import ConnectionConfig, DatabaseType, StorageConfig
from baselinr.learning.expectation_learner import (
    ExpectationLearner,
    LearnedExpectation,
)


@pytest.fixture
def test_db_engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    return engine


@pytest.fixture
def test_storage_config():
    """Create a test storage configuration."""
    return StorageConfig(
        connection=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
        results_table="baselinr_results",
        runs_table="baselinr_runs",
        create_tables=False,
    )


@pytest.fixture
def setup_test_tables(test_db_engine):
    """Create test tables in the database."""
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
        conn.commit()


@pytest.fixture
def populate_historical_data(test_db_engine, setup_test_tables):
    """Populate database with historical profiling data."""
    with test_db_engine.begin() as conn:
        base_time = datetime.utcnow() - timedelta(days=10)

        # Create runs and results for testing
        for i in range(10):
            run_id = f"run-{i}"
            profiled_at = base_time + timedelta(days=i)

            # Insert run
            conn.execute(
                text(
                    """
                    INSERT INTO baselinr_runs
                    (run_id, dataset_name, schema_name, profiled_at, status)
                    VALUES (:run_id, :dataset_name, :schema_name, :profiled_at, 'completed')
                """
                ),
                {
                    "run_id": run_id,
                    "dataset_name": "users",
                    "schema_name": None,
                    "profiled_at": profiled_at,
                },
            )

            # Insert metric results - simulate normal distribution
            # Mean around 30, stddev around 5
            mean_value = 30 + (i * 0.1)  # Slight trend
            stddev_value = 5.0

            conn.execute(
                text(
                    """
                    INSERT INTO baselinr_results
                    (run_id, dataset_name, column_name, column_type, metric_name,
                     metric_value, profiled_at)
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
                    "metric_value": str(mean_value),
                    "profiled_at": profiled_at,
                },
            )

            conn.execute(
                text(
                    """
                    INSERT INTO baselinr_results
                    (run_id, dataset_name, column_name, column_type, metric_name,
                     metric_value, profiled_at)
                    VALUES (:run_id, :dataset_name, :column_name, :column_type,
                            :metric_name, :metric_value, :profiled_at)
                """
                ),
                {
                    "run_id": run_id,
                    "dataset_name": "users",
                    "column_name": "age",
                    "column_type": "INTEGER",
                    "metric_name": "stddev",
                    "metric_value": str(stddev_value),
                    "profiled_at": profiled_at,
                },
            )

            conn.execute(
                text(
                    """
                    INSERT INTO baselinr_results
                    (run_id, dataset_name, column_name, column_type, metric_name,
                     metric_value, profiled_at)
                    VALUES (:run_id, :dataset_name, :column_name, :column_type,
                            :metric_name, :metric_value, :profiled_at)
                """
                ),
                {
                    "run_id": run_id,
                    "dataset_name": "users",
                    "column_name": "age",
                    "column_type": "INTEGER",
                    "metric_name": "count",
                    "metric_value": str(1000 + (i * 10)),
                    "profiled_at": profiled_at,
                },
            )

        conn.commit()


def test_learn_expectations_sufficient_samples(
    test_storage_config, test_db_engine, setup_test_tables, populate_historical_data
):
    """Test learning expectations with sufficient historical data."""
    learner = ExpectationLearner(
        storage_config=test_storage_config,
        engine=test_db_engine,
        default_window_days=30,
        min_samples=5,
    )

    expectation = learner.learn_expectations(
        table_name="users",
        column_name="age",
        metric_name="mean",
        window_days=30,
    )

    assert expectation is not None
    assert expectation.table_name == "users"
    assert expectation.column_name == "age"
    assert expectation.metric_name == "mean"
    assert expectation.expected_mean is not None
    assert expectation.expected_mean > 0
    assert expectation.expected_stddev is not None
    assert expectation.lower_control_limit is not None
    assert expectation.upper_control_limit is not None
    assert expectation.lower_control_limit < expectation.upper_control_limit
    assert expectation.sample_size == 10


def test_learn_expectations_insufficient_samples(
    test_storage_config, test_db_engine, setup_test_tables
):
    """Test learning expectations with insufficient historical data."""
    learner = ExpectationLearner(
        storage_config=test_storage_config,
        engine=test_db_engine,
        default_window_days=30,
        min_samples=5,
    )

    # Add only 2 runs (less than min_samples=5)
    with test_db_engine.begin() as conn:
        base_time = datetime.utcnow() - timedelta(days=1)

        for i in range(2):
            run_id = f"run-{i}"
            profiled_at = base_time + timedelta(hours=i)

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

            conn.execute(
                text(
                    """
                    INSERT INTO baselinr_results
                    (run_id, dataset_name, column_name, metric_name, metric_value,
                     profiled_at)
                    VALUES (:run_id, :dataset_name, :column_name, :metric_name,
                            :metric_value, :profiled_at)
                """
                ),
                {
                    "run_id": run_id,
                    "dataset_name": "users",
                    "column_name": "age",
                    "metric_name": "mean",
                    "metric_value": str(30.0 + i),
                    "profiled_at": profiled_at,
                },
            )

        conn.commit()

    expectation = learner.learn_expectations(
        table_name="users",
        column_name="age",
        metric_name="mean",
        window_days=30,
    )

    assert expectation is None


def test_compute_expected_statistics(test_storage_config, test_db_engine):
    """Test computation of expected statistics."""
    learner = ExpectationLearner(
        storage_config=test_storage_config,
        engine=test_db_engine,
    )

    values = [25.0, 30.0, 35.0, 40.0, 45.0, 30.0, 32.0, 28.0, 35.0, 38.0]
    expectation = LearnedExpectation(
        table_name="users",
        schema_name=None,
        column_name="age",
        metric_name="mean",
    )

    learner._compute_expected_statistics(expectation, values)

    assert expectation.expected_mean == statistics.mean(values)
    assert expectation.expected_stddev == statistics.stdev(values)
    assert expectation.expected_variance == statistics.variance(values)
    assert expectation.expected_min == min(values)
    assert expectation.expected_max == max(values)


def test_compute_control_limits(test_storage_config, test_db_engine):
    """Test computation of Shewhart control limits."""
    learner = ExpectationLearner(
        storage_config=test_storage_config,
        engine=test_db_engine,
    )

    values = [25.0, 30.0, 35.0, 40.0, 45.0, 30.0, 32.0, 28.0, 35.0, 38.0]
    expectation = LearnedExpectation(
        table_name="users",
        schema_name=None,
        column_name="age",
        metric_name="mean",
    )

    learner._compute_expected_statistics(expectation, values)
    learner._compute_control_limits(expectation, values)

    assert expectation.lower_control_limit is not None
    assert expectation.upper_control_limit is not None
    assert expectation.lcl_method == "shewhart"
    assert expectation.ucl_method == "shewhart"

    # Control limits should be mean ± 3*stddev
    expected_lcl = expectation.expected_mean - (3 * expectation.expected_stddev)
    expected_ucl = expectation.expected_mean + (3 * expectation.expected_stddev)

    assert abs(expectation.lower_control_limit - expected_lcl) < 0.001
    assert abs(expectation.upper_control_limit - expected_ucl) < 0.001


def test_compute_control_limits_no_variance(test_storage_config, test_db_engine):
    """Test control limits when variance is zero."""
    learner = ExpectationLearner(
        storage_config=test_storage_config,
        engine=test_db_engine,
    )

    # All values are the same
    values = [30.0, 30.0, 30.0, 30.0, 30.0]
    expectation = LearnedExpectation(
        table_name="users",
        schema_name=None,
        column_name="age",
        metric_name="mean",
    )

    learner._compute_expected_statistics(expectation, values)
    learner._compute_control_limits(expectation, values)

    # When no variance, should use min/max
    assert expectation.lower_control_limit == expectation.expected_min
    assert expectation.upper_control_limit == expectation.expected_max


def test_compute_ewma(test_storage_config, test_db_engine):
    """Test EWMA computation."""
    learner = ExpectationLearner(
        storage_config=test_storage_config,
        engine=test_db_engine,
        ewma_lambda=0.2,
    )

    values = [25.0, 30.0, 35.0, 40.0, 45.0]
    expectation = LearnedExpectation(
        table_name="users",
        schema_name=None,
        column_name="age",
        metric_name="mean",
        ewma_lambda=0.2,
    )

    learner._compute_ewma(expectation, values)

    assert expectation.ewma_value is not None
    # EWMA should be between min and max values
    assert min(values) <= expectation.ewma_value <= max(values)


def test_learn_distribution_normal(test_storage_config, test_db_engine):
    """Test distribution learning for normal distribution."""
    learner = ExpectationLearner(
        storage_config=test_storage_config,
        engine=test_db_engine,
    )

    # Values that approximate normal distribution
    values = [28.0, 29.0, 30.0, 30.0, 30.0, 31.0, 32.0, 30.0, 31.0, 29.0]
    expectation = LearnedExpectation(
        table_name="users",
        schema_name=None,
        column_name="age",
        metric_name="mean",
    )

    learner._compute_expected_statistics(expectation, values)
    learner._learn_distribution(expectation, values)

    # Should detect as normal (mean ≈ median, low skewness)
    assert expectation.distribution_type in ["normal", "empirical"]
    assert expectation.distribution_params is not None


def test_learn_distribution_empirical(test_storage_config, test_db_engine):
    """Test distribution learning for skewed distribution."""
    learner = ExpectationLearner(
        storage_config=test_storage_config,
        engine=test_db_engine,
    )

    # Highly skewed values
    values = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 50.0]
    expectation = LearnedExpectation(
        table_name="users",
        schema_name=None,
        column_name="age",
        metric_name="mean",
    )

    learner._compute_expected_statistics(expectation, values)
    learner._learn_distribution(expectation, values)

    # Should detect as empirical due to high skewness
    assert expectation.distribution_type in ["normal", "empirical"]
    assert expectation.distribution_params is not None
    if expectation.distribution_type == "empirical":
        assert "skewness" in expectation.distribution_params


def test_calculate_skewness(test_storage_config, test_db_engine):
    """Test skewness calculation."""
    learner = ExpectationLearner(
        storage_config=test_storage_config,
        engine=test_db_engine,
    )

    # Symmetric values (low skewness)
    values_symmetric = [25.0, 30.0, 35.0, 40.0, 45.0, 30.0, 35.0]
    mean_symmetric = statistics.mean(values_symmetric)
    skewness_symmetric = learner._calculate_skewness(values_symmetric, mean_symmetric)

    assert abs(skewness_symmetric) < 1.0  # Should be close to 0 for symmetric

    # Skewed values (high skewness)
    values_skewed = [10.0, 10.0, 10.0, 10.0, 50.0]
    mean_skewed = statistics.mean(values_skewed)
    skewness_skewed = learner._calculate_skewness(values_skewed, mean_skewed)

    assert abs(skewness_skewed) > abs(skewness_symmetric)


def test_is_numeric_metric(test_storage_config, test_db_engine):
    """Test numeric metric detection."""
    learner = ExpectationLearner(
        storage_config=test_storage_config,
        engine=test_db_engine,
    )

    assert learner._is_numeric_metric("mean")
    assert learner._is_numeric_metric("stddev")
    assert learner._is_numeric_metric("count")
    assert learner._is_numeric_metric("null_ratio")
    assert not learner._is_numeric_metric("histogram")
    assert not learner._is_numeric_metric("top_values")


def test_is_categorical_column(test_storage_config, test_db_engine):
    """Test categorical column detection."""
    learner = ExpectationLearner(
        storage_config=test_storage_config,
        engine=test_db_engine,
    )

    assert learner._is_categorical_column("VARCHAR(100)", "mean")
    assert learner._is_categorical_column("TEXT", "mean")
    assert learner._is_categorical_column("STRING", "mean")
    assert not learner._is_categorical_column("INTEGER", "mean")
    assert not learner._is_categorical_column("FLOAT", "mean")
    assert not learner._is_categorical_column(None, "mean")


def test_learn_expectations_no_values(
    test_storage_config, test_db_engine, setup_test_tables
):
    """Test learning with empty historical data."""
    learner = ExpectationLearner(
        storage_config=test_storage_config,
        engine=test_db_engine,
        min_samples=1,  # Lower threshold for this test
    )

    expectation = learner.learn_expectations(
        table_name="nonexistent",
        column_name="age",
        metric_name="mean",
    )

    assert expectation is None


def test_learn_expectations_with_schema(
    test_storage_config, test_db_engine, setup_test_tables
):
    """Test learning expectations with schema name."""
    learner = ExpectationLearner(
        storage_config=test_storage_config,
        engine=test_db_engine,
        min_samples=3,
    )

    # Populate data with schema
    with test_db_engine.begin() as conn:
        base_time = datetime.utcnow() - timedelta(days=1)

        for i in range(5):
            run_id = f"run-{i}"
            profiled_at = base_time + timedelta(hours=i)

            conn.execute(
                text(
                    """
                    INSERT INTO baselinr_runs
                    (run_id, dataset_name, schema_name, profiled_at, status)
                    VALUES (:run_id, :dataset_name, :schema_name, :profiled_at,
                            'completed')
                """
                ),
                {
                    "run_id": run_id,
                    "dataset_name": "users",
                    "schema_name": "public",
                    "profiled_at": profiled_at,
                },
            )

            conn.execute(
                text(
                    """
                    INSERT INTO baselinr_results
                    (run_id, dataset_name, schema_name, column_name, column_type,
                     metric_name, metric_value, profiled_at)
                    VALUES (:run_id, :dataset_name, :schema_name, :column_name,
                            :column_type, :metric_name, :metric_value, :profiled_at)
                """
                ),
                {
                    "run_id": run_id,
                    "dataset_name": "users",
                    "schema_name": "public",
                    "column_name": "age",
                    "column_type": "INTEGER",
                    "metric_name": "mean",
                    "metric_value": str(30.0 + i),
                    "profiled_at": profiled_at,
                },
            )

        conn.commit()

    expectation = learner.learn_expectations(
        table_name="users",
        column_name="age",
        metric_name="mean",
        schema_name="public",
    )

    assert expectation is not None
    assert expectation.schema_name == "public"

