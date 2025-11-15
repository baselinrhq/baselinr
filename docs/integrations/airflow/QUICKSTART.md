# Airflow Integration - Quick Start

Get up and running with ProfileMesh and Airflow in minutes.

## Installation

### Option 1: Install with pip

```bash
pip install profilemesh[airflow]
```

### Option 2: Install from source

```bash
git clone https://github.com/yourusername/profilemesh.git
cd profilemesh
pip install -e ".[airflow]"
```

## 5-Minute Quick Start

### 1. Create a ProfileMesh Configuration

Create `config.yml`:

```yaml
environment: development

source:
  type: postgres
  host: localhost
  port: 5432
  database: mydb
  user: postgres
  password: postgres

storage:
  connection:
    type: postgres
    host: localhost
    port: 5432
    database: profilemesh_results
    user: postgres
    password: postgres
  results_table: profiling_results
  runs_table: profiling_runs

profiling:
  tables:
    - schema: public
      table: users
    - schema: public
      table: orders
  metrics:
    - count
    - null_count
    - distinct_count
    - min
    - max
    - mean
```

### 2. Create Your First DAG

Create `dags/profilemesh_quickstart.py`:

```python
from datetime import datetime
from airflow import DAG
from profilemesh.integrations.airflow import ProfileMeshProfilingOperator

with DAG(
    'profilemesh_quickstart',
    start_date=datetime(2024, 1, 1),
    schedule_interval='@daily',
    catchup=False,
) as dag:
    
    profile_tables = ProfileMeshProfilingOperator(
        task_id='profile_all_tables',
        config_path='/path/to/config.yml',
    )
```

### 3. Run with Airflow

```bash
# Initialize Airflow database
airflow db init

# Create admin user
airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com

# Start webserver
airflow webserver --port 8080 &

# Start scheduler
airflow scheduler &

# Open browser to http://localhost:8080
# Login with admin/admin
# Trigger your DAG!
```

## Docker Quick Start

The fastest way to get started is using Docker Compose:

### 1. Start All Services

```bash
cd profilemesh
docker compose -f docker/docker-compose.yml up -d
```

This starts:
- PostgreSQL (source data)
- Airflow PostgreSQL (metadata)
- Airflow Webserver (UI)
- Airflow Scheduler

### 2. Access Airflow UI

Open http://localhost:8080

- Username: `admin`
- Password: `admin`

### 3. View Example DAGs

Three example DAGs are pre-loaded:
- `profilemesh_profile_all` - Profile all tables
- `profilemesh_profile_parallel` - Parallel profiling
- `profilemesh_plan_monitor` - Plan change monitoring

### 4. Trigger a DAG

1. Navigate to the DAGs page
2. Click on `profilemesh_profile_all`
3. Click the "Play" button to trigger
4. Watch the execution in real-time

### 5. View Logs

```bash
# Webserver logs
docker compose -f docker/docker-compose.yml logs -f airflow_webserver

# Scheduler logs
docker compose -f docker/docker-compose.yml logs -f airflow_scheduler
```

### 6. Stop Services

```bash
docker compose -f docker/docker-compose.yml down -v
```

## Next Steps

### Customize Your Configuration

Edit `examples/config.yml` to point to your own database:

```yaml
source:
  type: postgres
  host: your-database-host
  port: 5432
  database: your_database
  user: your_user
  password: your_password

profiling:
  tables:
    - schema: your_schema
      table: your_table
```

### Create Custom DAGs

See comprehensive examples in:
- [examples/airflow_dags/profilemesh_dag.py](../../../examples/airflow_dags/profilemesh_dag.py)
- [examples/airflow_dags/profilemesh_sensor_dag.py](../../../examples/airflow_dags/profilemesh_sensor_dag.py)

### Read the Documentation

- [Operators Reference](./OPERATORS.md)
- [Sensors Reference](./SENSORS.md)
- [Examples](./EXAMPLES.md)
- [Full README](./README.md)

## Troubleshooting

### ImportError: No module named 'airflow'

```bash
pip install apache-airflow==2.8.1
```

### ImportError: No module named 'profilemesh'

```bash
pip install profilemesh[airflow]
```

### DAGs not appearing in Airflow

1. Check DAG folder:
   ```bash
   echo $AIRFLOW_HOME/dags
   ls -la $AIRFLOW_HOME/dags
   ```

2. Check for import errors:
   ```bash
   airflow dags list
   ```

3. Verify ProfileMesh is installed:
   ```bash
   python -c "import profilemesh; print('OK')"
   ```

### Database connection errors

Check your configuration:

```python
from profilemesh.config.loader import ConfigLoader
config = ConfigLoader.load_from_file('/path/to/config.yml')
print(config.source)
```

## Support

- [Full Documentation](./README.md)
- [Examples](./EXAMPLES.md)
- [GitHub Issues](https://github.com/yourusername/profilemesh/issues)

Happy profiling! 🚀
