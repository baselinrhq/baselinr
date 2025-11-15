"""
Example Airflow DAG with ProfileMesh plan sensor.

This DAG demonstrates how to use the ProfileMeshPlanSensor to
automatically trigger profiling when the plan changes.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

from profilemesh.integrations.airflow import (
    ProfileMeshPlanSensor,
    ProfileMeshProfilingOperator,
)

# Determine config path
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


# DAG with sensor that monitors plan changes
with DAG(
    "profilemesh_plan_monitor",
    default_args=default_args,
    description="Monitor ProfileMesh plan changes and trigger profiling",
    schedule_interval="@hourly",  # Check hourly
    catchup=False,
    tags=["profilemesh", "sensor", "monitoring"],
) as dag_sensor:

    # Sensor that detects plan changes
    plan_sensor = ProfileMeshPlanSensor(
        task_id="detect_plan_changes",
        config_path=CONFIG_PATH,
        poke_interval=300,  # Check every 5 minutes
        timeout=3600,  # Timeout after 1 hour
        mode="poke",  # Use poke mode (reschedule is also supported)
    )

    def process_plan_changes(**context):
        """Process detected plan changes."""
        ti = context["ti"]
        metadata = ti.xcom_pull(
            task_ids="detect_plan_changes",
            key="plan_change_metadata",
        )

        if metadata:
            print("Plan Changes Detected:")
            print(f"  Environment: {metadata['environment']}")
            print(f"  Changed Tables: {metadata['changed_tables']}")
            print(f"  Metrics Requested: {metadata['metrics_requested']}")
            print(f"  Drift Strategy: {metadata['drift_strategy']}")
            print(f"  Plan Signature: {metadata['plan_signature']}")

            # You can add custom logic here to handle specific changes
            # For example, send notifications, update external systems, etc.
        else:
            print("No plan changes detected")

    process_changes = PythonOperator(
        task_id="process_changes",
        python_callable=process_plan_changes,
    )

    # Run profiling on changed tables
    profile_changed = ProfileMeshProfilingOperator(
        task_id="profile_changed_tables",
        config_path=CONFIG_PATH,
    )

    def notify_completion(**context):
        """Notify that profiling is complete."""
        ti = context["ti"]
        summary = ti.xcom_pull(
            task_ids="profile_changed_tables",
            key="profiling_results",
        )

        if summary:
            print("Profiling Complete:")
            print(f"  Tables: {summary['tables_profiled']}")
            print(f"  Run ID: {summary['run_id']}")

            # Add notification logic here (e.g., Slack, email, PagerDuty)

    notify = PythonOperator(
        task_id="notify_completion",
        python_callable=notify_completion,
    )

    # Define workflow
    plan_sensor >> process_changes >> profile_changed >> notify
