# Airflow Integration Examples

This document provides practical examples of using ProfileMesh with Airflow in various scenarios.

## Table of Contents

1. [Basic Workflows](#basic-workflows)
2. [Advanced Patterns](#advanced-patterns)
3. [Production Scenarios](#production-scenarios)
4. [Integration with Other Tools](#integration-with-other-tools)

---

## Basic Workflows

### Example 1: Daily Profiling Schedule

Simple daily profiling of all tables:

```python
from datetime import datetime, timedelta
from airflow import DAG
from profilemesh.integrations.airflow import ProfileMeshProfilingOperator

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email': ['data-team@company.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'daily_profiling',
    default_args=default_args,
    description='Daily data profiling at midnight',
    schedule_interval='0 0 * * *',  # Daily at midnight
    catchup=False,
    tags=['profilemesh', 'daily', 'production'],
) as dag:
    
    profile_all = ProfileMeshProfilingOperator(
        task_id='profile_all_tables',
        config_path='/configs/production.yml',
    )
```

### Example 2: Hourly Profiling for Critical Tables

Profile important tables more frequently:

```python
with DAG(
    'hourly_critical_profiling',
    default_args=default_args,
    schedule_interval='@hourly',
    catchup=False,
    tags=['profilemesh', 'critical', 'hourly'],
) as dag:
    
    profile_critical = ProfileMeshProfilingOperator(
        task_id='profile_critical_tables',
        config_path='/configs/production.yml',
        table_patterns=[
            {'schema': 'public', 'table': 'users'},
            {'schema': 'public', 'table': 'transactions'},
            {'schema': 'analytics', 'table': 'revenue'},
        ],
    )
```

### Example 3: Parallel Table Profiling

Profile multiple tables in parallel for better performance:

```python
from profilemesh.integrations.airflow import create_profiling_task_group
from airflow.operators.python import PythonOperator

with DAG('parallel_profiling', ...) as dag:
    
    def start_profiling():
        print("Starting profiling run...")
    
    def finish_profiling(**context):
        print("Profiling complete!")
        # Aggregate results, send notifications, etc.
    
    start = PythonOperator(
        task_id='start',
        python_callable=start_profiling,
    )
    
    profiling_tasks = create_profiling_task_group(
        group_id='profile_all_tables',
        config_path='/configs/production.yml',
    )
    
    finish = PythonOperator(
        task_id='finish',
        python_callable=finish_profiling,
    )
    
    start >> profiling_tasks >> finish
```

---

## Advanced Patterns

### Example 4: Conditional Profiling Based on Data Changes

Only run profiling if upstream data has changed:

```python
from airflow.operators.python import BranchPythonOperator
from airflow.sensors.external_task import ExternalTaskSensor

def check_data_changes(**context):
    """Check if source data has changed."""
    # Query your data warehouse for recent changes
    # This is a simplified example
    from datetime import datetime, timedelta
    
    # Check last modified time from metadata table
    # query = "SELECT MAX(modified_at) FROM metadata.tables"
    # last_modified = execute_query(query)
    
    # For demo, check if it's during business hours
    now = datetime.now()
    if 9 <= now.hour <= 17:
        return 'profile_tables'
    else:
        return 'skip_profiling'

with DAG('conditional_profiling', ...) as dag:
    
    # Wait for upstream ETL to complete
    wait_for_etl = ExternalTaskSensor(
        task_id='wait_for_etl',
        external_dag_id='etl_pipeline',
        external_task_id='load_complete',
        timeout=3600,
    )
    
    check_changes = BranchPythonOperator(
        task_id='check_data_changes',
        python_callable=check_data_changes,
    )
    
    profile = ProfileMeshProfilingOperator(
        task_id='profile_tables',
        config_path='/configs/production.yml',
    )
    
    skip = DummyOperator(task_id='skip_profiling')
    
    wait_for_etl >> check_changes
    check_changes >> [profile, skip]
```

### Example 5: Multi-Environment Profiling

Profile data across multiple environments:

```python
from airflow.operators.python import PythonOperator

def compare_environments(**context):
    """Compare profiling results across environments."""
    ti = context['ti']
    
    prod_results = ti.xcom_pull(
        task_ids='profile_production',
        key='profiling_results',
    )
    staging_results = ti.xcom_pull(
        task_ids='profile_staging',
        key='profiling_results',
    )
    
    # Compare table schemas, row counts, etc.
    print("Environment Comparison:")
    print(f"  Production tables: {prod_results['tables_profiled']}")
    print(f"  Staging tables: {staging_results['tables_profiled']}")
    
    # Alert on significant differences
    # ...

with DAG('multi_env_profiling', ...) as dag:
    
    profile_prod = ProfileMeshProfilingOperator(
        task_id='profile_production',
        config_path='/configs/production.yml',
    )
    
    profile_staging = ProfileMeshProfilingOperator(
        task_id='profile_staging',
        config_path='/configs/staging.yml',
    )
    
    compare = PythonOperator(
        task_id='compare_environments',
        python_callable=compare_environments,
    )
    
    [profile_prod, profile_staging] >> compare
```

### Example 6: Incremental Profiling with State Management

Track and profile only changed partitions:

```python
from airflow.models import Variable
import json

def determine_tables_to_profile(**context):
    """Determine which tables need profiling based on state."""
    # Load last profiling state
    last_state = Variable.get('profiling_state', default_var='{}')
    state = json.loads(last_state)
    
    # Query metadata to find changed tables
    # This is a simplified example
    changed_tables = [
        {'schema': 'public', 'table': 'users'},
        # ... tables that changed since last run
    ]
    
    # Store tables to profile in XCom
    context['ti'].xcom_push(key='tables_to_profile', value=changed_tables)
    
    return 'profile_changed_tables' if changed_tables else 'skip_profiling'

def update_profiling_state(**context):
    """Update state after successful profiling."""
    from datetime import datetime
    
    state = {
        'last_run': datetime.now().isoformat(),
        'tables_profiled': context['ti'].xcom_pull(
            task_ids='profile_changed_tables',
            key='profiling_results',
        )['tables_profiled'],
    }
    
    Variable.set('profiling_state', json.dumps(state))

with DAG('incremental_profiling', ...) as dag:
    
    determine = BranchPythonOperator(
        task_id='determine_tables',
        python_callable=determine_tables_to_profile,
    )
    
    profile = ProfileMeshProfilingOperator(
        task_id='profile_changed_tables',
        config_path='/configs/production.yml',
        # table_patterns will be determined dynamically
    )
    
    update_state = PythonOperator(
        task_id='update_state',
        python_callable=update_profiling_state,
    )
    
    skip = DummyOperator(task_id='skip_profiling')
    
    determine >> [profile, skip]
    profile >> update_state
```

---

## Production Scenarios

### Example 7: Complete Data Pipeline with Profiling

Integrate profiling into a complete data pipeline:

```python
from airflow.operators.bash import BashOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator

with DAG('data_pipeline_with_profiling', ...) as dag:
    
    # 1. Extract data
    extract = BashOperator(
        task_id='extract_data',
        bash_command='python /scripts/extract.py',
    )
    
    # 2. Load to staging
    load_staging = BashOperator(
        task_id='load_staging',
        bash_command='python /scripts/load_staging.py',
    )
    
    # 3. Profile staging data
    profile_staging = ProfileMeshProfilingOperator(
        task_id='profile_staging',
        config_path='/configs/staging.yml',
    )
    
    # 4. Validate staging data
    def validate_staging(**context):
        ti = context['ti']
        results = ti.xcom_pull(
            task_ids='profile_staging',
            key='profiling_results',
        )
        
        # Validate row counts, null percentages, etc.
        for result in results['results']:
            if result.get('row_count', 0) == 0:
                raise ValueError(f"Table {result['dataset_name']} is empty!")
        
        print("Staging validation passed")
    
    validate = PythonOperator(
        task_id='validate_staging',
        python_callable=validate_staging,
    )
    
    # 5. Transform and load to production
    transform = PostgresOperator(
        task_id='transform_data',
        postgres_conn_id='postgres_prod',
        sql='CALL transform_staging_to_prod()',
    )
    
    # 6. Profile production data
    profile_prod = ProfileMeshProfilingOperator(
        task_id='profile_production',
        config_path='/configs/production.yml',
    )
    
    # 7. Generate data quality report
    def generate_report(**context):
        ti = context['ti']
        prod_results = ti.xcom_pull(
            task_ids='profile_production',
            key='profiling_results',
        )
        
        # Generate HTML report, send email, etc.
        print(f"Data Quality Report Generated")
        print(f"  Tables: {prod_results['tables_profiled']}")
        print(f"  Run ID: {prod_results['run_id']}")
    
    report = PythonOperator(
        task_id='generate_report',
        python_callable=generate_report,
    )
    
    # Define pipeline
    extract >> load_staging >> profile_staging >> validate
    validate >> transform >> profile_prod >> report
```

### Example 8: Drift Detection and Alerting

Monitor for data drift and send alerts:

```python
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator

def detect_drift(**context):
    """Detect drift from profiling results."""
    ti = context['ti']
    results = ti.xcom_pull(
        task_ids='profile_tables',
        key='profiling_results',
    )
    
    drift_detected = []
    
    for result in results['results']:
        table = result['dataset_name']
        
        # Check for schema changes (simplified)
        # In reality, query historical profiling results
        expected_columns = 10
        actual_columns = result['columns_profiled']
        
        if actual_columns != expected_columns:
            drift_detected.append({
                'table': table,
                'issue': 'Column count mismatch',
                'expected': expected_columns,
                'actual': actual_columns,
            })
    
    if drift_detected:
        context['ti'].xcom_push(key='drift_issues', value=drift_detected)
        return 'alert_drift'
    else:
        return 'no_drift'

def format_alert(**context):
    ti = context['ti']
    issues = ti.xcom_pull(task_ids='detect_drift', key='drift_issues')
    
    message = "🚨 *Data Drift Detected*\n\n"
    for issue in issues:
        message += f"• *{issue['table']}*: {issue['issue']}\n"
        message += f"  Expected: {issue['expected']}, Actual: {issue['actual']}\n"
    
    return message

with DAG('drift_detection', ...) as dag:
    
    profile = ProfileMeshProfilingOperator(
        task_id='profile_tables',
        config_path='/configs/production.yml',
    )
    
    detect = BranchPythonOperator(
        task_id='detect_drift',
        python_callable=detect_drift,
    )
    
    alert = SlackWebhookOperator(
        task_id='alert_drift',
        slack_webhook_conn_id='slack_alerts',
        message=format_alert,
    )
    
    no_drift = DummyOperator(task_id='no_drift')
    
    profile >> detect >> [alert, no_drift]
```

### Example 9: SLA Monitoring

Monitor profiling SLAs and alert on violations:

```python
from datetime import timedelta

def check_sla(**context):
    """Check if profiling meets SLA requirements."""
    ti = context['ti']
    results = ti.xcom_pull(
        task_ids='profile_tables',
        key='profiling_results',
    )
    
    # Check execution time
    execution_time = ti.end_date - ti.start_date
    sla_threshold = timedelta(minutes=30)
    
    if execution_time > sla_threshold:
        print(f"⚠️ SLA violation: Profiling took {execution_time}")
        # Send alert
    else:
        print(f"✅ SLA met: Profiling took {execution_time}")
    
    # Check data freshness
    # Check completeness
    # etc.

with DAG('profiling_with_sla', ..., sla=timedelta(minutes=30)) as dag:
    
    profile = ProfileMeshProfilingOperator(
        task_id='profile_tables',
        config_path='/configs/production.yml',
        execution_timeout=timedelta(minutes=25),
    )
    
    check = PythonOperator(
        task_id='check_sla',
        python_callable=check_sla,
    )
    
    profile >> check
```

---

## Integration with Other Tools

### Example 10: Integration with dbt

Profile tables after dbt transformations:

```python
from airflow.providers.dbt.cloud.operators.dbt import DbtCloudRunJobOperator

with DAG('dbt_with_profiling', ...) as dag:
    
    # Run dbt models
    dbt_run = DbtCloudRunJobOperator(
        task_id='dbt_run',
        job_id=12345,
        check_interval=10,
        timeout=300,
    )
    
    # Profile transformed tables
    profile = ProfileMeshProfilingOperator(
        task_id='profile_transformed',
        config_path='/configs/dbt_models.yml',
    )
    
    # Validate transformations
    def validate_transforms(**context):
        ti = context['ti']
        results = ti.xcom_pull(
            task_ids='profile_transformed',
            key='profiling_results',
        )
        
        # Check that all expected models are present
        # Validate row counts match expectations
        # etc.
    
    validate = PythonOperator(
        task_id='validate',
        python_callable=validate_transforms,
    )
    
    dbt_run >> profile >> validate
```

### Example 11: Integration with Great Expectations

Combine ProfileMesh profiling with Great Expectations validation:

```python
from airflow.providers.great_expectations.operators.great_expectations import (
    GreatExpectationsOperator,
)

with DAG('profiling_with_ge', ...) as dag:
    
    # Profile data
    profile = ProfileMeshProfilingOperator(
        task_id='profile_tables',
        config_path='/configs/production.yml',
    )
    
    # Validate with Great Expectations
    validate_ge = GreatExpectationsOperator(
        task_id='validate_with_ge',
        data_context_root_dir='/configs/great_expectations',
        checkpoint_name='production_checkpoint',
    )
    
    # Compare results
    def compare_results(**context):
        """Compare ProfileMesh and GE results."""
        ti = context['ti']
        
        pm_results = ti.xcom_pull(
            task_ids='profile_tables',
            key='profiling_results',
        )
        
        # GE results available via XCom
        # Compare and reconcile any differences
        
        print("Profiling and validation complete")
    
    compare = PythonOperator(
        task_id='compare_results',
        python_callable=compare_results,
    )
    
    profile >> validate_ge >> compare
```

### Example 12: Integration with Data Catalogs

Push profiling metadata to a data catalog:

```python
import requests

def update_catalog(**context):
    """Update data catalog with profiling results."""
    ti = context['ti']
    results = ti.xcom_pull(
        task_ids='profile_tables',
        key='profiling_results',
    )
    
    catalog_api = 'https://datacatalog.company.com/api/v1'
    
    for result in results['results']:
        # Prepare metadata
        metadata = {
            'table': result['dataset_name'],
            'row_count': result['row_count'],
            'column_count': result['columns_profiled'],
            'last_profiled': result['profiled_at'],
            'profile_run_id': result['run_id'],
        }
        
        # Update catalog
        response = requests.post(
            f'{catalog_api}/tables/{result["dataset_name"]}/metadata',
            json=metadata,
            headers={'Authorization': 'Bearer TOKEN'},
        )
        
        if response.status_code == 200:
            print(f"Updated catalog for {result['dataset_name']}")
        else:
            print(f"Failed to update catalog: {response.text}")

with DAG('profiling_to_catalog', ...) as dag:
    
    profile = ProfileMeshProfilingOperator(
        task_id='profile_tables',
        config_path='/configs/production.yml',
    )
    
    update = PythonOperator(
        task_id='update_catalog',
        python_callable=update_catalog,
    )
    
    profile >> update
```

---

## Best Practices Summary

1. **Use TaskGroups** for parallel profiling of multiple tables
2. **Set appropriate retries** for resilience
3. **Monitor execution times** and set SLAs
4. **Validate results** before downstream processing
5. **Integrate with monitoring** (Slack, PagerDuty, DataDog)
6. **Use sensors** for reactive profiling
7. **Leverage XCom** for passing results between tasks
8. **Handle failures** gracefully with callbacks
9. **Tag DAGs** appropriately for organization
10. **Document dependencies** and expectations

For more examples, see the `examples/airflow_dags/` directory in the repository.
