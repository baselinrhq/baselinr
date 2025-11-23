# Baselinr API Reference

Complete API documentation for all public classes and methods in Baselinr.

## Table of Contents

- [Python SDK Client](#python-sdk-client)
  - [BaselinrClient](#baselinrclient)
- [Configuration Classes](#configuration-classes)
  - [BaselinrConfig](#baselinrconfig)
  - [ConnectionConfig](#connectionconfig)
  - [ProfilingConfig](#profilingconfig)
  - [DriftDetectionConfig](#driftdetectionconfig)
- [Data Classes](#data-classes)
  - [ProfilingPlan](#profilingplan)
  - [TablePlan](#tableplan)
  - [ProfilingResult](#profilingresult)
  - [DriftReport](#driftreport)
  - [ColumnDrift](#columndrift)
- [Core Classes](#core-classes)
  - [PlanBuilder](#planbuilder)
  - [ProfileEngine](#profileengine)
  - [DriftDetector](#driftdetector)
  - [MetadataQueryClient](#metadataqueryclient)
- [CLI Commands](#cli-commands)

## Python SDK Client

### BaselinrClient

High-level Python SDK client providing unified access to all Baselinr functionality.

**Location**: `baselinr.client.BaselinrClient`

#### Constructor

```python
BaselinrClient(
    config_path: Optional[str] = None,
    config: Optional[BaselinrConfig | Dict[str, Any]] = None
)
```

Initialize the Baselinr client.

**Parameters:**
- `config_path` (Optional[str]): Path to configuration file (YAML or JSON)
- `config` (Optional[BaselinrConfig | Dict[str, Any]]): Configuration object or dictionary

**Raises:**
- `ValueError`: If neither or both `config_path` and `config` are provided
- `FileNotFoundError`: If `config_path` doesn't exist

**Example:**
```python
from baselinr import BaselinrClient

# Using config file
client = BaselinrClient(config_path="config.yml")

# Using config dictionary
client = BaselinrClient(config={"environment": "development", ...})
```

#### Properties

##### `config: BaselinrConfig` (read-only)

Access the cached configuration object.

**Example:**
```python
environment = client.config.environment
source_type = client.config.source.type
```

#### Methods

##### `plan(table_patterns=None, verbose=False) -> ProfilingPlan`

Build execution plan without running profiling.

**Parameters:**
- `table_patterns` (Optional[List[TablePattern]]): Optional list of tables to plan for (uses config if not provided)
- `verbose` (bool): Whether to include verbose details in plan (default: False)

**Returns:** `ProfilingPlan` object with execution details

**Example:**
```python
plan = client.plan()
print(f"Will profile {plan.total_tables} tables")
print(f"Estimated metrics: {plan.estimated_metrics}")

# Access plan details
for table_plan in plan.tables:
    print(f"{table_plan.full_name}: {table_plan.status}")
```

##### `profile(table_patterns=None, dry_run=False, progress_callback=None) -> List[ProfilingResult]`

Profile tables and write results to storage.

**Parameters:**
- `table_patterns` (Optional[List[TablePattern]]): Optional list of tables to profile (uses config if not provided)
- `dry_run` (bool): If True, profile but don't write to storage (default: False)
- `progress_callback` (Optional[Callable]): Optional callback function(current, total, table_name) called when starting each table

**Returns:** List of `ProfilingResult` objects

**Example:**
```python
# Simple profiling
results = client.profile()

# With progress callback
def progress(current, total, table_name):
    print(f"Profiling {table_name} ({current}/{total})...")

results = client.profile(progress_callback=progress)

# Dry run (test without writing)
results = client.profile(dry_run=True)

# Access results
for result in results:
    print(f"{result.dataset_name}:")
    print(f"  Run ID: {result.run_id}")
    print(f"  Columns: {len(result.columns)}")
    print(f"  Row count: {result.metadata.get('row_count')}")
```

##### `detect_drift(dataset_name, baseline_run_id=None, current_run_id=None, schema_name=None) -> DriftReport`

Detect drift between profiling runs.

**Parameters:**
- `dataset_name` (str): Name of the dataset/table
- `baseline_run_id` (Optional[str]): Run ID to use as baseline (default: auto-selected based on strategy)
- `current_run_id` (Optional[str]): Run ID to compare (default: latest run)
- `schema_name` (Optional[str]): Optional schema name

**Returns:** `DriftReport` object with detected drift details

**Example:**
```python
# Automatic baseline selection
report = client.detect_drift("customers")

# Specify runs explicitly
report = client.detect_drift(
    dataset_name="customers",
    baseline_run_id="abc-123",
    current_run_id="def-456"
)

# Access drift information
print(f"Total drifts: {report.summary['total_drifts']}")
print(f"Schema changes: {len(report.schema_changes)}")

for drift in report.column_drifts:
    if drift.drift_detected:
        print(f"{drift.column_name}.{drift.metric_name}:")
        print(f"  Severity: {drift.drift_severity}")
        print(f"  Change: {drift.change_percent:.2f}%")
```

##### `query_runs(schema=None, table=None, status=None, environment=None, days=None, limit=100, offset=0) -> List[RunSummary]`

Query profiling runs with filters.

**Parameters:**
- `schema` (Optional[str]): Filter by schema name
- `table` (Optional[str]): Filter by table name
- `status` (Optional[str]): Filter by status
- `environment` (Optional[str]): Filter by environment
- `days` (Optional[int]): Number of days to look back
- `limit` (int): Maximum results to return (default: 100)
- `offset` (int): Pagination offset (default: 0)

**Returns:** List of `RunSummary` objects

**Example:**
```python
# Recent runs
runs = client.query_runs(days=7, limit=10)

# Filter by table
runs = client.query_runs(table="customers", days=30)

# Pagination
page1 = client.query_runs(limit=10, offset=0)
page2 = client.query_runs(limit=10, offset=10)

# Access run information
for run in runs:
    print(f"{run.dataset_name}: {run.profiled_at}")
    print(f"  Run ID: {run.run_id}")
    print(f"  Rows: {run.row_count}")
```

##### `query_drift(table=None, schema=None, severity=None, days=7, limit=100, offset=0) -> List[DriftEvent]`

Query drift events.

**Parameters:**
- `table` (Optional[str]): Filter by table name
- `schema` (Optional[str]): Filter by schema name
- `severity` (Optional[str]): Filter by severity (low/medium/high)
- `days` (int): Number of days to look back (default: 7)
- `limit` (int): Maximum results to return (default: 100)
- `offset` (int): Pagination offset (default: 0)

**Returns:** List of `DriftEvent` objects

**Example:**
```python
# All drift events
drift_events = client.query_drift(days=7)

# High severity only
high_severity = client.query_drift(severity="high", days=7)

# Specific table
table_drift = client.query_drift(table="customers", days=30)
```

##### `query_anomalies(table=None, schema=None, days=7, limit=100, offset=0) -> List[AnomalyEvent]`

Query anomaly events.

**Parameters:**
- `table` (Optional[str]): Filter by table name
- `schema` (Optional[str]): Filter by schema name
- `days` (int): Number of days to look back (default: 7)
- `limit` (int): Maximum results to return (default: 100)
- `offset` (int): Pagination offset (default: 0)

**Returns:** List of `AnomalyEvent` objects

##### `query_run_details(run_id) -> Dict[str, Any]`

Get detailed information about a specific profiling run.

**Parameters:**
- `run_id` (str): Run ID to query

**Returns:** Dictionary with run details

##### `query_table_history(table_name, schema_name=None, days=30, limit=100) -> List[Dict[str, Any]]`

Get profiling history for a table over time.

**Parameters:**
- `table_name` (str): Name of the table
- `schema_name` (Optional[str]): Optional schema name
- `days` (int): Number of days to look back (default: 30)
- `limit` (int): Maximum results to return (default: 100)

**Returns:** List of dictionaries with historical profiling data

##### `get_status(drift_only=False) -> Dict[str, Any]`

Get comprehensive status summary.

**Parameters:**
- `drift_only` (bool): If True, only include drift summary (default: False)

**Returns:** Dictionary with status summary including runs and drift information

##### `migrate_status() -> Dict[str, Any]`

Get migration status.

**Returns:** Dictionary with current schema version and pending migrations

##### `migrate_apply(dry_run=False) -> List[str]`

Apply pending migrations.

**Parameters:**
- `dry_run` (bool): If True, show what would be applied without applying (default: False)

**Returns:** List of applied migration IDs

##### `migrate_validate() -> Dict[str, Any]`

Validate migration state.

**Returns:** Dictionary with validation results

---

## Configuration Classes

### BaselinrConfig

Main Baselinr configuration class.

**Location**: `baselinr.config.schema.BaselinrConfig`

**Fields:**
- `environment` (str): Environment name (development/test/production)
- `source` (ConnectionConfig): Source database connection
- `storage` (StorageConfig): Storage configuration
- `profiling` (ProfilingConfig): Profiling configuration
- `drift_detection` (DriftDetectionConfig): Drift detection configuration
- `hooks` (HooksConfig): Event hooks configuration
- `monitoring` (MonitoringConfig): Monitoring configuration
- `retry` (RetryConfig): Retry configuration
- `execution` (ExecutionConfig): Execution and parallelism configuration
- `incremental` (IncrementalConfig): Incremental profiling configuration
- `schema_change` (SchemaChangeConfig): Schema change detection configuration

For detailed configuration reference, see [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md).

---

## Data Classes

### ProfilingPlan

Execution plan for profiling operations.

**Location**: `baselinr.planner.ProfilingPlan`

**Fields:**
- `run_id` (str): Unique run identifier
- `timestamp` (datetime): Plan timestamp
- `environment` (str): Environment name
- `tables` (List[TablePlan]): List of tables to profile
- `source_type` (str): Source database type
- `source_database` (str): Source database name
- `drift_strategy` (str): Drift detection strategy
- `total_tables` (int): Total number of tables
- `estimated_metrics` (int): Estimated number of metrics

**Methods:**
- `to_dict() -> Dict[str, Any]`: Convert plan to dictionary

### TablePlan

Plan for profiling a single table.

**Location**: `baselinr.planner.TablePlan`

**Fields:**
- `name` (str): Table name
- `schema` (Optional[str]): Schema name
- `status` (str): Table status (ready/pending/skipped)
- `partition_config` (Optional[Dict[str, Any]]): Partition configuration
- `sampling_config` (Optional[Dict[str, Any]]): Sampling configuration
- `metrics` (List[str]): List of metrics to compute
- `metadata` (Dict[str, Any]): Additional metadata

**Properties:**
- `full_name` (str): Fully qualified table name (schema.table)

### ProfilingResult

Container for profiling results.

**Location**: `baselinr.profiling.core.ProfilingResult`

**Fields:**
- `run_id` (str): Unique run identifier
- `dataset_name` (str): Dataset/table name
- `schema_name` (Optional[str]): Schema name
- `profiled_at` (datetime): Profiling timestamp
- `columns` (List[Dict[str, Any]]): Column metrics
- `metadata` (Dict[str, Any]): Additional metadata

**Methods:**
- `add_column_metrics(column_name, column_type, metrics)`: Add metrics for a column
- `to_dict() -> Dict[str, Any]`: Convert result to dictionary

### DriftReport

Complete drift detection report.

**Location**: `baselinr.drift.detector.DriftReport`

**Fields:**
- `dataset_name` (str): Dataset/table name
- `schema_name` (Optional[str]): Schema name
- `baseline_run_id` (str): Baseline run ID
- `current_run_id` (str): Current run ID
- `baseline_timestamp` (datetime): Baseline timestamp
- `current_timestamp` (datetime): Current timestamp
- `column_drifts` (List[ColumnDrift]): List of column drifts
- `schema_changes` (List[str]): List of schema changes
- `summary` (Dict[str, Any]): Summary statistics

**Methods:**
- `to_dict() -> Dict[str, Any]`: Convert report to dictionary

### ColumnDrift

Represents drift detected in a single column.

**Location**: `baselinr.drift.detector.ColumnDrift`

**Fields:**
- `column_name` (str): Column name
- `metric_name` (str): Metric name
- `baseline_value` (Any): Baseline value
- `current_value` (Any): Current value
- `change_percent` (Optional[float]): Percentage change
- `change_absolute` (Optional[float]): Absolute change
- `drift_detected` (bool): Whether drift was detected
- `drift_severity` (str): Severity level (none/low/medium/high)
- `metadata` (Optional[Dict[str, Any]]): Additional metadata

---

## Core Classes

### PlanBuilder

Builds profiling execution plans from configuration.

**Location**: `baselinr.planner.PlanBuilder`

**Methods:**
- `build_plan() -> ProfilingPlan`: Build execution plan from configuration

### ProfileEngine

Main profiling engine for Baselinr.

**Location**: `baselinr.profiling.core.ProfileEngine`

**Methods:**
- `profile(table_patterns=None, progress_callback=None) -> List[ProfilingResult]`: Profile tables

### DriftDetector

Detects drift between profiling runs.

**Location**: `baselinr.drift.detector.DriftDetector`

**Methods:**
- `detect_drift(dataset_name, baseline_run_id=None, current_run_id=None, schema_name=None) -> DriftReport`: Detect drift

### MetadataQueryClient

Client for querying Baselinr metadata from storage.

**Location**: `baselinr.query.client.MetadataQueryClient`

**Methods:**
- `query_runs(...) -> List[RunSummary]`: Query profiling runs
- `query_drift(...) -> List[DriftEvent]`: Query drift events
- `query_anomalies(...) -> List[AnomalyEvent]`: Query anomaly events

---

## CLI Commands

### `baselinr plan`

Build execution plan without running profiling.

**Usage:**
```bash
baselinr plan --config config.yml [--verbose]
```

### `baselinr profile`

Profile tables and store results.

**Usage:**
```bash
baselinr profile --config config.yml [--dry-run] [--table TABLE]
```

### `baselinr drift`

Detect drift between profiling runs.

**Usage:**
```bash
baselinr drift --config config.yml --dataset DATASET [--baseline-run-id ID] [--current-run-id ID]
```

### `baselinr query`

Query profiling runs, drift events, or anomalies.

**Usage:**
```bash
baselinr query runs --config config.yml [--table TABLE] [--days DAYS] [--limit LIMIT]
baselinr query drift --config config.yml [--table TABLE] [--severity SEVERITY] [--days DAYS]
baselinr query anomalies --config config.yml [--table TABLE] [--days DAYS]
```

### `baselinr status`

Get comprehensive status summary.

**Usage:**
```bash
baselinr status --config config.yml [--drift-only]
```

### `baselinr migrate`

Manage schema migrations.

**Usage:**
```bash
baselinr migrate status --config config.yml
baselinr migrate apply --config config.yml [--dry-run]
baselinr migrate validate --config config.yml
```

### `baselinr ui`

Start local web dashboard.

**Usage:**
```bash
baselinr ui --config config.yml [--host HOST] [--port PORT]
```

---

## Related Documentation

- [Configuration Reference](CONFIG_REFERENCE.md) - Complete configuration schema documentation
- [Python SDK Guide](../guides/PYTHON_SDK.md) - Comprehensive SDK usage guide
- [CLI Documentation](../schemas/STATUS_COMMAND.md) - CLI command reference

