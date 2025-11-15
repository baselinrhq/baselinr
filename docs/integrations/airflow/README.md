# Airflow Integration

ProfileMesh provides native integration with Apache Airflow, enabling you to orchestrate data profiling tasks as part of your Airflow workflows.

## Overview

The Airflow integration provides:

- **Operators**: Execute profiling tasks as Airflow tasks
- **Sensors**: Monitor plan changes and trigger DAGs automatically
- **Hooks**: Manage ProfileMesh configuration and execution
- **Event Emission**: Structured logging and XCom integration

## Installation

Install ProfileMesh with Airflow support:

```bash
pip install profilemesh[airflow]
```

Or install from source:

```bash
cd profilemesh
pip install -e ".[airflow]"
```

## Quick Start

### 1. Basic Profiling Operator

Profile all tables defined in your ProfileMesh configuration:

```python
from datetime import datetime
from airflow import DAG
from profilemesh.integrations.airflow import ProfileMeshProfilingOperator

default_args = {
    'owner': 'data-team',
    'start_date': datetime(2024, 1, 1),
}

with DAG('profile_all_tables', default_args=default_args, schedule_interval='@daily') as dag:
    profile_task = ProfileMeshProfilingOperator(
        task_id='profile_tables',
        config_path='/path/to/config.yml',
    )
```

### 2. Parallel Profiling with TaskGroup

Profile tables in parallel for better performance:

```python
from profilemesh.integrations.airflow import create_profiling_task_group

with DAG('profile_parallel', ...) as dag:
    profiling_tasks = create_profiling_task_group(
        group_id='profile_tables',
        config_path='/path/to/config.yml',
    )
```

### 3. Single Table Operator

Profile specific tables with fine-grained control:

```python
from profilemesh.integrations.airflow import ProfileMeshTableOperator

with DAG('profile_specific', ...) as dag:
    profile_users = ProfileMeshTableOperator(
        task_id='profile_users',
        config_path='/path/to/config.yml',
        table='users',
        schema='public',
    )
```

### 4. Plan Change Sensor

Automatically trigger profiling when the plan changes:

```python
from profilemesh.integrations.airflow import ProfileMeshPlanSensor

with DAG('monitor_plan', ...) as dag:
    plan_sensor = ProfileMeshPlanSensor(
        task_id='detect_changes',
        config_path='/path/to/config.yml',
        poke_interval=300,  # Check every 5 minutes
    )
    
    profile_task = ProfileMeshProfilingOperator(
        task_id='profile_changed',
        config_path='/path/to/config.yml',
    )
    
    plan_sensor >> profile_task
```

## Components

### ProfileMeshProfilingOperator

Main operator for executing profiling tasks.

**Parameters:**
- `config_path` (str): Path to ProfileMesh configuration file
- `table_patterns` (list, optional): Specific tables to profile
- `emit_xcom` (bool): Whether to emit results to XCom (default: True)

**Returns via XCom:**
- `profiling_results`: Dictionary with profiling summary and results

### ProfileMeshTableOperator

Operator for profiling a single table.

**Parameters:**
- `config_path` (str): Path to ProfileMesh configuration file
- `table` (str): Table name to profile
- `schema` (str, optional): Schema name
- `database` (str, optional): Database name

**Returns via XCom:**
- `profiling_result`: Dictionary with single table profiling result

### ProfileMeshPlanSensor

Sensor that detects changes in the profiling plan.

**Parameters:**
- `config_path` (str): Path to ProfileMesh configuration file
- `cursor_variable` (str, optional): Airflow Variable name for cursor storage
- `poke_interval` (int): Seconds between checks (default: 60)
- `timeout` (int): Timeout in seconds (default: 3600)
- `mode` (str): 'poke' or 'reschedule' (default: 'poke')

**Returns via XCom:**
- `plan_change_metadata`: Dictionary with change details

### ProfileMeshHook

Hook for managing ProfileMesh configuration and execution.

**Methods:**
- `get_config()`: Return the ProfileMesh configuration
- `build_plan()`: Build a profiling plan
- `get_engine()`: Create a ProfileEngine instance

## Docker Setup

### Using Docker Compose

Start the full stack including Airflow:

```bash
# Start all services
docker compose -f docker/docker-compose.yml up -d

# Access Airflow UI at http://localhost:8080
# Username: admin
# Password: admin

# View logs
docker compose -f docker/docker-compose.yml logs -f airflow_webserver
docker compose -f docker/docker-compose.yml logs -f airflow_scheduler

# Stop services
docker compose -f docker/docker-compose.yml down -v
```

### Services

The Docker Compose setup includes:

- **airflow_postgres** (port 5434): Airflow metadata database
- **airflow_webserver** (port 8080): Airflow UI and API
- **airflow_scheduler**: Airflow task scheduler
- **postgres** (port 5433): ProfileMesh source/storage database

## Configuration

### Environment Variables

Configure ProfileMesh via environment variables in Airflow:

```yaml
environment:
  - PROFILEMESH_CONFIG=/path/to/config.yml
  - PROFILEMESH_SOURCE__HOST=postgres
  - PROFILEMESH_SOURCE__PORT=5432
  - PROFILEMESH_STORAGE__CONNECTION__HOST=postgres
  - PROFILEMESH_STORAGE__CONNECTION__PORT=5432
```

### Airflow Variables

The plan sensor uses Airflow Variables for cursor storage:

```python
from airflow.models import Variable

# Manual cursor management
cursor = Variable.get('profilemesh_plan_cursor', default_var=None)
Variable.set('profilemesh_plan_cursor', new_cursor_value)
```

## Examples

See the `examples/airflow_dags/` directory for complete examples:

- `profilemesh_dag.py`: Basic profiling workflows
- `profilemesh_sensor_dag.py`: Plan monitoring with sensors

## Comparison with Dagster

| Feature | Dagster | Airflow |
|---------|---------|---------|
| Paradigm | Declarative (Assets) | Imperative (Tasks) |
| Parallelism | Automatic | TaskGroups |
| Metadata | Native | XCom + Logs |
| Sensors | Event-based | Polling-based |
| UI | Modern, asset-centric | Traditional, task-centric |

## Best Practices

### 1. Use TaskGroups for Parallelism

```python
# ✅ Good - Parallel execution
profiling_tasks = create_profiling_task_group(
    group_id='profile_tables',
    config_path=config_path,
)

# ❌ Less optimal - Sequential execution
profile_all = ProfileMeshProfilingOperator(
    task_id='profile_all',
    config_path=config_path,
)
```

### 2. Handle Failures Gracefully

```python
from airflow.operators.python import PythonOperator

def handle_failure(**context):
    # Send alerts, log errors, etc.
    pass

profile_task = ProfileMeshProfilingOperator(
    task_id='profile',
    config_path=config_path,
    on_failure_callback=handle_failure,
)
```

### 3. Use XCom for Downstream Tasks

```python
def process_results(**context):
    ti = context['ti']
    results = ti.xcom_pull(
        task_ids='profile_tables',
        key='profiling_results',
    )
    # Process results
    print(f"Profiled {results['tables_profiled']} tables")

process = PythonOperator(
    task_id='process_results',
    python_callable=process_results,
)

profile_task >> process
```

### 4. Monitor Plan Changes

```python
# Use sensors for reactive profiling
plan_sensor = ProfileMeshPlanSensor(
    task_id='detect_changes',
    config_path=config_path,
    poke_interval=300,  # 5 minutes
)

# Trigger profiling only when needed
plan_sensor >> profile_changed_tables
```

## Troubleshooting

### DAGs Not Appearing

1. Check DAG folder is correctly mounted:
   ```bash
   docker compose exec airflow_webserver ls -la /opt/airflow/dags
   ```

2. Check for import errors:
   ```bash
   docker compose exec airflow_webserver airflow dags list
   ```

3. Verify ProfileMesh is installed:
   ```bash
   docker compose exec airflow_webserver python -c "import profilemesh; print(profilemesh.__file__)"
   ```

### Operator Import Errors

Ensure the Airflow extra is installed:

```bash
pip install profilemesh[airflow]
```

Or in Docker:

```dockerfile
RUN pip install -e ".[airflow]"
```

### Database Connection Issues

Check environment variables are set correctly:

```python
# In your DAG
import os
print(os.getenv('PROFILEMESH_CONFIG'))
print(os.getenv('PROFILEMESH_SOURCE__HOST'))
```

### Sensor Not Detecting Changes

1. Check cursor variable exists:
   ```python
   from airflow.models import Variable
   cursor = Variable.get('profilemesh_plan_cursor', default_var=None)
   print(cursor)
   ```

2. Verify config file changes are reflected:
   ```bash
   docker compose exec airflow_webserver cat /app/examples/config.yml
   ```

## Testing

Run integration tests:

```bash
pytest tests/test_airflow_integration.py -v
```

Test DAG parsing:

```bash
python -c "from airflow.models import DagBag; dag_bag = DagBag(dag_folder='examples/airflow_dags'); print(dag_bag.dags.keys())"
```

## Resources

- [Airflow Documentation](https://airflow.apache.org/docs/)
- [ProfileMesh Examples](../../examples/)
- [GitHub Actions Workflow](../../.github/workflows/airflow-integration.yml)

## Support

For issues or questions:

1. Check the [troubleshooting section](#troubleshooting)
2. Review [example DAGs](../../examples/airflow_dags/)
3. Open an issue on GitHub
