# Dagster Integration Guide

Baselinr provides comprehensive integration with Dagster to enable scalable profiling and drift detection within your Dagster workflows.

## Overview

The Dagster integration includes:
- **Dynamic Assets**: Automatically create Dagster assets from your Baselinr configuration
- **Profiling Jobs**: Create jobs to run profiling for all configured tables
- **Sensors**: Intelligent sensors that use Baselinr's planning system to determine which tables need profiling
- **Resources**: BaselinrResource for accessing Baselinr functionality within Dagster ops
- **RCA Collector**: Automatic collection of Dagster run metadata for root cause analysis

## Installation

Install Baselinr with Dagster support:

```bash
pip install baselinr[dagster]
```

Or install Dagster separately:

```bash
pip install baselinr
pip install dagster dagster-webserver
```

## Quick Start

### Basic Integration

The simplest way to integrate Baselinr with Dagster is using `build_baselinr_definitions`:

```python
from baselinr.integrations.dagster import build_baselinr_definitions

defs = build_baselinr_definitions(
    config_path="config.yml",
    asset_prefix="baselinr",
    job_name="baselinr_profile_all",
    enable_sensor=True,  # optional
)
```

This creates:
- One asset per table in your configuration
- A job to run all profiling assets
- An optional sensor that uses Baselinr's planning system

### Complete Example

```python
"""
Dagster repository example for Baselinr.

This file defines Dagster assets and jobs for profiling tasks.
It demonstrates how to integrate Baselinr with Dagster for
orchestration and scheduling.
"""

import os
from pathlib import Path

from dagster import Definitions, ScheduleDefinition

from baselinr.integrations.dagster import (
    BaselinrResource,
    baselinr_plan_sensor,
    create_profiling_assets,
    create_profiling_job,
)

# Determine config path
CONFIG_PATH = os.getenv("BASELINR_CONFIG", str(Path(__file__).parent / "config.yml"))

# Create profiling assets from configuration
profiling_assets = create_profiling_assets(
    config_path=CONFIG_PATH,
    asset_name_prefix="baselinr",
)

profiling_job = create_profiling_job(
    assets=profiling_assets,
    job_name="profile_all_tables",
)

plan_sensor = baselinr_plan_sensor(
    config_path=CONFIG_PATH,
    job_name="profile_all_tables",
    asset_prefix="baselinr",
    sensor_name="baselinr_plan_sensor",
)

# Create a schedule to run profiling daily at midnight
daily_profiling_schedule = ScheduleDefinition(
    name="daily_profiling",
    job=profiling_job,
    cron_schedule="0 0 * * *",  # Daily at midnight
    description="Run Baselinr profiling daily",
)

defs = Definitions(
    assets=profiling_assets,
    jobs=[profiling_job],
    schedules=[daily_profiling_schedule],
    sensors=[plan_sensor],
    resources={"baselinr": BaselinrResource(config_path=CONFIG_PATH)},
)
```

## Core Components

### build_baselinr_definitions

The simplest way to get started. Creates all necessary Dagster components from your Baselinr configuration.

**Parameters:**
- `config_path` (str, required): Path to Baselinr configuration file
- `asset_prefix` (str, default: "baselinr"): Prefix for asset keys
- `job_name` (str, default: "baselinr_profile_all"): Name of the profiling job
- `enable_sensor` (bool, default: True): Whether to create the planning sensor
- `group_name` (str, default: "baselinr_profiling"): Asset group name
- `default_tags` (dict, optional): Default tags for assets
- `default_metadata` (dict, optional): Default metadata for assets

**Returns:** `Definitions` object ready to use in your Dagster repository

**Example:**
```python
defs = build_baselinr_definitions(
    config_path="config.yml",
    asset_prefix="data_quality",
    job_name="profile_warehouse",
    enable_sensor=True,
)
```

### create_profiling_assets

Creates Dagster assets dynamically from your Baselinr configuration.

**Parameters:**
- `config_path` (str, required): Path to Baselinr configuration file
- `asset_name_prefix` (str, default: "baselinr"): Prefix for asset keys
- `group_name` (str, default: "baselinr_profiling"): Asset group name
- `default_tags` (dict, optional): Default tags for assets
- `default_metadata` (dict, optional): Default metadata for assets

**Returns:** List of Dagster assets (one per table in configuration)

**Example:**
```python
from baselinr.integrations.dagster import create_profiling_assets

assets = create_profiling_assets(
    config_path="config.yml",
    asset_name_prefix="baselinr",
    group_name="data_quality",
)
```

### create_profiling_job

Creates a Dagster job to run all profiling assets.

**Parameters:**
- `assets` (list, required): List of profiling assets
- `job_name` (str, default: "baselinr_profile_all"): Name of the job

**Returns:** Dagster job definition

**Example:**
```python
from baselinr.integrations.dagster import create_profiling_job

job = create_profiling_job(
    assets=profiling_assets,
    job_name="profile_all_tables",
)
```

### baselinr_plan_sensor

Creates a sensor that uses Baselinr's planning system to intelligently determine which tables need profiling.

**Parameters:**
- `config_path` (str, required): Path to Baselinr configuration file
- `job_name` (str, required): Name of the job to trigger
- `asset_prefix` (str, required): Prefix used for asset keys
- `sensor_name` (str, default: "baselinr_plan_sensor"): Name of the sensor

**Returns:** Dagster sensor definition

**Example:**
```python
from baselinr.integrations.dagster import baselinr_plan_sensor

sensor = baselinr_plan_sensor(
    config_path="config.yml",
    job_name="profile_all_tables",
    asset_prefix="baselinr",
    sensor_name="baselinr_plan_sensor",
)
```

### BaselinrResource

A Dagster resource that provides access to Baselinr functionality within ops.

**Parameters:**
- `config_path` (str, required): Path to Baselinr configuration file

**Example:**
```python
from dagster import op
from baselinr.integrations.dagster import BaselinrResource

@op(required_resource_keys={"baselinr"})
def custom_profiling_op(context):
    baselinr = context.resources.baselinr
    # Use baselinr client here
    results = baselinr.profile()
    return results
```

## Advanced Usage

### Custom Asset Definitions

You can create custom assets with additional logic:

```python
from dagster import asset, AssetExecutionContext
from baselinr.integrations.dagster import BaselinrResource

@asset(
    key=["baselinr", "customers"],
    group_name="data_quality",
    required_resource_keys={"baselinr"},
)
def profile_customers(context: AssetExecutionContext):
    """Profile customers table with custom logic."""
    baselinr = context.resources.baselinr
    
    # Run profiling
    results = baselinr.profile(table="customers", schema="public")
    
    # Custom post-processing
    if results:
        # Send notification, update metadata, etc.
        pass
    
    return results
```

### Incremental Profiling with Sensors

The `baselinr_plan_sensor` integrates with Baselinr's incremental profiling system:

```python
sensor = baselinr_plan_sensor(
    config_path="config.yml",
    job_name="profile_all_tables",
    asset_prefix="baselinr",
)
```

This sensor:
- Uses Baselinr's planning system to determine which tables need profiling
- Only triggers profiling for tables that have changed or need updates
- Reduces unnecessary work and costs

### Schedules

Create schedules to run profiling on a regular cadence:

```python
from dagster import ScheduleDefinition

daily_profiling = ScheduleDefinition(
    name="daily_profiling",
    job=profiling_job,
    cron_schedule="0 0 * * *",  # Daily at midnight
    description="Run Baselinr profiling daily",
)

hourly_profiling = ScheduleDefinition(
    name="hourly_profiling",
    job=profiling_job,
    cron_schedule="0 * * * *",  # Every hour
    description="Run Baselinr profiling hourly",
)
```

### Root Cause Analysis Integration

Baselinr automatically collects Dagster run metadata for root cause analysis:

```python
from baselinr.rca.collectors import DagsterRunCollector

# Configure in your Baselinr config or code
collector = DagsterRunCollector(
    instance_path="/path/to/.dagster",  # Optional, uses DAGSTER_HOME env var
    graphql_url="http://localhost:3000/graphql",  # Optional
)
```

This enables Baselinr to correlate data quality issues with Dagster pipeline runs.

## Configuration

### Basic Configuration

Your Baselinr configuration file (`config.yml`) defines which tables to profile:

```yaml
source:
  type: postgres
  host: localhost
  database: mydb
  username: user
  password: password

storage:
  connection:
    type: postgres
    host: localhost
    database: baselinr
    username: user
    password: password

profiling:
  tables:
    - table: customers
      schema: public
    - table: orders
      schema: public
```

### Environment Variables

You can override the config path using environment variables:

```bash
export BASELINR_CONFIG=/path/to/config.yml
```

## Best Practices

1. **Use Sensors for Incremental Profiling**: The `baselinr_plan_sensor` integrates with Baselinr's planning system to only profile tables that need updates.

2. **Group Assets**: Use asset groups to organize profiling assets:
   ```python
   assets = create_profiling_assets(
       config_path="config.yml",
       group_name="data_quality",
   )
   ```

3. **Tag Assets**: Add tags for better organization and filtering:
   ```python
   assets = create_profiling_assets(
       config_path="config.yml",
       default_tags={"team": "data-engineering", "domain": "analytics"},
   )
   ```

4. **Separate Jobs for Different Environments**: Create separate jobs for dev/staging/prod:
   ```python
   dev_job = create_profiling_job(
       assets=dev_assets,
       job_name="profile_dev",
   )
   
   prod_job = create_profiling_job(
       assets=prod_assets,
       job_name="profile_prod",
   )
   ```

5. **Use Resources for Custom Logic**: Use `BaselinrResource` when you need custom profiling logic within ops.

## Troubleshooting

### Assets Not Appearing

- Check that your config file path is correct
- Verify that tables are properly configured in `profiling.tables`
- Check Dagster logs for errors during asset creation

### Sensor Not Triggering

- Ensure the sensor is included in your `Definitions`
- Check that the job name matches between sensor and job
- Verify the asset prefix matches

### Import Errors

- Ensure Dagster is installed: `pip install baselinr[dagster]`
- Check that you're using compatible versions (Dagster 1.0+)

## See Also

- [Airflow Integration](AIRFLOW_INTEGRATION.md) - Similar integration for Airflow
- [Incremental Profiling](INCREMENTAL_PROFILING.md) - How the planning system works
- [Root Cause Analysis](ROOT_CAUSE_ANALYSIS.md) - Using Dagster metadata for RCA
- [Data Lineage](DATA_LINEAGE.md) - Dagster lineage provider


