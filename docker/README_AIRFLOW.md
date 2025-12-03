# Airflow Integration Testing

This directory contains Docker configuration for testing the Baselinr Airflow integration locally.

## Quick Start

1. **Generate Fernet key** (optional, but recommended for production):
   ```bash
   cd docker
   pip install cryptography  # If not already installed
   python generate_fernet_key.py
   ```
   Copy the output and update `AIRFLOW__CORE__FERNET_KEY` in `docker-compose.yml`.
   Also generate a secret key for `AIRFLOW__WEBSERVER__SECRET_KEY` (can be any random string).

2. **Start all services** (including Airflow):
   ```bash
   cd docker
   docker-compose up -d
   ```

2. **Wait for Airflow to initialize** (first time only, takes ~30 seconds):
   ```bash
   docker-compose logs -f airflow_webserver
   ```
   Look for "Airflow webserver is ready" message.

3. **Access Airflow UI**:
   - URL: http://localhost:8080
   - Username: `admin`
   - Password: `admin`

4. **Copy test DAGs** (if not already mounted):
   ```bash
   docker cp airflow_test_dag.py baselinr_airflow_webserver:/opt/airflow/dags/
   docker cp airflow_test_dag.py baselinr_airflow_scheduler:/opt/airflow/dags/
   ```

   Or ensure the volume mount in docker-compose.yml includes your DAGs directory.

## Test DAGs

The `airflow_test_dag.py` file contains several test DAGs:

- **baselinr_test_profile**: Tests the `BaselinrProfileOperator`
- **baselinr_test_drift**: Tests the `BaselinrDriftOperator`
- **baselinr_test_query**: Tests the `BaselinrQueryOperator`
- **baselinr_test_combined**: Tests a combined workflow with all operators

## Running Tests

1. Open the Airflow UI at http://localhost:8080
2. Find the test DAGs in the DAGs list
3. Toggle them ON (they start paused)
4. Click "Trigger DAG" to run them manually
5. Click on the DAG name to view details and logs

## Viewing Logs

```bash
# Airflow webserver logs
docker-compose logs -f airflow_webserver

# Airflow scheduler logs
docker-compose logs -f airflow_scheduler

# Task execution logs (view in Airflow UI or via CLI)
docker-compose exec airflow_webserver airflow tasks logs baselinr_test_profile profile_test 2024-01-01
```

## Configuration

The Airflow services use the same PostgreSQL database as Baselinr for testing. Make sure:

1. The `postgres` service is running and healthy
2. The Baselinr config at `/app/examples/config.yml` is properly configured
3. The database connection settings match your Docker setup

## Troubleshooting

### Airflow webserver won't start
- Check logs: `docker-compose logs airflow_webserver`
- Ensure `airflow_postgres` is healthy: `docker-compose ps`
- Try recreating: `docker-compose up -d --force-recreate airflow_webserver`

### DAGs not appearing
- Check scheduler logs: `docker-compose logs airflow_scheduler`
- Ensure DAG files are in `/opt/airflow/dags/`
- Check for Python syntax errors in DAG files
- Restart scheduler: `docker-compose restart airflow_scheduler`

### Import errors
- Ensure Baselinr is installed with Airflow extras: `pip install -e ".[airflow]"`
- Check that the Dockerfile.airflow includes the Airflow dependencies
- Verify the volume mount includes your code: `../:/app`

### Database connection issues
- Verify PostgreSQL is running: `docker-compose ps postgres`
- Check connection string in docker-compose.yml environment variables
- Ensure network connectivity between containers

## Security Notes

⚠️ **Important**: The default Fernet key and secret key in `docker-compose.yml` are placeholders. 
For production use, generate secure keys:

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

Update the `AIRFLOW__CORE__FERNET_KEY` and `AIRFLOW__WEBSERVER__SECRET_KEY` environment variables.

## Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

## Next Steps

- Test the RCA collector by configuring it in your Baselinr config
- Integrate with your actual data pipelines
- Set up proper authentication and security
- Configure Airflow connections for your data sources

