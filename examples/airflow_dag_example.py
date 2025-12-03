"""
Example Airflow DAGs for Baselinr integration.

This file contains several example DAGs demonstrating different patterns
for using Baselinr with Airflow:
1. Basic profiling DAG
2. Profiling with drift detection
3. Scheduled profiling with alerts
4. Integration with dbt (run profiling after dbt run)
5. Multi-table profiling with dynamic task generation
"""

from datetime import datetime, timedelta
from typing import Dict

# Example 1: Basic Profiling DAG
from airflow import DAG
from airflow.operators.python import PythonOperator

try:
    from baselinr.integrations.airflow import (
        BaselinrDriftOperator,
        BaselinrProfileOperator,
        BaselinrQueryOperator,
    )
except ImportError:
    # If Airflow is not installed, these will be None
    BaselinrProfileOperator = None
    BaselinrDriftOperator = None
    BaselinrQueryOperator = None


# Example 1: Basic Profiling DAG
def create_basic_profiling_dag():
    """Create a basic DAG that profiles tables."""
    if not BaselinrProfileOperator:
        return None

    default_args = {
        "owner": "data-engineering",
        "depends_on_past": False,
        "email_on_failure": True,
        "email_on_retry": False,
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    }

    dag = DAG(
        "baselinr_basic_profiling",
        default_args=default_args,
        description="Basic Baselinr profiling DAG",
        schedule_interval=timedelta(days=1),
        start_date=datetime(2024, 1, 1),
        catchup=False,
        tags=["baselinr", "profiling"],
    )

    profile_task = BaselinrProfileOperator(
        task_id="profile_tables",
        config_path="/path/to/baselinr/config.yml",
        table_patterns=[{"pattern": "customers_*"}],
        dry_run=False,
        dag=dag,
    )

    return dag


# Example 2: Profiling with Drift Detection
def create_profiling_with_drift_dag():
    """Create a DAG that profiles and then checks for drift."""
    if not BaselinrProfileOperator or not BaselinrDriftOperator:
        return None

    default_args = {
        "owner": "data-engineering",
        "depends_on_past": False,
        "email_on_failure": True,
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    }

    dag = DAG(
        "baselinr_profiling_with_drift",
        default_args=default_args,
        description="Profile tables and detect drift",
        schedule_interval=timedelta(days=1),
        start_date=datetime(2024, 1, 1),
        catchup=False,
        tags=["baselinr", "profiling", "drift"],
    )

    # Profile tables
    profile_task = BaselinrProfileOperator(
        task_id="profile_tables",
        config_path="/path/to/baselinr/config.yml",
        dag=dag,
    )

    # Check for drift in critical tables
    drift_check_customers = BaselinrDriftOperator(
        task_id="check_drift_customers",
        config_path="/path/to/baselinr/config.yml",
        dataset_name="customers",
        fail_on_drift=False,  # Don't fail DAG on drift, just alert
        dag=dag,
    )

    drift_check_orders = BaselinrDriftOperator(
        task_id="check_drift_orders",
        config_path="/path/to/baselinr/config.yml",
        dataset_name="orders",
        fail_on_drift=False,
        dag=dag,
    )

    # Set dependencies
    profile_task >> [drift_check_customers, drift_check_orders]

    return dag


# Example 3: Scheduled Profiling with Alerts
def create_scheduled_profiling_dag():
    """Create a DAG that runs scheduled profiling and alerts on drift."""
    if not BaselinrProfileOperator or not BaselinrDriftOperator:
        return None

    default_args = {
        "owner": "data-engineering",
        "depends_on_past": False,
        "email_on_failure": True,
        "email_on_retry": False,
        "retries": 2,
        "retry_delay": timedelta(minutes=10),
    }

    dag = DAG(
        "baselinr_scheduled_profiling",
        default_args=default_args,
        description="Scheduled profiling with drift alerts",
        schedule_interval="0 2 * * *",  # Daily at 2 AM
        start_date=datetime(2024, 1, 1),
        catchup=False,
        tags=["baselinr", "profiling", "monitoring"],
    )

    # Profile all tables
    profile_task = BaselinrProfileOperator(
        task_id="profile_all_tables",
        config_path="/path/to/baselinr/config.yml",
        dag=dag,
    )

    # Check drift for critical tables (fail on high severity)
    critical_tables = ["customers", "orders", "payments"]

    drift_tasks = []
    for table in critical_tables:
        drift_task = BaselinrDriftOperator(
            task_id=f"check_drift_{table}",
            config_path="/path/to/baselinr/config.yml",
            dataset_name=table,
            fail_on_severity="high",  # Only fail on high severity drift
            dag=dag,
        )
        drift_tasks.append(drift_task)

    # Set dependencies
    profile_task >> drift_tasks

    return dag


# Example 4: Integration with dbt
def create_dbt_integration_dag():
    """Create a DAG that runs dbt and then profiles the resulting tables."""
    if not BaselinrProfileOperator:
        return None

    default_args = {
        "owner": "data-engineering",
        "depends_on_past": False,
        "email_on_failure": True,
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    }

    dag = DAG(
        "dbt_then_baselinr",
        default_args=default_args,
        description="Run dbt models then profile with Baselinr",
        schedule_interval=timedelta(days=1),
        start_date=datetime(2024, 1, 1),
        catchup=False,
        tags=["dbt", "baselinr", "profiling"],
    )

    # Run dbt (using BashOperator as example)
    from airflow.operators.bash import BashOperator

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command="cd /path/to/dbt/project && dbt run",
        dag=dag,
    )

    # Profile tables after dbt run
    profile_task = BaselinrProfileOperator(
        task_id="profile_dbt_tables",
        config_path="/path/to/baselinr/config.yml",
        table_patterns=[
            {"schema": "analytics", "select_schema": True}  # Profile all tables in analytics schema
        ],
        dag=dag,
    )

    # Set dependency: profile after dbt completes
    dbt_run >> profile_task

    return dag


# Example 5: Multi-table Profiling with Dynamic Task Generation
def create_dynamic_profiling_dag():
    """Create a DAG that dynamically generates profiling tasks for multiple tables."""
    if not BaselinrProfileOperator:
        return None

    default_args = {
        "owner": "data-engineering",
        "depends_on_past": False,
        "email_on_failure": True,
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    }

    dag = DAG(
        "baselinr_dynamic_profiling",
        default_args=default_args,
        description="Dynamic multi-table profiling",
        schedule_interval=timedelta(days=1),
        start_date=datetime(2024, 1, 1),
        catchup=False,
        tags=["baselinr", "profiling", "dynamic"],
    )

    # List of tables to profile (could come from config, database query, etc.)
    tables_to_profile = [
        {"table": "customers", "schema": "public"},
        {"table": "orders", "schema": "public"},
        {"table": "products", "schema": "public"},
        {"table": "reviews", "schema": "public"},
    ]

    # Generate profiling tasks dynamically
    profiling_tasks = []
    for table_info in tables_to_profile:
        task_id = f"profile_{table_info['table']}"
        profile_task = BaselinrProfileOperator(
            task_id=task_id,
            config_path="/path/to/baselinr/config.yml",
            table_patterns=[{"table": table_info["table"], "schema": table_info["schema"]}],
            dag=dag,
        )
        profiling_tasks.append(profile_task)

    # Optional: Add a summary task that queries all runs
    if BaselinrQueryOperator:
        summary_task = BaselinrQueryOperator(
            task_id="query_profiling_summary",
            config_path="/path/to/baselinr/config.yml",
            query_type="runs",
            days=1,
            limit=100,
            dag=dag,
        )

        # Set dependencies: summary after all profiling tasks
        profiling_tasks >> summary_task

    return dag


# Example 6: Query and Monitor DAG
def create_query_monitor_dag():
    """Create a DAG that queries Baselinr metadata and monitors drift."""
    if not BaselinrQueryOperator or not BaselinrDriftOperator:
        return None

    default_args = {
        "owner": "data-engineering",
        "depends_on_past": False,
        "email_on_failure": True,
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    }

    dag = DAG(
        "baselinr_query_monitor",
        default_args=default_args,
        description="Query Baselinr metadata and monitor drift",
        schedule_interval="0 */6 * * *",  # Every 6 hours
        start_date=datetime(2024, 1, 1),
        catchup=False,
        tags=["baselinr", "monitoring", "query"],
    )

    # Query recent runs
    query_runs = BaselinrQueryOperator(
        task_id="query_recent_runs",
        config_path="/path/to/baselinr/config.yml",
        query_type="runs",
        days=1,
        limit=50,
        dag=dag,
    )

    # Query drift events
    query_drift = BaselinrQueryOperator(
        task_id="query_drift_events",
        config_path="/path/to/baselinr/config.yml",
        query_type="drift",
        days=7,
        severity="high",
        limit=100,
        dag=dag,
    )

    # Check drift for specific table
    check_drift = BaselinrDriftOperator(
        task_id="check_critical_table_drift",
        config_path="/path/to/baselinr/config.yml",
        dataset_name="customers",
        fail_on_severity="high",
        dag=dag,
    )

    # Set dependencies
    [query_runs, query_drift] >> check_drift

    return dag


# Export DAGs (Airflow will discover these)
# Uncomment the DAG you want to use:

# dag = create_basic_profiling_dag()
# dag = create_profiling_with_drift_dag()
# dag = create_scheduled_profiling_dag()
# dag = create_dbt_integration_dag()
# dag = create_dynamic_profiling_dag()
# dag = create_query_monitor_dag()
