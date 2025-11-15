# Airflow Operators Reference

This document provides detailed reference for ProfileMesh Airflow operators.

## ProfileMeshProfilingOperator

Main operator for executing ProfileMesh profiling tasks.

### Class Definition

```python
class ProfileMeshProfilingOperator(BaseOperator):
    """
    Airflow operator that executes ProfileMesh profiling.
    
    This operator can profile one or more tables and emit results via XCom.
    Similar to Dagster assets, it materializes profiling runs.
    """
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `config_path` | str | Yes | - | Path to ProfileMesh configuration file |
| `table_patterns` | List[Dict] | No | None | Specific tables to profile (if None, profiles all) |
| `emit_xcom` | bool | No | True | Whether to emit results to XCom |
| `task_id` | str | Yes | - | Airflow task ID |

### Table Patterns Format

When specifying `table_patterns`, use this format:

```python
table_patterns = [
    {"schema": "public", "table": "users"},
    {"schema": "analytics", "table": "events", "database": "prod"},
]
```

### Returns

#### XCom Key: `profiling_results`

Dictionary with the following structure:

```python
{
    "run_id": "uuid-string",
    "environment": "production",
    "tables_profiled": 3,
    "profiled_at": "2024-01-15T10:30:00",
    "results": [
        {
            "run_id": "uuid-string",
            "dataset_name": "users",
            "schema_name": "public",
            "profiled_at": "2024-01-15T10:30:00",
            "columns_profiled": 10,
            "row_count": 1000,
            "metadata": {...}
        },
        # ... more results
    ]
}
```

### Usage Examples

#### Example 1: Profile All Tables

```python
from airflow import DAG
from profilemesh.integrations.airflow import ProfileMeshProfilingOperator
from datetime import datetime

with DAG('profile_all', start_date=datetime(2024, 1, 1)) as dag:
    profile_task = ProfileMeshProfilingOperator(
        task_id='profile_all_tables',
        config_path='/path/to/config.yml',
    )
```

#### Example 2: Profile Specific Tables

```python
profile_subset = ProfileMeshProfilingOperator(
    task_id='profile_important_tables',
    config_path='/path/to/config.yml',
    table_patterns=[
        {"schema": "public", "table": "users"},
        {"schema": "public", "table": "orders"},
    ],
)
```

#### Example 3: Process Results Downstream

```python
from airflow.operators.python import PythonOperator

def process_results(**context):
    ti = context['ti']
    results = ti.xcom_pull(
        task_ids='profile_all_tables',
        key='profiling_results',
    )
    
    print(f"Environment: {results['environment']}")
    print(f"Tables profiled: {results['tables_profiled']}")
    
    for result in results['results']:
        print(f"  {result['dataset_name']}: {result['columns_profiled']} columns")
        
        # Check for data quality issues
        if result['row_count'] == 0:
            print(f"    WARNING: {result['dataset_name']} has no rows!")

profile_task = ProfileMeshProfilingOperator(
    task_id='profile_all_tables',
    config_path='/path/to/config.yml',
)

process_task = PythonOperator(
    task_id='process_results',
    python_callable=process_results,
)

profile_task >> process_task
```

### Events Emitted

The operator emits the following events via XCom (key: `profilemesh_events`):

1. **profiling_started**
   ```python
   {
       "event_type": "profiling_started",
       "environment": "production",
       "table_count": 3
   }
   ```

2. **profiling_completed**
   ```python
   {
       "event_type": "profiling_completed",
       "environment": "production",
       "run_id": "uuid-string",
       "tables_profiled": 3,
       "total_columns": 45
   }
   ```

### Error Handling

The operator raises `ValueError` if:
- No profiling results are returned
- Configuration file is invalid
- Database connection fails

Example with error handling:

```python
from airflow.operators.python import PythonOperator

def handle_error(**context):
    ti = context['ti']
    task_instance = context['task_instance']
    print(f"Profiling failed for task: {task_instance.task_id}")
    # Send alert, log to external system, etc.

profile_task = ProfileMeshProfilingOperator(
    task_id='profile_tables',
    config_path='/path/to/config.yml',
    on_failure_callback=handle_error,
    retries=2,
    retry_delay=timedelta(minutes=5),
)
```

---

## ProfileMeshTableOperator

Operator for profiling a single table with fine-grained control.

### Class Definition

```python
class ProfileMeshTableOperator(BaseOperator):
    """
    Operator that profiles a single table.
    
    This is useful for creating per-table tasks in a TaskGroup,
    providing better parallelism and observability.
    """
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `config_path` | str | Yes | - | Path to ProfileMesh configuration file |
| `table` | str | Yes | - | Table name to profile |
| `schema` | str | No | "" | Schema name |
| `database` | str | No | "" | Database name |
| `task_id` | str | Yes | - | Airflow task ID |

### Returns

#### XCom Key: `profiling_result`

Dictionary with the following structure:

```python
{
    "run_id": "uuid-string",
    "dataset_name": "users",
    "schema_name": "public",
    "profiled_at": "2024-01-15T10:30:00",
    "columns_profiled": 10,
    "row_count": 1000,
    "metadata": {...}
}
```

### Usage Examples

#### Example 1: Single Table

```python
from profilemesh.integrations.airflow import ProfileMeshTableOperator

profile_users = ProfileMeshTableOperator(
    task_id='profile_users',
    config_path='/path/to/config.yml',
    table='users',
    schema='public',
)
```

#### Example 2: Multiple Tables in Parallel

```python
from airflow.utils.task_group import TaskGroup

with TaskGroup('profile_tables') as tg:
    profile_users = ProfileMeshTableOperator(
        task_id='users',
        config_path='/path/to/config.yml',
        table='users',
        schema='public',
    )
    
    profile_orders = ProfileMeshTableOperator(
        task_id='orders',
        config_path='/path/to/config.yml',
        table='orders',
        schema='public',
    )
    
    profile_events = ProfileMeshTableOperator(
        task_id='events',
        config_path='/path/to/config.yml',
        table='events',
        schema='analytics',
    )
```

#### Example 3: With Validation

```python
def validate_profile(**context):
    ti = context['ti']
    result = ti.xcom_pull(
        task_ids='profile_users',
        key='profiling_result',
    )
    
    # Validate minimum columns
    assert result['columns_profiled'] >= 5, "Too few columns profiled"
    
    # Validate row count
    assert result['row_count'] > 0, "Table is empty"
    
    print(f"Validation passed for {result['dataset_name']}")

profile_users = ProfileMeshTableOperator(
    task_id='profile_users',
    config_path='/path/to/config.yml',
    table='users',
    schema='public',
)

validate = PythonOperator(
    task_id='validate_users',
    python_callable=validate_profile,
)

profile_users >> validate
```

---

## create_profiling_task_group

Helper function to create a TaskGroup with one task per table.

### Function Signature

```python
def create_profiling_task_group(
    *,
    group_id: str,
    config_path: str,
    dag=None,
    **task_group_kwargs,
) -> TaskGroup
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `group_id` | str | Yes | - | ID for the TaskGroup |
| `config_path` | str | Yes | - | Path to ProfileMesh configuration file |
| `dag` | DAG | No | None | Parent DAG (can be inferred from context) |
| `**task_group_kwargs` | dict | No | {} | Additional TaskGroup parameters |

### Returns

`TaskGroup` containing one `ProfileMeshTableOperator` per table in the configuration.

### Usage Examples

#### Example 1: Basic TaskGroup

```python
from profilemesh.integrations.airflow import create_profiling_task_group

with DAG('my_dag', start_date=datetime(2024, 1, 1)) as dag:
    profiling_tasks = create_profiling_task_group(
        group_id='profile_all_tables',
        config_path='/path/to/config.yml',
    )
```

#### Example 2: With Upstream/Downstream Tasks

```python
from airflow.operators.bash import BashOperator

start = BashOperator(task_id='start', bash_command='echo Starting...')

profiling_tasks = create_profiling_task_group(
    group_id='profile_tables',
    config_path='/path/to/config.yml',
)

end = BashOperator(task_id='end', bash_command='echo Done!')

start >> profiling_tasks >> end
```

#### Example 3: Custom TaskGroup Parameters

```python
profiling_tasks = create_profiling_task_group(
    group_id='profile_tables',
    config_path='/path/to/config.yml',
    tooltip='Profile all tables in parallel',
    prefix_group_id=True,
)
```

#### Example 4: Aggregate Results

```python
def aggregate_all_results(**context):
    dag_run = context['dag_run']
    task_instances = dag_run.get_task_instances()
    
    results = []
    for ti in task_instances:
        if ti.task_id.startswith('profile_tables.'):
            result = ti.xcom_pull(key='profiling_result')
            if result:
                results.append(result)
    
    total_columns = sum(r['columns_profiled'] for r in results)
    total_rows = sum(r.get('row_count', 0) for r in results)
    
    print(f"Total tables: {len(results)}")
    print(f"Total columns: {total_columns}")
    print(f"Total rows: {total_rows}")

profiling_tasks = create_profiling_task_group(
    group_id='profile_tables',
    config_path='/path/to/config.yml',
)

aggregate = PythonOperator(
    task_id='aggregate_results',
    python_callable=aggregate_all_results,
)

profiling_tasks >> aggregate
```

### Task Naming

Tasks within the group are named using sanitized table names:

- `schema.table` → `schema_table`
- `my-table` → `my_table`
- `table.name` → `table_name`

Example task IDs:
- `profile_tables.users`
- `profile_tables.events`
- `profile_tables.order_items`

---

## Best Practices

### 1. Choose the Right Operator

```python
# ✅ Use ProfileMeshProfilingOperator for small datasets
profile_all = ProfileMeshProfilingOperator(
    task_id='profile_all',
    config_path=config_path,
)

# ✅ Use create_profiling_task_group for large datasets (parallel)
profiling_tasks = create_profiling_task_group(
    group_id='profile_tables',
    config_path=config_path,
)

# ✅ Use ProfileMeshTableOperator for custom workflows
profile_users = ProfileMeshTableOperator(
    task_id='profile_users',
    table='users',
    config_path=config_path,
)
```

### 2. Handle XCom Data

```python
# Always pull XCom data safely
result = ti.xcom_pull(task_ids='profile_task', key='profiling_results')
if result is None:
    print("No profiling results available")
    return

# Process results...
```

### 3. Set Appropriate Retries

```python
profile_task = ProfileMeshProfilingOperator(
    task_id='profile_tables',
    config_path=config_path,
    retries=2,
    retry_delay=timedelta(minutes=5),
    retry_exponential_backoff=True,
)
```

### 4. Use Task Dependencies Wisely

```python
# ✅ Good - Clear dependencies
extract >> transform >> profile >> validate >> alert

# ❌ Bad - Too many dependencies
task1 >> task2 >> task3 >> task4 >> task5 >> task6
```
