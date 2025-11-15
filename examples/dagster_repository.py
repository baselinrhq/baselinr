"""
Dagster repository example for ProfileMesh.

This file defines Dagster assets and jobs for profiling tasks.
It demonstrates how to integrate ProfileMesh with Dagster for
orchestration and scheduling.
"""

import os
from pathlib import Path

from dagster import Definitions, ScheduleDefinition

from profilemesh.integrations.dagster import (
    ProfileMeshResource,
    create_profiling_assets,
    create_profiling_job,
    profilemesh_plan_sensor,
)

# Determine config path
# In Docker, this will be /app/examples/config.yml
# In local development, adjust as needed
CONFIG_PATH = os.getenv(
    "PROFILEMESH_CONFIG",
    str(Path(__file__).parent / "config.yml")
)

# Create profiling assets from configuration
try:
    profiling_assets = create_profiling_assets(
        config_path=CONFIG_PATH,
        asset_name_prefix="profilemesh",
    )

    profiling_job = create_profiling_job(
        assets=profiling_assets,
        job_name="profile_all_tables",
    )

    plan_sensor = profilemesh_plan_sensor(
        config_path=CONFIG_PATH,
        job_name="profile_all_tables",
        asset_prefix="profilemesh",
        sensor_name="profilemesh_plan_sensor",
    )

    # Create a schedule to run profiling daily at midnight
    daily_profiling_schedule = ScheduleDefinition(
        name="daily_profiling",
        job=profiling_job,
        cron_schedule="0 0 * * *",  # Daily at midnight
        description="Run ProfileMesh profiling daily"
    )

    defs = Definitions(
        assets=profiling_assets,
        jobs=[profiling_job],
        schedules=[daily_profiling_schedule],
        sensors=[plan_sensor],
        resources={"profilemesh": ProfileMeshResource(config_path=CONFIG_PATH)},
    )

except Exception as e:
    print(f"Warning: Failed to create ProfileMesh Dagster assets: {e}")
    print(f"Config path: {CONFIG_PATH}")
    
    # Create empty definitions as fallback
    defs = Definitions(
        assets=[],
        jobs=[],
        schedules=[]
    )

