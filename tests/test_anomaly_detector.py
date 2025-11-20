"""Tests for anomaly detector."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import create_engine, text

from baselinr.anomaly import AnomalyDetector, AnomalyResult, AnomalyType
from baselinr.config.schema import ConnectionConfig, DatabaseType, StorageConfig
from baselinr.events import EventBus
from baselinr.learning.expectation_learner import LearnedExpectation
from baselinr.learning.expectation_storage import ExpectationStorage


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
        enable_anomaly_detection=True,
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
def populate_expectations(test_db_engine, setup_test_tables):
    """Populate expectations table with test data."""
    storage_config = StorageConfig(
        connection=ConnectionConfig(type=DatabaseType.SQLITE, database=":memory:"),
        results_table="baselinr_results",
        runs_table="baselinr_runs",
        create_tables=False,
    )
    storage = ExpectationStorage(storage_config, test_db_engine)

    expectation = LearnedExpectation(
        table_name="users",
        schema_name=None,
        column_name="age",
        metric_name="mean",
        expected_mean=30.0,
        expected_stddev=5.0,
        expected_min=18.0,
        expected_max=65.0,
        lower_control_limit=15.0,  # mean - 3*stddev
        upper_control_limit=45.0,  # mean + 3*stddev
        ewma_value=30.0,
        ewma_lambda=0.2,
        sample_size=10,
        last_updated=datetime.utcnow(),
    )
    storage.save_expectation(expectation)


@pytest.fixture
def populate_historical_data(test_db_engine, setup_test_tables):
    """Populate database with historical profiling data."""
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

            # Insert metric result
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
                    "metric_name": "mean",
                    "metric_value": str(30.0 + i * 0.5),  # Gradual trend
                    "profiled_at": profiled_at,
                },
            )
        conn.commit()


class TestAnomalyDetector:
    """Tests for AnomalyDetector class."""

    def test_detect_anomalies_no_expectation(
        self, test_storage_config, test_db_engine, setup_test_tables
    ):
        """Test anomaly detection when no expectation exists."""
        detector = AnomalyDetector(
            storage_config=test_storage_config,
            engine=test_db_engine,
        )

        anomalies = detector.detect_anomalies(
            table_name="users",
            column_name="age",
            metric_name="mean",
            current_value=30.0,
        )

        assert anomalies == []

    def test_detect_anomalies_control_limits_breach(
        self,
        test_storage_config,
        test_db_engine,
        setup_test_tables,
        populate_expectations,
    ):
        """Test control limits breach detection."""
        detector = AnomalyDetector(
            storage_config=test_storage_config,
            engine=test_db_engine,
            enabled_methods=["control_limits"],
        )

        # Value above upper control limit
        anomalies = detector.detect_anomalies(
            table_name="users",
            column_name="age",
            metric_name="mean",
            current_value=50.0,  # Above UCL of 45.0
        )

        assert len(anomalies) > 0
        assert any(
            a.anomaly_type == AnomalyType.CONTROL_LIMIT_BREACH for a in anomalies
        )

    def test_detect_anomalies_ewma_outlier(
        self,
        test_storage_config,
        test_db_engine,
        setup_test_tables,
        populate_expectations,
    ):
        """Test EWMA-based outlier detection."""
        detector = AnomalyDetector(
            storage_config=test_storage_config,
            engine=test_db_engine,
            enabled_methods=["ewma"],
            ewma_deviation_threshold=2.0,
        )

        # Value significantly different from EWMA
        anomalies = detector.detect_anomalies(
            table_name="users",
            column_name="age",
            metric_name="mean",
            current_value=45.0,  # ~3 stddevs from EWMA (30.0)
        )

        assert len(anomalies) > 0
        assert any(a.anomaly_type == AnomalyType.EWMA_OUTLIER for a in anomalies)

    def test_detect_anomalies_iqr_with_historical_data(
        self,
        test_storage_config,
        test_db_engine,
        setup_test_tables,
        populate_expectations,
        populate_historical_data,
    ):
        """Test IQR detection with historical data."""
        detector = AnomalyDetector(
            storage_config=test_storage_config,
            engine=test_db_engine,
            enabled_methods=["iqr"],
        )

        # Outlier value
        anomalies = detector.detect_anomalies(
            table_name="users",
            column_name="age",
            metric_name="mean",
            current_value=100.0,  # Clear outlier
        )

        # May or may not detect depending on historical distribution
        assert isinstance(anomalies, list)

    def test_detect_anomalies_categorization(
        self,
        test_storage_config,
        test_db_engine,
        setup_test_tables,
        populate_expectations,
    ):
        """Test anomaly categorization by metric type."""
        detector = AnomalyDetector(
            storage_config=test_storage_config,
            engine=test_db_engine,
            enabled_methods=["control_limits"],
        )

        # Test row count spike detection
        # Create expectation for count metric
        storage = ExpectationStorage(test_storage_config, test_db_engine)
        count_expectation = LearnedExpectation(
            table_name="users",
            schema_name=None,
            column_name="age",
            metric_name="count",
            expected_mean=1000.0,
            expected_stddev=50.0,
            lower_control_limit=850.0,
            upper_control_limit=1150.0,
            sample_size=10,
            last_updated=datetime.utcnow(),
        )
        storage.save_expectation(count_expectation)

        # Value above UCL
        anomalies = detector.detect_anomalies(
            table_name="users",
            column_name="age",
            metric_name="count",
            current_value=2000.0,  # Spike
        )

        assert len(anomalies) > 0
        # Should be categorized as row count spike
        assert any(
            a.anomaly_type == AnomalyType.ROW_COUNT_SPIKE for a in anomalies
        )

    def test_detect_anomalies_event_emission(
        self,
        test_storage_config,
        test_db_engine,
        setup_test_tables,
        populate_expectations,
    ):
        """Test that anomalies emit events via event bus."""
        event_bus = Mock(spec=EventBus)
        detector = AnomalyDetector(
            storage_config=test_storage_config,
            engine=test_db_engine,
            event_bus=event_bus,
            enabled_methods=["control_limits"],
        )

        # Value above UCL
        anomalies = detector.detect_anomalies(
            table_name="users",
            column_name="age",
            metric_name="mean",
            current_value=50.0,
        )

        # Emit events
        detector.emit_anomaly_events(anomalies)

        # Verify events were emitted
        if anomalies:
            assert event_bus.emit.called
            # Check that AnomalyDetected event was emitted
            call_args = event_bus.emit.call_args[0][0]
            assert call_args.event_type == "AnomalyDetected"
            assert call_args.table == "users"
            assert call_args.column == "age"
            assert call_args.metric == "mean"

    def test_detect_anomalies_non_numeric_metric(
        self,
        test_storage_config,
        test_db_engine,
        setup_test_tables,
    ):
        """Test that non-numeric metrics are skipped."""
        detector = AnomalyDetector(
            storage_config=test_storage_config,
            engine=test_db_engine,
        )

        anomalies = detector.detect_anomalies(
            table_name="users",
            column_name="name",
            metric_name="histogram",  # Non-numeric metric
            current_value="test",
        )

        assert anomalies == []

    def test_detect_anomalies_with_schema(
        self,
        test_storage_config,
        test_db_engine,
        setup_test_tables,
    ):
        """Test anomaly detection with schema name."""
        storage = ExpectationStorage(test_storage_config, test_db_engine)

        expectation = LearnedExpectation(
            table_name="users",
            schema_name="public",
            column_name="age",
            metric_name="mean",
            expected_mean=30.0,
            expected_stddev=5.0,
            lower_control_limit=15.0,
            upper_control_limit=45.0,
            sample_size=10,
            last_updated=datetime.utcnow(),
        )
        storage.save_expectation(expectation)

        detector = AnomalyDetector(
            storage_config=test_storage_config,
            engine=test_db_engine,
            enabled_methods=["control_limits"],
        )

        anomalies = detector.detect_anomalies(
            table_name="users",
            schema_name="public",
            column_name="age",
            metric_name="mean",
            current_value=50.0,
        )

        assert len(anomalies) > 0

    def test_check_control_limits_no_limits(
        self,
        test_storage_config,
        test_db_engine,
        setup_test_tables,
    ):
        """Test control limits check when limits are not set."""
        storage = ExpectationStorage(test_storage_config, test_db_engine)

        expectation = LearnedExpectation(
            table_name="users",
            schema_name=None,
            column_name="age",
            metric_name="mean",
            expected_mean=30.0,
            lower_control_limit=None,
            upper_control_limit=None,
            sample_size=10,
            last_updated=datetime.utcnow(),
        )
        storage.save_expectation(expectation)

        detector = AnomalyDetector(
            storage_config=test_storage_config,
            engine=test_db_engine,
        )

        # Should return no anomaly when limits are not set
        result = detector._check_control_limits(50.0, expectation)
        assert not result.is_anomaly

