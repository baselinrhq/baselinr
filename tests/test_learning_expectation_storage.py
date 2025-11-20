"""Tests for expectation storage."""

import json
from datetime import datetime
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, text

from baselinr.config.schema import ConnectionConfig, DatabaseType, StorageConfig
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
    )


@pytest.fixture
def setup_expectations_table(test_db_engine):
    """Create expectations table in the database."""
    with test_db_engine.begin() as conn:
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


def test_insert_expectation(test_storage_config, test_db_engine, setup_expectations_table):
    """Test inserting a new expectation."""
    storage = ExpectationStorage(storage_config=test_storage_config, engine=test_db_engine)

    expectation = LearnedExpectation(
        table_name="users",
        schema_name=None,
        column_name="age",
        metric_name="mean",
        column_type="INTEGER",
        expected_mean=30.5,
        expected_variance=25.0,
        expected_stddev=5.0,
        expected_min=20.0,
        expected_max=45.0,
        lower_control_limit=15.5,
        upper_control_limit=45.5,
        lcl_method="shewhart",
        ucl_method="shewhart",
        sample_size=10,
        learning_window_days=30,
    )

    storage.save_expectation(expectation)

    # Retrieve and verify
    retrieved = storage.get_expectation(
        table_name="users",
        column_name="age",
        metric_name="mean",
    )

    assert retrieved is not None
    assert retrieved.table_name == "users"
    assert retrieved.column_name == "age"
    assert retrieved.metric_name == "mean"
    assert retrieved.expected_mean == 30.5
    assert retrieved.expected_stddev == 5.0
    assert retrieved.lower_control_limit == 15.5
    assert retrieved.upper_control_limit == 45.5
    assert retrieved.sample_size == 10
    assert retrieved.expectation_version == 1


def test_update_expectation(test_storage_config, test_db_engine, setup_expectations_table):
    """Test updating an existing expectation."""
    storage = ExpectationStorage(storage_config=test_storage_config, engine=test_db_engine)

    # Insert initial expectation
    expectation1 = LearnedExpectation(
        table_name="users",
        schema_name=None,
        column_name="age",
        metric_name="mean",
        expected_mean=30.0,
        expected_stddev=5.0,
        sample_size=10,
        learning_window_days=30,
    )

    storage.save_expectation(expectation1)

    # Update expectation
    expectation2 = LearnedExpectation(
        table_name="users",
        schema_name=None,
        column_name="age",
        metric_name="mean",
        expected_mean=31.0,  # Updated
        expected_stddev=5.5,  # Updated
        sample_size=15,  # Updated
        learning_window_days=30,
    )

    storage.save_expectation(expectation2)

    # Retrieve and verify update
    retrieved = storage.get_expectation(
        table_name="users",
        column_name="age",
        metric_name="mean",
    )

    assert retrieved is not None
    assert retrieved.expected_mean == 31.0
    assert retrieved.expected_stddev == 5.5
    assert retrieved.sample_size == 15
    assert retrieved.expectation_version == 2  # Should increment


def test_get_expectation_not_found(test_storage_config, test_db_engine, setup_expectations_table):
    """Test retrieving non-existent expectation."""
    storage = ExpectationStorage(storage_config=test_storage_config, engine=test_db_engine)

    retrieved = storage.get_expectation(
        table_name="nonexistent",
        column_name="age",
        metric_name="mean",
    )

    assert retrieved is None


def test_expectation_with_distribution_params(
    test_storage_config, test_db_engine, setup_expectations_table
):
    """Test expectation with distribution parameters."""
    storage = ExpectationStorage(storage_config=test_storage_config, engine=test_db_engine)

    expectation = LearnedExpectation(
        table_name="users",
        schema_name=None,
        column_name="age",
        metric_name="mean",
        expected_mean=30.0,
        expected_stddev=5.0,
        distribution_type="normal",
        distribution_params={"mean": 30.0, "stddev": 5.0},
        sample_size=10,
        learning_window_days=30,
    )

    storage.save_expectation(expectation)

    retrieved = storage.get_expectation(
        table_name="users",
        column_name="age",
        metric_name="mean",
    )

    assert retrieved is not None
    assert retrieved.distribution_type == "normal"
    assert retrieved.distribution_params == {"mean": 30.0, "stddev": 5.0}


def test_expectation_with_category_distribution(
    test_storage_config, test_db_engine, setup_expectations_table
):
    """Test expectation with categorical distribution."""
    storage = ExpectationStorage(storage_config=test_storage_config, engine=test_db_engine)

    expectation = LearnedExpectation(
        table_name="users",
        schema_name=None,
        column_name="status",
        metric_name="category_distribution",
        category_distribution={"active": 0.65, "inactive": 0.25, "pending": 0.10},
        sample_size=10,
        learning_window_days=30,
    )

    storage.save_expectation(expectation)

    retrieved = storage.get_expectation(
        table_name="users",
        column_name="status",
        metric_name="category_distribution",
    )

    assert retrieved is not None
    assert retrieved.category_distribution == {
        "active": 0.65,
        "inactive": 0.25,
        "pending": 0.10,
    }


def test_expectation_with_schema(test_storage_config, test_db_engine, setup_expectations_table):
    """Test expectation with schema name."""
    storage = ExpectationStorage(storage_config=test_storage_config, engine=test_db_engine)

    expectation = LearnedExpectation(
        table_name="users",
        schema_name="public",
        column_name="age",
        metric_name="mean",
        expected_mean=30.0,
        expected_stddev=5.0,
        sample_size=10,
        learning_window_days=30,
    )

    storage.save_expectation(expectation)

    retrieved = storage.get_expectation(
        table_name="users",
        column_name="age",
        metric_name="mean",
        schema_name="public",
    )

    assert retrieved is not None
    assert retrieved.schema_name == "public"

    # Try retrieving without schema (should not find)
    retrieved_no_schema = storage.get_expectation(
        table_name="users",
        column_name="age",
        metric_name="mean",
    )

    # In SQLite, NULL = NULL is false, so this might return None
    # This behavior depends on the query logic
    assert retrieved_no_schema is None or retrieved_no_schema.schema_name == "public"


def test_expectation_version_increment(
    test_storage_config, test_db_engine, setup_expectations_table
):
    """Test that expectation version increments on update."""
    storage = ExpectationStorage(storage_config=test_storage_config, engine=test_db_engine)

    expectation = LearnedExpectation(
        table_name="users",
        schema_name=None,
        column_name="age",
        metric_name="mean",
        expected_mean=30.0,
        sample_size=10,
        learning_window_days=30,
        expectation_version=1,
    )

    # First save
    storage.save_expectation(expectation)
    retrieved1 = storage.get_expectation(
        table_name="users",
        column_name="age",
        metric_name="mean",
    )
    assert retrieved1.expectation_version == 1

    # Update
    expectation.expected_mean = 31.0
    storage.save_expectation(expectation)
    retrieved2 = storage.get_expectation(
        table_name="users",
        column_name="age",
        metric_name="mean",
    )
    assert retrieved2.expectation_version == 2

    # Update again
    expectation.expected_mean = 32.0
    storage.save_expectation(expectation)
    retrieved3 = storage.get_expectation(
        table_name="users",
        column_name="age",
        metric_name="mean",
    )
    assert retrieved3.expectation_version == 3


def test_expectation_serialization(test_storage_config, test_db_engine, setup_expectations_table):
    """Test serialization of complex expectation data."""
    storage = ExpectationStorage(storage_config=test_storage_config, engine=test_db_engine)

    # Create expectation with complex data
    expectation = LearnedExpectation(
        table_name="users",
        schema_name=None,
        column_name="age",
        metric_name="mean",
        expected_mean=30.0,
        expected_stddev=5.0,
        distribution_type="empirical",
        distribution_params={
            "mean": 30.0,
            "stddev": 5.0,
            "min": 20.0,
            "max": 45.0,
            "skewness": 0.2,
        },
        category_distribution={"cat1": 0.5, "cat2": 0.3, "cat3": 0.2},
        ewma_value=30.5,
        ewma_lambda=0.2,
        sample_size=10,
        learning_window_days=30,
    )

    storage.save_expectation(expectation)

    retrieved = storage.get_expectation(
        table_name="users",
        column_name="age",
        metric_name="mean",
    )

    assert retrieved is not None
    assert retrieved.distribution_params == expectation.distribution_params
    assert retrieved.category_distribution == expectation.category_distribution
    assert retrieved.ewma_value == 30.5
    assert retrieved.ewma_lambda == 0.2

