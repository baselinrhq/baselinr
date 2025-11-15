"""
Example Airflow DAG for ProfileMesh profiling.

This DAG demonstrates how to use ProfileMesh operators and sensors
in an Airflow workflow.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

from profilemesh.integrations.airflow import (
    ProfileMeshProfilingOperator,
    ProfileMeshTableOperator,
    create_profiling_task_group,
)

# Determine config path
# In Docker, this will be /app/examples/config.yml
CONFIG_PATH = os.getenv(
    "PROFILEMESH_CONFIG",
    str(Path(__file__).parent.parent / "config.yml"),
)

default_args = {
    "owner": "profilemesh",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


# DAG 1: Profile all tables with a single operator
with DAG(
    "profilemesh_profile_all",
    default_args=default_args,
    description="Profile all tables defined in ProfileMesh config",
    schedule_interval="@daily",
    catchup=False,
    tags=["profilemesh", "profiling"],
) as dag_profile_all:

    profile_all_tables = ProfileMeshProfilingOperator(
        task_id="profile_all_tables",
        config_path=CONFIG_PATH,
    )

    def log_summary(**context):
        """Log profiling summary from XCom."""
        ti = context["ti"]
        summary = ti.xcom_pull(
            task_ids="profile_all_tables",
            key="profiling_results",
        )
        if summary:
            print(f"Profiling Summary:")
            print(f"  Environment: {summary['environment']}")
            print(f"  Tables Profiled: {summary['tables_profiled']}")
            print(f"  Run ID: {summary['run_id']}")
            for result in summary["results"]:
                print(f"  - {result['dataset_name']}: {result['columns_profiled']} columns")

    log_summary_task = PythonOperator(
        task_id="log_summary",
        python_callable=log_summary,
    )

    profile_all_tables >> log_summary_task


# DAG 2: Profile tables in parallel using TaskGroup
with DAG(
    "profilemesh_profile_parallel",
    default_args=default_args,
    description="Profile tables in parallel using TaskGroup",
    schedule_interval="@daily",
    catchup=False,
    tags=["profilemesh", "profiling", "parallel"],
) as dag_profile_parallel:

    # Create a task group with one task per table
    profiling_tasks = create_profiling_task_group(
        group_id="profile_tables",
        config_path=CONFIG_PATH,
    )

    def aggregate_results(**context):
        """Aggregate results from all table profiling tasks."""
        ti = context["ti"]
        dag_run = context["dag_run"]

        print("Aggregating profiling results...")

        # Get all task instances in the profiling_tasks group
        task_instances = dag_run.get_task_instances()
        table_results = []

        for task_instance in task_instances:
            if task_instance.task_id.startswith("profile_tables."):
                result = ti.xcom_pull(
                    task_ids=task_instance.task_id,
                    key="profiling_result",
                )
                if result:
                    table_results.append(result)

        print(f"Profiled {len(table_results)} table(s):")
        for result in table_results:
            print(f"  - {result['dataset_name']}: {result['columns_profiled']} columns")

    aggregate_task = PythonOperator(
        task_id="aggregate_results",
        python_callable=aggregate_results,
    )

    profiling_tasks >> aggregate_task


# DAG 3: Profile specific tables
with DAG(
    "profilemesh_profile_specific",
    default_args=default_args,
    description="Profile specific tables only",
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    tags=["profilemesh", "profiling", "manual"],
) as dag_profile_specific:

    # Profile specific tables using individual operators
    # This gives you fine-grained control over task dependencies

    profile_users = ProfileMeshTableOperator(
        task_id="profile_users",
        config_path=CONFIG_PATH,
        table="users",
        schema="public",
    )

    profile_events = ProfileMeshTableOperator(
        task_id="profile_events",
        config_path=CONFIG_PATH,
        table="events",
        schema="public",
    )

    def validate_profile(**context):
        """Validate profiling results."""
        ti = context["ti"]
        result = ti.xcom_pull(
            task_ids=context["task"].upstream_task_ids,
            key="profiling_result",
        )
        if result:
            print(f"Validation for {result.get('dataset_name')}:")
            print(f"  Columns: {result.get('columns_profiled')}")
            print(f"  Rows: {result.get('row_count')}")

            # Add custom validation logic here
            if result.get("columns_profiled", 0) == 0:
                raise ValueError(f"No columns profiled for {result.get('dataset_name')}")

    validate_users = PythonOperator(
        task_id="validate_users",
        python_callable=validate_profile,
    )

    validate_events = PythonOperator(
        task_id="validate_events",
        python_callable=validate_profile,
    )

    # Define dependencies
    profile_users >> validate_users
    profile_events >> validate_events
