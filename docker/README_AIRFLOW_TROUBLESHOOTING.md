# Airflow Troubleshooting Guide

## Viewing Logs

### Option 1: Airflow UI (Recommended)
1. Go to http://localhost:8080
2. Click on your DAG name
3. Click on the task (e.g., "profile_test")
4. Click the task instance square
5. Click "Log" button to view task logs

### Option 2: Docker Logs
```bash
# View scheduler logs
docker-compose logs -f airflow_scheduler

# View webserver logs
docker-compose logs -f airflow_webserver

# View specific task logs (replace DAG_ID, TASK_ID, RUN_ID)
docker exec baselinr_airflow_webserver airflow tasks logs DAG_ID TASK_ID RUN_ID
```

### Option 3: Direct Log Files
Task logs are stored in the `airflow_logs` volume. You can access them via:
```bash
docker exec baselinr_airflow_webserver ls -la /opt/airflow/logs/
```

## Common Issues

### 1. Tasks Not Running / Stuck in "Queued"

**Symptoms:**
- Tasks show as "queued" but never start
- Scheduler logs show "DAG record was locked"

**Solutions:**
- Check if the default pool exists: `docker exec baselinr_airflow_webserver airflow pools list`
- Create default pool if missing: `docker exec baselinr_airflow_webserver airflow pools set default_pool 128 "Default pool"`
- Restart scheduler: `docker-compose restart airflow_scheduler`
- Check task logs for errors

### 2. Config File Not Found

**Symptoms:**
- Task fails with "FileNotFoundError" or "Config file not found"

**Solutions:**
- Verify config path in DAG: `/app/examples/config.yml`
- Check if file exists: `docker exec baselinr_airflow_webserver ls -la /app/examples/config.yml`
- Ensure the volume mount is correct in docker-compose.yml

### 3. Import Errors

**Symptoms:**
- DAG shows "Broken DAG" with import errors

**Solutions:**
- Check DAG syntax: `docker exec baselinr_airflow_webserver python /opt/airflow/dags/airflow_test_dag.py`
- Verify Baselinr is installed: `docker exec baselinr_airflow_webserver pip list | grep baselinr`
- Check Python path and imports

### 4. Database Connection Issues

**Symptoms:**
- Tasks fail with database connection errors

**Solutions:**
- Verify PostgreSQL is running: `docker-compose ps postgres`
- Check connection settings in config.yml match Docker environment
- Test connection: `docker exec baselinr_airflow_webserver python -c "from baselinr import BaselinrClient; c = BaselinrClient('/app/examples/config.yml'); print('OK')"`

### 5. Tasks Running But No Output

**Symptoms:**
- Task shows as "success" but no results

**Solutions:**
- Check XCom for return values (in Airflow UI, task details → XCom)
- Verify Baselinr client is actually executing (check logs)
- Check if profiling results are being saved to database

## Debugging Commands

```bash
# List all DAGs
docker exec baselinr_airflow_webserver airflow dags list

# List DAG runs
docker exec baselinr_airflow_webserver airflow dags list-runs -d DAG_ID

# Check task state
docker exec baselinr_airflow_webserver airflow tasks state DAG_ID TASK_ID RUN_ID

# Test DAG import
docker exec baselinr_airflow_webserver python -m py_compile /opt/airflow/dags/airflow_test_dag.py

# Check Baselinr installation
docker exec baselinr_airflow_webserver python -c "from baselinr.integrations.airflow import BaselinrProfileOperator; print('OK')"

# View task logs
docker exec baselinr_airflow_webserver airflow tasks logs DAG_ID TASK_ID RUN_ID

# Clear DAG run (if stuck)
docker exec baselinr_airflow_webserver airflow dags delete-orphans
```

## Checking Task Execution

1. **In Airflow UI:**
   - Go to DAG → Graph View
   - Click on task instance
   - View logs, XCom, and task details

2. **Via CLI:**
   ```bash
   # Get the latest run ID
   docker exec baselinr_airflow_webserver airflow dags list-runs -d baselinr_test_combined --no-backfill | head -5
   
   # View logs for that run
   docker exec baselinr_airflow_webserver airflow tasks logs baselinr_test_combined profile <RUN_ID>
   ```

## Restarting Services

If tasks are stuck or not running:
```bash
# Restart scheduler
docker-compose restart airflow_scheduler

# Restart webserver
docker-compose restart airflow_webserver

# Full restart
docker-compose restart
```

