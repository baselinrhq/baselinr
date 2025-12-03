"""
Test DAG for Baselinr Airflow integration.

This DAG demonstrates basic usage of Baselinr operators in Airflow.
Place this file in /opt/airflow/dags/ (or mount it via docker-compose volume).
"""

from datetime import datetime, timedelta
from airflow import DAG
from baselinr.integrations.airflow import (
    BaselinrProfileOperator,
    BaselinrDriftOperator,
    BaselinrQueryOperator,
)

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# Test DAG 1: Basic profiling
with DAG(
    "baselinr_test_profile",
    default_args=default_args,
    description="Test Baselinr Profile Operator",
    schedule_interval=None,  # Manual trigger only
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["baselinr", "test", "profile"],
) as dag_profile:
    profile_task = BaselinrProfileOperator(
        task_id="profile_test",
        config_path="/app/examples/config.yml",
        dag=dag_profile,
    )

# Test DAG 2: Profile with drift detection
with DAG(
    "baselinr_test_drift",
    default_args=default_args,
    description="Test Baselinr Drift Operator",
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["baselinr", "test", "drift"],
) as dag_drift:
    drift_task = BaselinrDriftOperator(
        task_id="drift_test",
        config_path="/app/examples/config.yml",
        dataset_name="customers",  # Required: name of the dataset/table to check for drift
        dag=dag_drift,
    )

# Test DAG 3: Query metadata
with DAG(
    "baselinr_test_query",
    default_args=default_args,
    description="Test Baselinr Query Operator",
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["baselinr", "test", "query"],
) as dag_query:
    query_task = BaselinrQueryOperator(
        task_id="query_test",
        config_path="/app/examples/config.yml",
        query_type="runs",  # Query type: runs, drift, table_history, run_details
        limit=10,  # Limit to 10 results
        dag=dag_query,
    )

# Test DAG 4: Combined workflow
with DAG(
    "baselinr_test_combined",
    default_args=default_args,
    description="Test combined Baselinr workflow",
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["baselinr", "test", "combined"],
) as dag_combined:
    profile = BaselinrProfileOperator(
        task_id="profile",
        config_path="/app/examples/config.yml",
        dag=dag_combined,
    )

    drift = BaselinrDriftOperator(
        task_id="drift",
        config_path="/app/examples/config.yml",
        dataset_name="customers",  # Required: name of the dataset/table to check for drift
        dag=dag_combined,
    )

    query = BaselinrQueryOperator(
        task_id="query_results",
        config_path="/app/examples/config.yml",
        query_type="runs",  # Query type: runs, drift, table_history, run_details
        limit=5,  # Limit to 5 results
        dag=dag_combined,
    )

    # Set task dependencies
    profile >> drift >> query

