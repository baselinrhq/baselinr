# ProfileMesh Airflow Integration - Complete Guide

## 📋 Overview

ProfileMesh now provides full integration with Apache Airflow, enabling you to orchestrate data profiling tasks as part of your Airflow workflows. This integration maintains feature parity with the existing Dagster integration while adapting to Airflow's task-based execution model.

---

## 🎯 What's Included

### Core Components

1. **Operators** (`profilemesh/integrations/airflow/operators.py`)
   - `ProfileMeshProfilingOperator` - Profile all or specific tables
   - `ProfileMeshTableOperator` - Profile a single table with fine-grained control
   - `create_profiling_task_group()` - Helper to create parallel profiling tasks

2. **Sensors** (`profilemesh/integrations/airflow/sensors.py`)
   - `ProfileMeshPlanSensor` - Monitor configuration changes and trigger profiling

3. **Hooks** (`profilemesh/integrations/airflow/hooks.py`)
   - `ProfileMeshHook` - Manage configuration and ProfileEngine lifecycle

4. **Events** (`profilemesh/integrations/airflow/events.py`)
   - `emit_profiling_event()` - Structured logging and XCom emission

### Infrastructure

1. **Docker Setup**
   - `docker/Dockerfile.airflow` - Airflow container with ProfileMesh
   - `docker/docker-compose.yml` - Full stack including Airflow services
   - Auto-initialization with admin user (admin/admin)

2. **CI/CD**
   - `.github/workflows/airflow-integration.yml` - End-to-end validation
   - Validates DAG parsing, operator imports, and Docker deployment

3. **Examples**
   - `examples/airflow_dags/profilemesh_dag.py` - Three example workflows
   - `examples/airflow_dags/profilemesh_sensor_dag.py` - Plan monitoring example

4. **Tests**
   - `tests/test_airflow_integration.py` - 10 comprehensive test cases
   - Covers operators, sensors, hooks, and error handling

5. **Documentation**
   - `docs/integrations/airflow/README.md` - Complete integration guide
   - `docs/integrations/airflow/QUICKSTART.md` - 5-minute getting started
   - `docs/integrations/airflow/OPERATORS.md` - Detailed operator reference
   - `docs/integrations/airflow/SENSORS.md` - Comprehensive sensor guide
   - `docs/integrations/airflow/EXAMPLES.md` - 12+ real-world examples

---

## 🚀 Quick Start

### Installation

```bash
pip install profilemesh[airflow]
```

### Docker Setup (Recommended)

```bash
# Start all services
docker compose -f docker/docker-compose.yml up -d

# Access Airflow UI at http://localhost:8080
# Login: admin / admin

# View example DAGs and trigger them

# Stop services
docker compose -f docker/docker-compose.yml down -v
```

### Create Your First DAG

```python
from datetime import datetime
from airflow import DAG
from profilemesh.integrations.airflow import ProfileMeshProfilingOperator

with DAG(
    'my_profiling_dag',
    start_date=datetime(2024, 1, 1),
    schedule_interval='@daily',
    catchup=False,
) as dag:
    
    profile = ProfileMeshProfilingOperator(
        task_id='profile_tables',
        config_path='/path/to/config.yml',
    )
```

---

## 📚 Documentation

### Getting Started
- **[Quick Start Guide](./airflow/QUICKSTART.md)** - Get running in 5 minutes
- **[Complete README](./airflow/README.md)** - Full integration overview

### Reference
- **[Operators Reference](./airflow/OPERATORS.md)** - Detailed operator documentation
- **[Sensors Reference](./airflow/SENSORS.md)** - Comprehensive sensor guide

### Examples
- **[Examples Guide](./airflow/EXAMPLES.md)** - 12+ real-world scenarios
- **[Example DAGs](../../examples/airflow_dags/)** - Ready-to-use code

---

## 🏗️ Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Airflow DAG                          │
│  ┌────────────────────────────────────────────────┐    │
│  │         ProfileMeshProfilingOperator           │    │
│  │                      │                          │    │
│  │                      ▼                          │    │
│  │              ProfileMeshHook                    │    │
│  │              (Load Config)                      │    │
│  │                      │                          │    │
│  │                      ▼                          │    │
│  │              ProfileEngine                      │    │
│  │            (Execute Profiling)                  │    │
│  │                      │                          │    │
│  │                      ▼                          │    │
│  │              ResultWriter                       │    │
│  │            (Store Results)                      │    │
│  │                      │                          │    │
│  │                      ▼                          │    │
│  │         Emit XCom + Events                      │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              ProfileMeshPlanSensor                      │
│  ┌────────────────────────────────────────────────┐    │
│  │         Monitor Config Changes                  │    │
│  │                      │                          │    │
│  │         Load Config → Build Plan                │    │
│  │                      │                          │    │
│  │         Compare with Cursor                     │    │
│  │         (Airflow Variable)                      │    │
│  │                      │                          │    │
│  │         Changes Detected?                       │    │
│  │         ├─ Yes → Emit Metadata → Trigger        │    │
│  │         └─ No → Continue Poking                 │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### Feature Comparison

| Feature | Dagster | Airflow | Implementation |
|---------|---------|---------|----------------|
| Profiling | Assets | Operators | ✅ Complete |
| Parallelism | Automatic | TaskGroups | ✅ Complete |
| Plan Monitoring | Sensor | Sensor | ✅ Complete |
| Config Management | Resource | Hook | ✅ Complete |
| Metadata | Native | XCom | ✅ Complete |
| Events | Event Bus | XCom + Logs | ✅ Complete |
| State Storage | Cursor | Variables | ✅ Complete |

---

## 🎓 Usage Patterns

### Pattern 1: Simple Daily Profiling

```python
profile = ProfileMeshProfilingOperator(
    task_id='profile_all',
    config_path='/configs/prod.yml',
)
```

### Pattern 2: Parallel Profiling

```python
tasks = create_profiling_task_group(
    group_id='profile_tables',
    config_path='/configs/prod.yml',
)
```

### Pattern 3: Reactive Profiling

```python
sensor = ProfileMeshPlanSensor(
    task_id='detect_changes',
    config_path='/configs/prod.yml',
    poke_interval=300,
)

profile = ProfileMeshProfilingOperator(
    task_id='profile_changed',
    config_path='/configs/prod.yml',
)

sensor >> profile
```

### Pattern 4: Integrated Pipeline

```python
extract >> transform >> profile >> validate >> alert
```

See the [Examples Guide](./airflow/EXAMPLES.md) for 12+ complete patterns.

---

## 🧪 Testing

### Run Unit Tests

```bash
pytest tests/test_airflow_integration.py -v
```

### Run Integration Tests

```bash
# Start services
docker compose -f docker/docker-compose.yml up -d

# Wait for health checks

# Validate DAGs
docker compose -f docker/docker-compose.yml exec airflow_webserver \
  airflow dags list

# Stop services
docker compose -f docker/docker-compose.yml down -v
```

### CI/CD Validation

The GitHub Actions workflow (`.github/workflows/airflow-integration.yml`) automatically:
- ✅ Runs unit tests
- ✅ Builds Docker images
- ✅ Starts all services
- ✅ Validates DAG parsing
- ✅ Checks operator imports
- ✅ Verifies end-to-end setup

---

## 📊 Code Statistics

```
Integration Code:      765 lines
  - operators.py:      353 lines
  - sensors.py:        219 lines
  - hooks.py:           87 lines
  - events.py:          75 lines
  - __init__.py:        31 lines

Tests:                 428 lines
Example DAGs:          ~400 lines
Documentation:       5,000+ words
```

---

## 🔧 Configuration

### Environment Variables

```bash
export PROFILEMESH_CONFIG=/path/to/config.yml
export PROFILEMESH_SOURCE__HOST=localhost
export PROFILEMESH_SOURCE__PORT=5432
```

### Airflow Configuration

```python
# In airflow.cfg or docker-compose.yml
AIRFLOW__CORE__DAGS_FOLDER=/path/to/dags
AIRFLOW__CORE__LOAD_EXAMPLES=False
```

### ProfileMesh Configuration

```yaml
environment: production

source:
  type: postgres
  host: localhost
  port: 5432
  database: mydb

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
```

---

## 🐛 Troubleshooting

### DAGs Not Appearing

```bash
# Check DAG folder
airflow dags list

# Check for import errors
airflow dags list-import-errors

# Verify ProfileMesh is installed
python -c "import profilemesh; print('OK')"
```

### Operator Import Errors

```bash
pip install profilemesh[airflow]
```

### Database Connection Issues

```python
from profilemesh.config.loader import ConfigLoader
config = ConfigLoader.load_from_file('/path/to/config.yml')
print(config.source)
```

See the [README](./airflow/README.md#troubleshooting) for more solutions.

---

## 🎯 Best Practices

1. **Use TaskGroups** for parallel profiling of multiple tables
2. **Set appropriate retries** for resilience (2-3 retries recommended)
3. **Monitor execution times** and set SLAs
4. **Validate results** before downstream processing
5. **Use sensors** for reactive profiling
6. **Leverage XCom** for passing results between tasks
7. **Handle failures** gracefully with callbacks
8. **Tag DAGs** appropriately for organization
9. **Document dependencies** and expectations
10. **Test locally** with Docker before deploying

---

## 🚦 Next Steps

### Phase 1: Validate Setup
1. ✅ Run `docker compose up` to test the environment
2. ✅ Access Airflow UI at http://localhost:8080
3. ✅ Trigger example DAGs
4. ✅ Review logs and results

### Phase 2: Customize
1. Create your own configuration file
2. Write custom DAGs for your use case
3. Set up appropriate schedules
4. Configure alerts and notifications

### Phase 3: Deploy to Production
1. Review security settings
2. Configure production databases
3. Set up monitoring and alerting
4. Deploy to Kubernetes/Cloud Composer/MWAA

---

## 📦 What's Next

Potential future enhancements:

- Dynamic Task Mapping (Airflow 2.3+)
- OpenLineage integration for data lineage
- Custom XCom backends for large results
- Provider package distribution
- Airflow Datasets API integration (2.4+)
- Custom UI for cursor management
- Metrics export to Prometheus/StatsD

---

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- Additional example DAGs
- Performance optimizations
- Enhanced error handling
- More comprehensive tests
- Additional documentation

---

## 📄 License

ProfileMesh is released under the same license as the main project.

---

## 🙏 Acknowledgments

This integration was designed to maintain feature parity with the Dagster integration while embracing Airflow's task-based paradigm. Special thanks to the Airflow community for building a robust orchestration platform.

---

## 📞 Support

- **Documentation**: [docs/integrations/airflow/](./airflow/)
- **Examples**: [examples/airflow_dags/](../../examples/airflow_dags/)
- **Tests**: [tests/test_airflow_integration.py](../../tests/test_airflow_integration.py)
- **Issues**: GitHub Issues

---

**Happy profiling with Airflow! 🚀**
