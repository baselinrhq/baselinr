# Airflow Integration Guide

Baselinr provides comprehensive integration with Apache Airflow 2.x to enable scalable profiling and drift detection within your Airflow workflows.

## Overview

The Airflow integration includes:
- **Operators**: `BaselinrProfileOperator`, `BaselinrDriftOperator`, `BaselinrQueryOperator`
- **RCA Collector**: Automatic collection of Airflow DAG run metadata for root cause analysis
- **XCom Support**: Results are automatically passed via XCom for downstream tasks

## Installation

Install Baselinr with Airflow support:

```bash
pip install baselinr[airflow]
```

Or install Airflow separately:

```bash
pip install baselinr
pip install apache-airflow>=2.0.0,<3.0.0
```

## Quick Start

### Basic Profiling DAG

```python
from airflow import DAG
from airflow.utils.dates import days_ago
from baselinr.integrations.airflow import BaselinrProfileOperator

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 1,
}

dag = DAG(
    "baselinr_profiling",
    default_args=default_args,
    description="Basic Baselinr profiling",
    schedule_interval="@daily",
    start_date=days_ago(1),
    catchup=False,
)

profile_task = BaselinrProfileOperator(
    task_id="profile_tables",
    config_path="/path/to/baselinr/config.yml",
    dag=dag,
)
```

## Operators

### BaselinrProfileOperator

Runs Baselinr profiling and returns results via XCom.

**Parameters:**
- `config_path` (str, optional): Path to Baselinr configuration file
- `config` (dict, optional): Baselinr configuration dictionary (alternative to config_path)
- `table_patterns` (list, optional): List of table patterns to profile. If not provided, uses patterns from config.
- `dry_run` (bool): If True, profile but don't write to storage (default: False)
- Standard Airflow operator parameters (`task_id`, `dag`, etc.)

**XCom Return Value:**
```python
{
    "run_ids": ["run-123", "run-456"],
    "tables_profiled": ["customers", "orders"],
    "tables_count": 2,
    "results_count": 2,
}
```

**Example:**
```python
profile_task = BaselinrProfileOperator(
    task_id="profile_customers",
    config_path="/path/to/config.yml",
    table_patterns=[{"table": "customers", "schema": "public"}],
    dag=dag,
)
```

### BaselinrDriftOperator

Detects drift between profiling runs and optionally fails the DAG on drift.

**Parameters:**
- `config_path` (str, optional): Path to Baselinr configuration file
- `config` (dict, optional): Baselinr configuration dictionary
- `dataset_name` (str, required): Name of the dataset/table to check
- `schema_name` (str, optional): Schema name
- `baseline_run_id` (str, optional): Run ID to use as baseline (default: auto-selected)
- `current_run_id` (str, optional): Run ID to compare (default: latest run)
- `fail_on_drift` (bool): If True, raise exception if any drift is detected (default: False)
- `fail_on_severity` (str, optional): Only fail on drift of this severity or higher (low/medium/high)

**XCom Return Value:**
```python
{
    "has_drift": True,
    "column_drifts_count": 3,
    "schema_changes_count": 0,
    "severity_counts": {"low": 1, "medium": 1, "high": 1},
    "drift_report": {...},
}
```

**Example:**
```python
drift_task = BaselinrDriftOperator(
    task_id="check_drift",
    config_path="/path/to/config.yml",
    dataset_name="customers",
    fail_on_severity="high",  # Only fail on high severity drift
    dag=dag,
)
```

### BaselinrQueryOperator

Queries Baselinr metadata (runs, drift events, table history, etc.).

**Parameters:**
- `config_path` (str, optional): Path to Baselinr configuration file
- `config` (dict, optional): Baselinr configuration dictionary
- `query_type` (str): Type of query - one of: `runs`, `drift`, `table_history`, `run_details`
- Query-specific parameters (passed as kwargs):
  - For `runs`: `schema`, `table`, `status`, `environment`, `days`, `limit`, `offset`
  - For `drift`: `table`, `schema`, `severity`, `days`, `limit`, `offset`
  - For `table_history`: `table` (required), `schema`, `days`, `limit`
  - For `run_details`: `run_id` (required), `dataset_name`

**Example:**
```python
query_task = BaselinrQueryOperator(
    task_id="query_recent_runs",
    config_path="/path/to/config.yml",
    query_type="runs",
    days=7,
    limit=50,
    dag=dag,
)
```

## Common Patterns

### Pattern 1: Profile Then Check Drift

```python
from baselinr.integrations.airflow import (
    BaselinrProfileOperator,
    BaselinrDriftOperator,
)

# Profile tables
profile_task = BaselinrProfileOperator(
    task_id="profile_tables",
    config_path="/path/to/config.yml",
    dag=dag,
)

# Check drift for critical tables
drift_check = BaselinrDriftOperator(
    task_id="check_drift",
    config_path="/path/to/config.yml",
    dataset_name="customers",
    fail_on_severity="high",
    dag=dag,
)

profile_task >> drift_check
```

### Pattern 2: Integration with dbt

```python
from airflow.operators.bash import BashOperator
from baselinr.integrations.airflow import BaselinrProfileOperator

# Run dbt
dbt_run = BashOperator(
    task_id="dbt_run",
    bash_command="cd /path/to/dbt && dbt run",
    dag=dag,
)

# Profile dbt models
profile_dbt = BaselinrProfileOperator(
    task_id="profile_dbt_models",
    config_path="/path/to/config.yml",
    table_patterns=[{"schema": "analytics", "select_schema": True}],
    dag=dag,
)

dbt_run >> profile_dbt
```

### Pattern 3: Dynamic Task Generation

```python
tables_to_profile = ["customers", "orders", "products"]

profiling_tasks = []
for table in tables_to_profile:
    task = BaselinrProfileOperator(
        task_id=f"profile_{table}",
        config_path="/path/to/config.yml",
        table_patterns=[{"table": table}],
        dag=dag,
    )
    profiling_tasks.append(task)
```

### Pattern 4: Scheduled Monitoring

```python
dag = DAG(
    "baselinr_monitoring",
    schedule_interval="0 */6 * * *",  # Every 6 hours
    start_date=days_ago(1),
    catchup=False,
)

# Query recent drift events
query_drift = BaselinrQueryOperator(
    task_id="query_drift",
    config_path="/path/to/config.yml",
    query_type="drift",
    days=7,
    severity="high",
    dag=dag,
)

# Check specific table
check_drift = BaselinrDriftOperator(
    task_id="check_critical_drift",
    config_path="/path/to/config.yml",
    dataset_name="customers",
    fail_on_severity="high",
    dag=dag,
)

query_drift >> check_drift
```

## RCA Collector Configuration

The Airflow RCA collector automatically collects DAG run metadata for root cause analysis. Configure it in your Baselinr config:

```yaml
rca:
  enabled: true
  collectors:
    airflow: true
    airflow_api_url: "http://localhost:8080/api/v1"
    airflow_api_version: "v1"  # or "v2"
    airflow_username: "admin"  # Optional
    airflow_password: "admin"  # Optional
    airflow_metadata_db_connection: "postgresql://user:pass@localhost/airflow"  # Optional
    airflow_dag_ids:  # Optional: filter specific DAGs
      - "my_dag"
      - "another_dag"
```

### Collection Methods

The collector supports three methods (tries each in order):

1. **REST API**: Uses Airflow REST API (v1 or v2)
2. **Metadata Database**: Direct SQL access to Airflow's metadata database
3. **Environment Variables**: For Airflow Cloud/Managed environments

### Environment Variables

The collector can also be configured via environment variables:

- `AIRFLOW_API_URL`: Airflow API URL
- `AIRFLOW_API_VERSION`: API version (v1 or v2)
- `AIRFLOW_USERNAME`: Username for API auth
- `AIRFLOW_PASSWORD`: Password for API auth
- `AIRFLOW_METADATA_DB_CONNECTION`: Database connection string
- `AIRFLOW_CTX_DAG_ID`: Current DAG ID (set by Airflow)
- `AIRFLOW_CTX_RUN_ID`: Current run ID (set by Airflow)

## Best Practices

### 1. Use Config Files

Store Baselinr configuration in version-controlled YAML files rather than passing dicts:

```python
# Good
BaselinrProfileOperator(
    task_id="profile",
    config_path="/path/to/config.yml",
    dag=dag,
)

# Less ideal
BaselinrProfileOperator(
    task_id="profile",
    config={"source": {...}, "storage": {...}},  # Hard to maintain
    dag=dag,
)
```

### 2. Fail on High Severity Only

Use `fail_on_severity` instead of `fail_on_drift` to avoid failing on minor drifts:

```python
BaselinrDriftOperator(
    task_id="check_drift",
    dataset_name="customers",
    fail_on_severity="high",  # Only fail on high severity
    dag=dag,
)
```

### 3. Use XCom for Downstream Tasks

Access profiling results in downstream tasks:

```python
def process_profiling_results(**context):
    ti = context["ti"]
    profiling_summary = ti.xcom_pull(task_ids="profile_tables")
    run_ids = profiling_summary["run_ids"]
    # Process results...

process_task = PythonOperator(
    task_id="process_results",
    python_callable=process_profiling_results,
    dag=dag,
)

profile_task >> process_task
```

### 4. Separate Profiling and Drift Detection

Run profiling and drift detection in separate tasks for better observability:

```python
profile_task = BaselinrProfileOperator(...)
drift_task = BaselinrDriftOperator(...)

profile_task >> drift_task
```

### 5. Use Dynamic Task Generation for Many Tables

For large numbers of tables, use dynamic task generation:

```python
tables = get_tables_from_config()  # Your function
tasks = [
    BaselinrProfileOperator(
        task_id=f"profile_{table}",
        table_patterns=[{"table": table}],
        ...
    )
    for table in tables
]
```

## Troubleshooting

### ImportError: Airflow is not installed

Install Airflow:
```bash
pip install apache-airflow>=2.0.0,<3.0.0
```

### Operator fails with "Provide either config_path or config"

You must provide exactly one of `config_path` or `config`:

```python
# Correct
BaselinrProfileOperator(config_path="/path/to/config.yml", ...)

# Also correct
BaselinrProfileOperator(config={"source": {...}}, ...)

# Wrong
BaselinrProfileOperator(config_path="...", config={...}, ...)  # Both provided
BaselinrProfileOperator(...)  # Neither provided
```

### RCA Collector not collecting runs

Check:
1. Airflow API is accessible: `curl http://localhost:8080/api/v1/health`
2. Credentials are correct (if using auth)
3. DAG IDs filter is not excluding your DAGs
4. Check collector logs for errors

### XCom data too large

If profiling results are too large for XCom:
1. Use `dry_run=True` to test without storing results
2. Store results in external storage and pass references via XCom
3. Use `BaselinrQueryOperator` to query results instead of passing via XCom

## Examples

See `examples/airflow_dag_example.py` for comprehensive examples including:
- Basic profiling DAG
- Profiling with drift detection
- Scheduled profiling with alerts
- Integration with dbt
- Multi-table profiling with dynamic task generation
- Query and monitor DAG

## Additional Resources

- [Quick Start Guide](AIRFLOW_QUICKSTART.md)
- [Python SDK Guide](PYTHON_SDK.md)
- [Drift Detection Guide](DRIFT_DETECTION.md)
- [Root Cause Analysis Guide](ROOT_CAUSE_ANALYSIS.md)

