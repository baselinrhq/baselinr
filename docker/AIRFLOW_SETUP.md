# Airflow Integration Setup

This directory contains the official Apache Airflow docker-compose setup for ProfileMesh integration testing.

## Quick Start

```bash
# Start Airflow with ProfileMesh integration
cd docker
docker compose -f docker-compose-airflow.yml up -d

# Access Airflow UI
open http://localhost:8080
# Login: airflow / airflow

# View logs
docker compose -f docker-compose-airflow.yml logs -f

# Stop everything
docker compose -f docker-compose-airflow.yml down -v
```

## Architecture

### Services

1. **airflow-init** - One-time initialization
   - Runs database migrations
   - Creates admin user (airflow/airflow)
   - Validates system requirements

2. **airflow-webserver** - Web UI
   - Accessible at http://localhost:8080
   - Health check: http://localhost:8080/health

3. **airflow-scheduler** - DAG scheduler
   - Monitors and triggers DAGs
   - Health check on port 8974

4. **airflow-postgres** - Airflow metadata database
   - Port: 5434 (host) → 5432 (container)
   - User: airflow / airflow / airflow

5. **profilemesh-postgres** - Sample data for profiling
   - Port: 5433 (host) → 5432 (container)
   - User: profilemesh / profilemesh / profilemesh
   - Initialized with sample schema via init_postgres.sql

### ProfileMesh Integration

ProfileMesh is installed at container startup via:
```yaml
_PIP_ADDITIONAL_REQUIREMENTS: 'pip install -e /opt/profilemesh[airflow]'
```

**Mounted Volumes:**
- `/opt/profilemesh` - ProfileMesh codebase (read-only)
- `/opt/airflow/dags` - Example DAGs from `examples/airflow_dags/`

**Environment Configuration:**
```yaml
PROFILEMESH_CONFIG: /opt/profilemesh/examples/config.yml
PROFILEMESH_SOURCE__HOST: profilemesh-postgres
PROFILEMESH_STORAGE__CONNECTION__HOST: profilemesh-postgres
```

## Example DAGs

Three example DAGs are automatically loaded:

1. **profilemesh_profile_all** - Profile all tables with single operator
2. **profilemesh_profile_parallel** - Parallel profiling with task groups
3. **profilemesh_plan_monitor** - Plan-aware sensor for change detection

View them in the Airflow UI after startup!

## Based on Official Airflow Setup

This configuration is based on [Apache Airflow's official docker-compose.yaml](https://airflow.apache.org/docs/apache-airflow/2.8.1/docker-compose.yaml) with these modifications:

- **Executor:** CeleryExecutor → LocalExecutor (simpler, no Redis)
- **Examples:** Disabled (LOAD_EXAMPLES=false)
- **Auto-pause:** Disabled (DAGS_ARE_PAUSED_AT_CREATION=false)
- **Additional packages:** ProfileMesh with airflow extras
- **Additional volumes:** ProfileMesh codebase + sample data database

## Troubleshooting

### Webserver won't start

Check the init service completed successfully:
```bash
docker compose -f docker-compose-airflow.yml logs airflow-init
```

### DAGs not appearing

1. Check the DAGs directory is mounted:
```bash
docker compose -f docker-compose-airflow.yml exec airflow-webserver ls -la /opt/airflow/dags
```

2. Check for import errors in the Airflow UI or:
```bash
docker compose -f docker-compose-airflow.yml exec airflow-webserver airflow dags list-import-errors
```

### ProfileMesh not installed

Check the pip install succeeded:
```bash
docker compose -f docker-compose-airflow.yml logs airflow-webserver | grep profilemesh
```

## Production Deployment

**⚠️ This setup is for development/testing only!**

For production:
1. Build a custom Docker image with ProfileMesh pre-installed
2. Use a managed Airflow service (Cloud Composer, MWAA, etc.)
3. Configure proper secrets management
4. Use external databases (not containerized)
5. Set up proper authentication and authorization

See [Airflow's production deployment guide](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/production-deployment.html).

## CI/CD

GitHub Actions validates the integration using this setup:
- `.github/workflows/airflow-integration.yml`

The workflow:
1. Starts all services
2. Waits for webserver health check
3. Lists DAGs
4. Validates DAG parsing
5. Tests ProfileMesh operator imports

## References

- [Airflow Docker Compose](https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/index.html)
- [ProfileMesh Airflow Integration Docs](../docs/integrations/airflow/)
- [Example DAGs](../examples/airflow_dags/)
