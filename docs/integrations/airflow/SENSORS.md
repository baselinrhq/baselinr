# Airflow Sensors Reference

This document provides detailed reference for ProfileMesh Airflow sensors.

## ProfileMeshPlanSensor

Sensor that monitors ProfileMesh plan changes and triggers when modifications are detected.

### Class Definition

```python
class ProfileMeshPlanSensor(BaseSensorOperator):
    """
    Sensor that monitors ProfileMesh plan changes.
    
    This sensor checks the profiling plan configuration and triggers
    when changes are detected (new tables, modified sampling, etc.).
    Similar to the Dagster plan sensor.
    """
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `config_path` | str | Yes | - | Path to ProfileMesh configuration file |
| `cursor_variable` | str | No | `profilemesh_plan_cursor` | Airflow Variable name for cursor storage |
| `poke_interval` | int | No | 60 | Seconds between checks |
| `timeout` | int | No | 3600 | Sensor timeout in seconds (1 hour) |
| `mode` | str | No | `poke` | Sensor mode ('poke' or 'reschedule') |

### Sensor Modes

#### Poke Mode
- Continuously checks at `poke_interval`
- Holds a worker slot while waiting
- Best for short intervals (< 5 minutes)

```python
sensor = ProfileMeshPlanSensor(
    task_id='detect_changes',
    config_path='/path/to/config.yml',
    mode='poke',
    poke_interval=300,  # 5 minutes
)
```

#### Reschedule Mode
- Releases worker slot between checks
- More resource-efficient for long intervals
- Best for longer intervals (> 10 minutes)

```python
sensor = ProfileMeshPlanSensor(
    task_id='detect_changes',
    config_path='/path/to/config.yml',
    mode='reschedule',
    poke_interval=3600,  # 1 hour
)
```

### Returns

#### XCom Key: `plan_change_metadata`

Dictionary with the following structure:

```python
{
    "environment": "production",
    "changed_tables": ["public.users", "analytics.events"],
    "metrics_requested": 24,
    "drift_strategy": "absolute_threshold",
    "plan_signature": "a1b2c3d4..."
}
```

### Change Detection

The sensor detects the following types of changes:

1. **New tables added** to the configuration
2. **Tables removed** from the configuration
3. **Metric changes** (different metrics requested)
4. **Sampling configuration changes** (different sample size, strategy)
5. **Partition configuration changes** (different partitions)

### Cursor Storage

The sensor stores its cursor in an Airflow Variable. This allows:
- Persistent state across DAG runs
- Manual cursor inspection and modification
- Shared state across multiple sensors (if needed)

#### View Cursor

```bash
# Via Airflow CLI
airflow variables get profilemesh_plan_cursor

# Via Python
from airflow.models import Variable
cursor = Variable.get('profilemesh_plan_cursor')
print(cursor)
```

#### Reset Cursor

```bash
# Via Airflow CLI
airflow variables delete profilemesh_plan_cursor

# Via Python
from airflow.models import Variable
Variable.delete('profilemesh_plan_cursor')
```

### Usage Examples

#### Example 1: Basic Plan Monitoring

```python
from airflow import DAG
from profilemesh.integrations.airflow import (
    ProfileMeshPlanSensor,
    ProfileMeshProfilingOperator,
)
from datetime import datetime

with DAG('monitor_plan', start_date=datetime(2024, 1, 1), schedule_interval='@hourly') as dag:
    
    sensor = ProfileMeshPlanSensor(
        task_id='detect_plan_changes',
        config_path='/path/to/config.yml',
        poke_interval=300,  # Check every 5 minutes
    )
    
    profile = ProfileMeshProfilingOperator(
        task_id='profile_changed',
        config_path='/path/to/config.yml',
    )
    
    sensor >> profile
```

#### Example 2: Process Changes Before Profiling

```python
from airflow.operators.python import PythonOperator

def analyze_changes(**context):
    ti = context['ti']
    metadata = ti.xcom_pull(
        task_ids='detect_plan_changes',
        key='plan_change_metadata',
    )
    
    if not metadata:
        print("No changes detected")
        return
    
    print(f"Plan Changes Detected:")
    print(f"  Environment: {metadata['environment']}")
    print(f"  Changed Tables: {metadata['changed_tables']}")
    print(f"  Metrics: {metadata['metrics_requested']}")
    print(f"  Strategy: {metadata['drift_strategy']}")
    
    # Notify team
    # Update external systems
    # Log to monitoring

sensor = ProfileMeshPlanSensor(
    task_id='detect_plan_changes',
    config_path='/path/to/config.yml',
)

analyze = PythonOperator(
    task_id='analyze_changes',
    python_callable=analyze_changes,
)

profile = ProfileMeshProfilingOperator(
    task_id='profile_changed',
    config_path='/path/to/config.yml',
)

sensor >> analyze >> profile
```

#### Example 3: Conditional Profiling

```python
from airflow.operators.python import BranchPythonOperator
from airflow.operators.dummy import DummyOperator

def decide_action(**context):
    ti = context['ti']
    metadata = ti.xcom_pull(
        task_ids='detect_plan_changes',
        key='plan_change_metadata',
    )
    
    if not metadata:
        return 'skip_profiling'
    
    # Only profile if significant changes
    if metadata['metrics_requested'] > 10:
        return 'profile_full'
    else:
        return 'profile_sample'

sensor = ProfileMeshPlanSensor(
    task_id='detect_plan_changes',
    config_path='/path/to/config.yml',
)

branch = BranchPythonOperator(
    task_id='decide_action',
    python_callable=decide_action,
)

profile_full = ProfileMeshProfilingOperator(
    task_id='profile_full',
    config_path='/path/to/config.yml',
)

profile_sample = ProfileMeshProfilingOperator(
    task_id='profile_sample',
    config_path='/path/to/config_sample.yml',
)

skip = DummyOperator(task_id='skip_profiling')

sensor >> branch
branch >> profile_full
branch >> profile_sample
branch >> skip
```

#### Example 4: Multiple Config Monitoring

```python
# Monitor multiple environments
sensor_prod = ProfileMeshPlanSensor(
    task_id='detect_changes_prod',
    config_path='/path/to/prod_config.yml',
    cursor_variable='profilemesh_cursor_prod',
)

sensor_staging = ProfileMeshPlanSensor(
    task_id='detect_changes_staging',
    config_path='/path/to/staging_config.yml',
    cursor_variable='profilemesh_cursor_staging',
)

profile_prod = ProfileMeshProfilingOperator(
    task_id='profile_prod',
    config_path='/path/to/prod_config.yml',
)

profile_staging = ProfileMeshProfilingOperator(
    task_id='profile_staging',
    config_path='/path/to/staging_config.yml',
)

sensor_prod >> profile_prod
sensor_staging >> profile_staging
```

#### Example 5: Notification on Changes

```python
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator

def format_slack_message(**context):
    ti = context['ti']
    metadata = ti.xcom_pull(
        task_ids='detect_plan_changes',
        key='plan_change_metadata',
    )
    
    if not metadata:
        return "No plan changes detected"
    
    tables = ', '.join(metadata['changed_tables'])
    message = f"""
    🔔 *ProfileMesh Plan Changes Detected*
    
    • Environment: `{metadata['environment']}`
    • Changed Tables: `{tables}`
    • Metrics Requested: `{metadata['metrics_requested']}`
    • Drift Strategy: `{metadata['drift_strategy']}`
    """
    
    return message

sensor = ProfileMeshPlanSensor(
    task_id='detect_plan_changes',
    config_path='/path/to/config.yml',
)

notify = SlackWebhookOperator(
    task_id='notify_slack',
    slack_webhook_conn_id='slack_webhook',
    message=format_slack_message,
)

profile = ProfileMeshProfilingOperator(
    task_id='profile_changed',
    config_path='/path/to/config.yml',
)

sensor >> notify >> profile
```

### Best Practices

#### 1. Choose Appropriate Poke Intervals

```python
# ✅ Good - Balanced intervals
sensor = ProfileMeshPlanSensor(
    task_id='detect_changes',
    config_path='/path/to/config.yml',
    poke_interval=300,  # 5 minutes
    mode='poke',
)

# ✅ Good - Long intervals with reschedule
sensor = ProfileMeshPlanSensor(
    task_id='detect_changes',
    config_path='/path/to/config.yml',
    poke_interval=3600,  # 1 hour
    mode='reschedule',
)

# ❌ Bad - Too frequent, wastes resources
sensor = ProfileMeshPlanSensor(
    task_id='detect_changes',
    config_path='/path/to/config.yml',
    poke_interval=10,  # 10 seconds
)
```

#### 2. Set Reasonable Timeouts

```python
# ✅ Good - Timeout based on expected change frequency
sensor = ProfileMeshPlanSensor(
    task_id='detect_changes',
    config_path='/path/to/config.yml',
    timeout=7200,  # 2 hours
)

# ❌ Bad - Very long timeout
sensor = ProfileMeshPlanSensor(
    task_id='detect_changes',
    config_path='/path/to/config.yml',
    timeout=86400,  # 24 hours
)
```

#### 3. Use Unique Cursor Variables

```python
# ✅ Good - Unique cursor per config
sensor_prod = ProfileMeshPlanSensor(
    task_id='detect_changes_prod',
    config_path='/configs/prod.yml',
    cursor_variable='profilemesh_cursor_prod',
)

sensor_dev = ProfileMeshPlanSensor(
    task_id='detect_changes_dev',
    config_path='/configs/dev.yml',
    cursor_variable='profilemesh_cursor_dev',
)
```

#### 4. Handle Sensor Timeouts

```python
def handle_timeout(**context):
    print("Sensor timed out - no plan changes in expected timeframe")
    # Send alert or take alternative action

sensor = ProfileMeshPlanSensor(
    task_id='detect_changes',
    config_path='/path/to/config.yml',
    timeout=3600,
    on_failure_callback=handle_timeout,
)
```

### Comparison with Dagster Sensor

| Feature | Dagster Sensor | Airflow Sensor |
|---------|---------------|----------------|
| Execution | Event-based | Polling-based |
| State Storage | Cursor (in-memory) | Airflow Variable |
| Resource Usage | Efficient | Depends on mode |
| Flexibility | High | High |
| Configuration | Python | Python |

### Troubleshooting

#### Sensor Not Detecting Changes

1. **Check config file is accessible:**
   ```bash
   docker exec airflow_webserver cat /path/to/config.yml
   ```

2. **Verify cursor is being updated:**
   ```python
   from airflow.models import Variable
   cursor = Variable.get('profilemesh_plan_cursor')
   import json
   print(json.loads(cursor))
   ```

3. **Check sensor logs:**
   ```bash
   docker logs airflow_scheduler | grep "ProfileMesh plan"
   ```

#### Sensor Always Triggering

1. **Reset cursor:**
   ```python
   from airflow.models import Variable
   Variable.delete('profilemesh_plan_cursor')
   ```

2. **Check for config file changes:**
   ```bash
   # Ensure config file isn't being modified unintentionally
   watch -n 5 md5sum /path/to/config.yml
   ```

#### Worker Slot Exhaustion

If using poke mode with many sensors:

```python
# Switch to reschedule mode
sensor = ProfileMeshPlanSensor(
    task_id='detect_changes',
    config_path='/path/to/config.yml',
    mode='reschedule',  # Frees worker slot
    poke_interval=600,
)
```

### Advanced Usage

#### Custom Change Detection Logic

While the sensor automatically detects plan changes, you can add custom logic:

```python
def custom_change_handler(**context):
    ti = context['ti']
    metadata = ti.xcom_pull(
        task_ids='detect_plan_changes',
        key='plan_change_metadata',
    )
    
    if not metadata:
        return 'skip'
    
    # Custom logic: only profile during business hours
    from datetime import datetime
    hour = datetime.now().hour
    if not (9 <= hour <= 17):
        print("Outside business hours, skipping profiling")
        return 'skip'
    
    # Custom logic: check if changes are significant
    if metadata['metrics_requested'] < 5:
        print("Too few metrics, skipping profiling")
        return 'skip'
    
    return 'profile'

sensor = ProfileMeshPlanSensor(...)
branch = BranchPythonOperator(
    task_id='check_conditions',
    python_callable=custom_change_handler,
)
# ... rest of DAG
```

#### Integrate with External Monitoring

```python
def report_to_datadog(**context):
    ti = context['ti']
    metadata = ti.xcom_pull(...)
    
    if metadata:
        from datadog import statsd
        statsd.increment('profilemesh.plan.changes')
        statsd.gauge('profilemesh.plan.tables', len(metadata['changed_tables']))
        statsd.gauge('profilemesh.plan.metrics', metadata['metrics_requested'])

sensor = ProfileMeshPlanSensor(...)
report = PythonOperator(
    task_id='report_metrics',
    python_callable=report_to_datadog,
)
# ... rest of DAG
```
