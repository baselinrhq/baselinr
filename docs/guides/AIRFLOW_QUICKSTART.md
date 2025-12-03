# Airflow Integration Quick Start

Get started with Baselinr and Airflow in 5 minutes.

## Installation

```bash
pip install baselinr[airflow]
```

## Minimal Example

Create a file `baselinr_dag.py` in your Airflow `dags/` directory:

```python
from airflow import DAG
from airflow.utils.dates import days_ago
from baselinr.integrations.airflow import BaselinrProfileOperator

default_args = {
    "owner": "data-engineering",
    "retries": 1,
}

dag = DAG(
    "baselinr_quickstart",
    default_args=default_args,
    description="Baselinr quick start",
    schedule_interval="@daily",
    start_date=days_ago(1),
    catchup=False,
)

profile_task = BaselinrProfileOperator(
    task_id="profile_tables",
    config_path="/path/to/your/baselinr/config.yml",
    dag=dag,
)
```

## Configuration File

Create `/path/to/your/baselinr/config.yml`:

```yaml
environment: production
source:
  type: postgres
  host: localhost
  port: 5432
  database: mydb
  username: user
  password: pass

storage:
  connection:
    type: postgres
    host: localhost
    port: 5432
    database: baselinr
    username: user
    password: pass

profiling:
  tables:
    - table: customers
    - table: orders
```

## Run the DAG

1. Start Airflow: `airflow webserver` and `airflow scheduler`
2. Open Airflow UI: http://localhost:8080
3. Find your DAG: `baselinr_quickstart`
4. Trigger it manually or wait for the schedule

## Add Drift Detection

```python
from baselinr.integrations.airflow import (
    BaselinrProfileOperator,
    BaselinrDriftOperator,
)

profile_task = BaselinrProfileOperator(
    task_id="profile_tables",
    config_path="/path/to/config.yml",
    dag=dag,
)

drift_task = BaselinrDriftOperator(
    task_id="check_drift",
    config_path="/path/to/config.yml",
    dataset_name="customers",
    fail_on_severity="high",
    dag=dag,
)

profile_task >> drift_task
```

## Next Steps

- Read the [full Airflow Integration Guide](AIRFLOW_INTEGRATION.md)
- Check out [example DAGs](../../examples/airflow_dag_example.py)
- Learn about [drift detection](DRIFT_DETECTION.md)
- Explore [root cause analysis](ROOT_CAUSE_ANALYSIS.md)

