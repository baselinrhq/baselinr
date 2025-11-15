# Airbyte & Airflow Integration Plan for ProfileMesh

## 🎯 Executive Summary

This plan outlines the integration of ProfileMesh with **Airflow** (orchestration) and **Airbyte** (data ingestion), following the successful pattern established with the Dagster integration. This will enable ProfileMesh to be used in Airflow-based data pipelines and potentially trigger profiling after Airbyte sync operations.

---

## 📋 Table of Contents

1. [Background & Context](#background--context)
2. [Integration Architecture](#integration-architecture)
3. [Components to Build](#components-to-build)
4. [Implementation Plan](#implementation-plan)
5. [Testing Strategy](#testing-strategy)
6. [Documentation Requirements](#documentation-requirements)
7. [Success Criteria](#success-criteria)
8. [Timeline Estimate](#timeline-estimate)

---

## 🔍 Background & Context

### Current State
- ✅ **Dagster Integration**: Fully functional with assets, sensors, events, and resources
- ✅ **Core ProfileMesh**: CLI, profiling engine, drift detection, event hooks
- ✅ **Docker Environment**: PostgreSQL, Dagster daemon, Dagster UI

### Why Airflow + Airbyte?

**Airflow** is the most widely-adopted orchestration framework in data engineering:
- Used by many enterprises as their primary orchestration tool
- Mature ecosystem with extensive operator library
- Strong community and support

**Airbyte** is a leading open-source ELT platform:
- Handles data ingestion from 300+ sources
- Natural trigger point for data profiling (after data lands)
- API-driven for programmatic integration

**Use Case**: Profile data immediately after Airbyte syncs it to the warehouse, or orchestrate ProfileMesh runs in Airflow DAGs alongside other data operations.

---

## 🏗️ Integration Architecture

### High-Level Flow

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Airbyte    │────────▶│   Airflow    │────────▶│ ProfileMesh  │
│  Data Sync   │         │   Operator   │         │  Profiling   │
└──────────────┘         └──────────────┘         └──────────────┘
      │                         │                         │
      │                         │                         │
      ▼                         ▼                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    Data Warehouse                            │
│                  (Postgres/Snowflake)                        │
└──────────────────────────────────────────────────────────────┘
```

### Integration Patterns

1. **Pattern A: Post-Airbyte Profiling**
   - Airbyte syncs data to warehouse
   - Airflow sensor detects sync completion
   - ProfileMesh operator profiles the new/updated tables
   - Drift detection runs automatically

2. **Pattern B: Standalone Airflow Orchestration**
   - Airflow DAG schedules ProfileMesh runs
   - Independent of Airbyte (useful for existing Airflow users)
   - Can coordinate with other data quality tasks

3. **Pattern C: Event-Driven**
   - Airbyte webhook triggers Airflow DAG
   - ProfileMesh runs as part of the triggered workflow
   - Real-time profiling after data ingestion

---

## 🔧 Components to Build

### 1. Airflow Operator (`profilemesh/integrations/airflow/`)

Following the Dagster pattern, create:

#### File Structure
```
profilemesh/integrations/airflow/
├── __init__.py                 # Main exports
├── operators.py                # ProfileMeshOperator
├── sensors.py                  # ProfileMeshPlanSensor, AirbyteSyncSensor
├── hooks.py                    # ProfileMeshHook (connection management)
└── utils.py                    # Helper functions
```

#### Core Components

**A. ProfileMeshOperator** (`operators.py`)
```python
class ProfileMeshOperator(BaseOperator):
    """
    Airflow operator to run ProfileMesh profiling.
    
    Similar to Dagster assets but as an Airflow operator.
    Profiles specified tables and writes results to storage.
    """
    
    def __init__(
        self,
        config_path: str,
        table_patterns: Optional[List[str]] = None,
        environment: Optional[str] = None,
        dry_run: bool = False,
        fail_on_error: bool = True,
        **kwargs
    ):
        ...
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """Execute profiling and return results metadata."""
        ...
```

**B. ProfileMeshHook** (`hooks.py`)
```python
class ProfileMeshHook(BaseHook):
    """
    Hook for managing ProfileMesh configuration and execution.
    
    Similar to ProfileMeshResource in Dagster.
    Handles config loading, caching, and execution context.
    """
    
    def get_config(self) -> ProfileMeshConfig:
        """Load and cache ProfileMesh configuration."""
        ...
    
    def run_profiling(
        self, 
        table_patterns: Optional[List[str]] = None
    ) -> List[ProfilingResult]:
        """Execute profiling with the loaded config."""
        ...
```

**C. Sensors** (`sensors.py`)
```python
class ProfileMeshPlanSensor(BaseSensorOperator):
    """
    Sensor that triggers when ProfileMesh plan changes.
    
    Similar to Dagster's profilemesh_plan_sensor.
    Monitors config changes and triggers DAG runs.
    """
    ...

class AirbyteSyncSensor(BaseSensorOperator):
    """
    Sensor that monitors Airbyte sync completion.
    
    Polls Airbyte API for sync status and triggers
    ProfileMesh profiling when sync completes.
    """
    ...
```

**D. XCom Integration**
- Operators push metadata to XCom for downstream tasks
- Include run_id, table names, row counts, drift alerts
- Enable conditional DAG execution based on profiling results

### 2. Airbyte Integration (`profilemesh/integrations/airbyte/`)

#### File Structure
```
profilemesh/integrations/airbyte/
├── __init__.py              # Main exports
├── client.py                # Airbyte API client
├── triggers.py              # Trigger profiling after Airbyte sync
└── config_templates/        # Example connection configs
    ├── postgres_source.json
    ├── snowflake_dest.json
    └── sync_config.json
```

#### Core Components

**A. AirbyteClient** (`client.py`)
```python
class AirbyteClient:
    """
    Client for interacting with Airbyte API.
    
    - Check sync status
    - Trigger syncs programmatically
    - Get sync logs and metadata
    - List connections and streams
    """
    
    def get_sync_status(self, connection_id: str) -> SyncStatus:
        """Get the latest sync status for a connection."""
        ...
    
    def wait_for_sync(
        self, 
        connection_id: str, 
        job_id: str, 
        timeout: int = 3600
    ) -> SyncResult:
        """Wait for sync completion with timeout."""
        ...
```

**B. PostSyncTrigger** (`triggers.py`)
```python
class PostSyncProfilingTrigger:
    """
    Trigger ProfileMesh profiling after Airbyte sync.
    
    Maps Airbyte streams to ProfileMesh table patterns
    and automatically profiles synced tables.
    """
    
    def create_profiling_config(
        self, 
        sync_result: SyncResult
    ) -> Dict[str, Any]:
        """Generate ProfileMesh config from sync metadata."""
        ...
```

### 3. Docker Test Environment

#### File Structure
```
docker/airflow/
├── docker-compose.yml        # Airflow + Airbyte stack
├── Dockerfile.airflow        # Custom Airflow image with ProfileMesh
├── dags/
│   ├── example_profilemesh_dag.py
│   ├── example_airbyte_profilemesh_dag.py
│   └── example_scheduled_profiling_dag.py
├── plugins/                  # Airflow plugins dir
└── airflow.cfg               # Airflow configuration
```

#### Services
- **Airflow Webserver** (port 8080)
- **Airflow Scheduler**
- **Airflow Worker** (CeleryExecutor or LocalExecutor)
- **PostgreSQL** (Airflow metadata + sample data)
- **Redis** (Celery backend, if needed)
- **Airbyte Server** (port 8000)
- **Airbyte Webapp** (port 8001)
- **Airbyte Temporal** (workflow engine)

### 4. Example DAGs

#### DAG 1: Standalone Profiling
```python
# dags/profilemesh_scheduled.py
from airflow import DAG
from profilemesh.integrations.airflow import ProfileMeshOperator

with DAG(
    'profilemesh_daily_profiling',
    schedule_interval='@daily',
    ...
) as dag:
    
    profile_customers = ProfileMeshOperator(
        task_id='profile_customers',
        config_path='/opt/airflow/config/profilemesh.yml',
        table_patterns=['customers'],
    )
    
    profile_orders = ProfileMeshOperator(
        task_id='profile_orders',
        config_path='/opt/airflow/config/profilemesh.yml',
        table_patterns=['orders'],
    )
    
    [profile_customers, profile_orders]
```

#### DAG 2: Post-Airbyte Profiling
```python
# dags/airbyte_sync_and_profile.py
from airflow import DAG
from airflow.providers.airbyte.operators.airbyte import AirbyteTriggerSyncOperator
from profilemesh.integrations.airflow import (
    ProfileMeshOperator,
    AirbyteSyncSensor
)

with DAG(
    'airbyte_sync_and_profile',
    schedule_interval='@hourly',
    ...
) as dag:
    
    # Trigger Airbyte sync
    trigger_sync = AirbyteTriggerSyncOperator(
        task_id='trigger_airbyte_sync',
        airbyte_conn_id='airbyte_default',
        connection_id='{{ var.value.airbyte_connection_id }}',
    )
    
    # Wait for sync completion
    wait_for_sync = AirbyteSyncSensor(
        task_id='wait_for_sync',
        airbyte_conn_id='airbyte_default',
        connection_id='{{ var.value.airbyte_connection_id }}',
        poke_interval=30,
        timeout=3600,
    )
    
    # Profile the synced data
    profile_synced_data = ProfileMeshOperator(
        task_id='profile_synced_data',
        config_path='/opt/airflow/config/profilemesh.yml',
        table_patterns=['{{ task_instance.xcom_pull(task_ids="trigger_sync")["streams"] }}'],
    )
    
    trigger_sync >> wait_for_sync >> profile_synced_data
```

#### DAG 3: Drift-Based Alerting
```python
# dags/profile_with_drift_detection.py
from airflow import DAG
from profilemesh.integrations.airflow import ProfileMeshOperator
from airflow.operators.python import BranchPythonOperator
from airflow.operators.email import EmailOperator

with DAG(
    'profile_with_drift_detection',
    schedule_interval='@daily',
    ...
) as dag:
    
    profile = ProfileMeshOperator(
        task_id='profile_tables',
        config_path='/opt/airflow/config/profilemesh.yml',
    )
    
    check_drift = BranchPythonOperator(
        task_id='check_drift',
        python_callable=check_for_drift,
    )
    
    alert_drift = EmailOperator(
        task_id='alert_drift',
        to='data-team@company.com',
        subject='Data Drift Detected',
        html_content='{{ task_instance.xcom_pull(task_ids="profile_tables") }}',
    )
    
    no_action = DummyOperator(task_id='no_action')
    
    profile >> check_drift >> [alert_drift, no_action]
```

---

## 📝 Implementation Plan

### Phase 1: Core Airflow Operator (Week 1)

**Tasks:**
1. ✅ Create `profilemesh/integrations/airflow/` directory
2. ✅ Implement `ProfileMeshOperator` with basic functionality
3. ✅ Implement `ProfileMeshHook` for config management
4. ✅ Add event emission support (leverage existing event system)
5. ✅ Write unit tests for operator and hook
6. ✅ Update `setup.py` with Airflow extras

**Deliverables:**
- Working ProfileMeshOperator
- Unit tests with >80% coverage
- Updated setup.py: `pip install profilemesh[airflow]`

### Phase 2: Sensors & Advanced Features (Week 1-2)

**Tasks:**
1. ✅ Implement `ProfileMeshPlanSensor` for config-based triggering
2. ✅ Implement `AirbyteSyncSensor` for Airbyte integration
3. ✅ Add XCom integration for metadata passing
4. ✅ Implement retry/failure handling
5. ✅ Add support for dynamic table pattern generation
6. ✅ Write integration tests

**Deliverables:**
- Functional sensors
- XCom integration working
- Integration tests

### Phase 3: Airbyte Integration (Week 2)

**Tasks:**
1. ✅ Create `profilemesh/integrations/airbyte/` directory
2. ✅ Implement `AirbyteClient` for API interactions
3. ✅ Implement `PostSyncProfilingTrigger`
4. ✅ Create stream-to-table mapping utilities
5. ✅ Add connection config templates
6. ✅ Write integration tests with mocked Airbyte API

**Deliverables:**
- Working Airbyte client
- Post-sync trigger functionality
- Config templates

### Phase 4: Docker Test Environment (Week 2-3)

**Tasks:**
1. ✅ Create `docker/airflow/` directory structure
2. ✅ Write `docker-compose.yml` with all services
3. ✅ Create custom Airflow Dockerfile with ProfileMesh
4. ✅ Add example DAGs (3 patterns shown above)
5. ✅ Configure Airflow connections and variables
6. ✅ Configure Airbyte with sample connection
7. ✅ Add init scripts for database setup
8. ✅ Write startup/shutdown scripts

**Deliverables:**
- Working Docker Compose setup
- Example DAGs demonstrating all patterns
- Documentation for running locally

### Phase 5: Documentation (Week 3)

**Tasks:**
1. ✅ Create `docs/integrations/airflow/` directory
   - `QUICKSTART.md` - Getting started guide
   - `OPERATOR_REFERENCE.md` - Complete operator docs
   - `SENSORS_REFERENCE.md` - Sensor documentation
   - `EXAMPLES.md` - Real-world DAG examples
2. ✅ Create `docs/integrations/airbyte/` directory
   - `INTEGRATION_GUIDE.md` - Airbyte setup guide
   - `POST_SYNC_PROFILING.md` - Post-sync pattern docs
   - `API_REFERENCE.md` - Airbyte client reference
3. ✅ Update main README with Airflow section
4. ✅ Create tutorial videos/GIFs (optional)

**Deliverables:**
- Complete documentation
- Updated README
- Architecture diagrams

### Phase 6: Testing & Polish (Week 3-4)

**Tasks:**
1. ✅ End-to-end testing with real Airflow + Airbyte
2. ✅ Performance testing with large DAGs
3. ✅ Error handling improvements
4. ✅ Logging enhancements
5. ✅ CI/CD pipeline for integration tests
6. ✅ Code review and refactoring
7. ✅ Release preparation

**Deliverables:**
- All tests passing
- Production-ready code
- CI/CD integration
- Release notes

---

## 🧪 Testing Strategy

### Unit Tests
```python
# tests/integrations/airflow/test_operator.py
def test_profilemesh_operator_executes():
    """Test operator execution with valid config."""
    ...

def test_profilemesh_operator_handles_errors():
    """Test operator error handling."""
    ...

def test_xcom_push_metadata():
    """Test XCom metadata pushing."""
    ...
```

### Integration Tests
```python
# tests/integrations/airflow/test_integration.py
def test_operator_in_dag():
    """Test operator in a real DAG context."""
    ...

def test_sensor_detects_plan_changes():
    """Test sensor plan change detection."""
    ...

def test_airbyte_sensor_polls_api():
    """Test Airbyte sensor with mocked API."""
    ...
```

### E2E Tests
```bash
# Docker-based end-to-end tests
docker-compose -f docker/airflow/docker-compose.yml up -d
pytest tests/e2e/test_airflow_integration.py
```

### Manual Testing Checklist
- [ ] Operator runs in Airflow UI
- [ ] Sensors trigger correctly
- [ ] Airbyte sync → ProfileMesh flow works
- [ ] Error handling displays in Airflow logs
- [ ] XCom metadata is accessible
- [ ] Drift detection triggers alerts
- [ ] Performance is acceptable for 100+ tables

---

## 📚 Documentation Requirements

### 1. User Documentation
- **Quickstart Guide**: 5-minute setup with Docker
- **Operator Reference**: Complete API docs for all operators/sensors
- **Configuration Guide**: How to configure Airflow connections
- **Example DAGs**: 10+ real-world patterns
- **Troubleshooting**: Common issues and solutions

### 2. Developer Documentation
- **Architecture Overview**: How integration works internally
- **Contributing Guide**: How to add new features
- **Testing Guide**: How to run tests locally
- **Release Process**: How to cut a new release

### 3. Integration Documentation
- **Airbyte Setup**: How to configure Airbyte connections
- **Webhook Integration**: Setting up Airbyte webhooks
- **Event System**: How events flow through the system

---

## ✅ Success Criteria

### Functional Requirements
- ✅ ProfileMeshOperator executes profiling in Airflow
- ✅ Sensors detect plan changes and Airbyte syncs
- ✅ XCom integration passes metadata between tasks
- ✅ Airbyte sync completion triggers profiling
- ✅ Docker environment runs all services successfully
- ✅ Example DAGs demonstrate all patterns

### Non-Functional Requirements
- ✅ Unit test coverage >80%
- ✅ Integration tests pass consistently
- ✅ Documentation is comprehensive and clear
- ✅ Performance: <5s overhead per operator execution
- ✅ Error messages are actionable
- ✅ Code follows project style guidelines

### User Experience
- ✅ Installation: `pip install profilemesh[airflow]` works
- ✅ Docker: `docker-compose up` starts environment
- ✅ DAG examples work out-of-the-box
- ✅ Error messages guide users to solutions
- ✅ Logs provide debugging information

---

## ⏱️ Timeline Estimate

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| Phase 1: Core Operator | 3-4 days | Working operator, basic tests |
| Phase 2: Sensors | 2-3 days | Sensors, XCom integration |
| Phase 3: Airbyte | 2-3 days | Airbyte client, triggers |
| Phase 4: Docker | 3-4 days | Full test environment |
| Phase 5: Documentation | 2-3 days | Complete docs |
| Phase 6: Testing & Polish | 3-4 days | Production-ready |
| **Total** | **15-21 days** | **Full integration** |

### Parallel Work Opportunities
- Documentation can be written alongside development
- Docker setup can be built while working on operators
- Airbyte integration can proceed independently of sensors

---

## 🚀 Getting Started (Post-Implementation)

Once implemented, users will be able to:

```bash
# Install with Airflow support
pip install profilemesh[airflow]

# Start test environment
cd docker/airflow
docker-compose up -d

# Access Airflow UI
open http://localhost:8080

# Access Airbyte UI
open http://localhost:8001

# Trigger example DAG
airflow dags trigger profilemesh_daily_profiling
```

---

## 🔄 Future Enhancements (Post-Phase 3)

1. **Airflow Provider Package**: Publish as `airflow-provider-profilemesh`
2. **TaskFlow API Support**: Modern Airflow 2.x decorator syntax
3. **Dynamic DAG Generation**: Auto-generate DAGs from ProfileMesh config
4. **Airflow Variables Integration**: Store ProfileMesh config in Airflow variables
5. **Connection Management**: Use Airflow connections for ProfileMesh DB config
6. **Metrics Integration**: Push metrics to Airflow metrics backend
7. **Great Expectations Integration**: Coordinate with GE for data quality
8. **dbt Integration**: Profile dbt models after dbt runs

---

## 📋 Dependencies

### Python Packages (New)
```python
# setup.py additions
"airflow": [
    "apache-airflow>=2.5.0",
    "apache-airflow-providers-airbyte>=3.2.0",  # For Airbyte operators
],
"airbyte": [
    "airbyte-api-python-sdk>=0.1.0",  # Airbyte API client
    "requests>=2.28.0",
],
```

### Infrastructure Dependencies
- Airflow 2.5+ (for testing)
- Airbyte 0.50+ (for testing)
- PostgreSQL (shared with existing setup)
- Redis (optional, for Celery)

---

## 🎯 Key Design Decisions

### 1. Follow Dagster Pattern
- ✅ **Rationale**: Consistency across integrations
- ✅ **Impact**: Easier to maintain, familiar to developers

### 2. Separate Airbyte Integration
- ✅ **Rationale**: Airbyte client useful beyond Airflow
- ✅ **Impact**: Can be used standalone or with other orchestrators

### 3. XCom for Metadata
- ✅ **Rationale**: Native Airflow pattern for task communication
- ✅ **Impact**: Enables conditional workflows and monitoring

### 4. Optional Airbyte Dependency
- ✅ **Rationale**: Not all users need Airbyte
- ✅ **Impact**: Separate extras: `[airflow]` and `[airflow,airbyte]`

### 5. Docker for Testing
- ✅ **Rationale**: Complex stack requires isolated environment
- ✅ **Impact**: Easier onboarding, consistent testing

---

## 🤔 Open Questions for Discussion

1. **Scope**: Should we support Airflow 1.x or only 2.x+?
   - **Recommendation**: Airflow 2.x+ only (1.x is EOL)

2. **Airbyte**: OSS version only, or also support Airbyte Cloud?
   - **Recommendation**: Both (API is similar)

3. **Deployment**: Should we create Helm charts for Kubernetes?
   - **Recommendation**: Phase 4 (post-Phase 3)

4. **Backwards Compatibility**: How to handle breaking changes?
   - **Recommendation**: Semantic versioning, deprecation warnings

5. **Monitoring**: Should we integrate with Airflow metrics?
   - **Recommendation**: Yes, push execution metrics

6. **Configuration**: Store config in Airflow Variables/Connections?
   - **Recommendation**: Support both file-based and Airflow-native

---

## 📞 Next Steps

1. **Review this plan** and provide feedback
2. **Prioritize phases** if timeline needs adjustment
3. **Assign resources** (developers, reviewers)
4. **Set up project tracking** (Jira, GitHub Projects, etc.)
5. **Kick off Phase 1** once approved

---

## 📎 Appendix

### A. Comparison: Dagster vs Airflow Integration

| Feature | Dagster | Airflow (Proposed) |
|---------|---------|-------------------|
| Resource/Hook | `ProfileMeshResource` | `ProfileMeshHook` |
| Asset/Task | Dynamic assets | `ProfileMeshOperator` |
| Sensors | `profilemesh_plan_sensor` | `ProfileMeshPlanSensor` |
| Event Emission | Built-in | XCom + Logging |
| Job/DAG | `create_profiling_job` | User-defined DAG |
| Schedule | `ScheduleDefinition` | `schedule_interval` |

### B. Example Configurations

**Airflow Connection**
```json
{
  "conn_id": "profilemesh_postgres",
  "conn_type": "postgres",
  "host": "postgres",
  "schema": "public",
  "login": "profilemesh",
  "password": "profilemesh",
  "port": 5432
}
```

**ProfileMesh Config for Airflow**
```yaml
environment: airflow_managed
source:
  type: postgres
  connection: "{{ conn.profilemesh_postgres }}"  # Use Airflow connection
storage:
  connection:
    type: postgres
    connection: "{{ conn.profilemesh_postgres }}"
  results_table: profilemesh_results
  runs_table: profilemesh_runs
profiling:
  tables:
    - table: customers
    - table: orders
```

### C. Resources

- [Airflow Custom Operators](https://airflow.apache.org/docs/apache-airflow/stable/howto/custom-operator.html)
- [Airbyte API Docs](https://docs.airbyte.com/api-documentation)
- [Airflow Providers](https://airflow.apache.org/docs/apache-airflow-providers/)
- [ProfileMesh Dagster Integration](profilemesh/integrations/dagster/)

---

**End of Plan Document**
