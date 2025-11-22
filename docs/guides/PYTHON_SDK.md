# Python SDK Guide

Baselinr provides a high-level Python SDK (`BaselinrClient`) for programmatic access to all functionality. This guide covers installation, basic usage, advanced patterns, and API reference.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Advanced Usage](#advanced-usage)
- [Best Practices](#best-practices)
- [Examples](#examples)

## Overview

The Baselinr Python SDK provides a clean, unified interface for:

- **Profiling**: Profile tables and collect metrics
- **Drift Detection**: Detect changes between profiling runs
- **Querying**: Query runs, drift events, anomalies, and history
- **Status Monitoring**: Get comprehensive status summaries
- **Schema Management**: Manage schema migrations

The SDK handles configuration loading, connection management, and event bus setup automatically, making it easy to integrate Baselinr into your Python workflows.

## Installation

The SDK is included in the main Baselinr package:

```bash
pip install baselinr
```

For development with optional dependencies:

```bash
pip install baselinr[dev]
```

## Quick Start

### Basic Usage

```python
from baselinr import BaselinrClient

# Initialize client with config file
client = BaselinrClient(config_path="config.yml")

# Build execution plan
plan = client.plan()
print(f"Will profile {plan.total_tables} tables")

# Profile tables
results = client.profile()
for result in results:
    print(f"Profiled {result.dataset_name}: {len(result.columns)} columns")

# Detect drift
drift_report = client.detect_drift("customers")
print(f"Found {len(drift_report.column_drifts)} column drifts")
```

### Initialization Options

The SDK supports multiple initialization patterns:

```python
# Option 1: Config file path
client = BaselinrClient(config_path="config.yml")

# Option 2: Config dictionary
config_dict = {
    "environment": "development",
    "source": {...},
    "storage": {...}
}
client = BaselinrClient(config=config_dict)

# Option 3: BaselinrConfig object
from baselinr.config.loader import ConfigLoader
config = ConfigLoader.load_from_file("config.yml")
client = BaselinrClient(config=config)
```

## API Reference

### BaselinrClient

Main SDK client class providing access to all Baselinr functionality.

#### Initialization

```python
BaselinrClient(
    config_path: Optional[str] = None,
    config: Optional[BaselinrConfig | Dict[str, Any]] = None
)
```

**Parameters:**
- `config_path` (Optional[str]): Path to configuration file (YAML or JSON)
- `config` (Optional[BaselinrConfig | Dict]): Configuration object or dictionary

**Raises:**
- `ValueError`: If neither or both `config_path` and `config` are provided
- `FileNotFoundError`: If `config_path` doesn't exist

**Example:**
```python
client = BaselinrClient(config_path="config.yml")
```

#### Properties

##### `config: BaselinrConfig` (read-only)

Access the cached configuration object.

```python
environment = client.config.environment
source_type = client.config.source.type
```

### Profiling Methods

#### `plan(table_patterns=None, verbose=False) -> ProfilingPlan`

Build execution plan without running profiling.

**Parameters:**
- `table_patterns` (Optional[List[TablePattern]]): Optional list of tables to plan for
- `verbose` (bool): Whether to include verbose details

**Returns:** `ProfilingPlan` object

**Example:**
```python
plan = client.plan()
print(f"Will profile {plan.total_tables} tables")
print(f"Estimated metrics: {plan.estimated_metrics}")

# Access plan details
for table_plan in plan.tables:
    print(f"{table_plan.full_name}: {table_plan.status}")
```

#### `profile(table_patterns=None, dry_run=False, progress_callback=None) -> List[ProfilingResult]`

Profile tables and write results to storage.

**Parameters:**
- `table_patterns` (Optional[List[TablePattern]]): Optional list of tables to profile
- `dry_run` (bool): If True, profile but don't write to storage
- `progress_callback` (Optional[Callable]): Callback function(current, total, table_name)

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

### Drift Detection

#### `detect_drift(dataset_name, baseline_run_id=None, current_run_id=None, schema_name=None) -> DriftReport`

Detect drift between profiling runs.

**Parameters:**
- `dataset_name` (str): Name of the dataset/table
- `baseline_run_id` (Optional[str]): Run ID to use as baseline (default: auto-selected)
- `current_run_id` (Optional[str]): Run ID to compare (default: latest)
- `schema_name` (Optional[str]): Optional schema name

**Returns:** `DriftReport` object

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

### Query Methods

#### `query_runs(schema=None, table=None, status=None, environment=None, days=None, limit=100, offset=0) -> List[RunSummary]`

Query profiling runs with filters.

**Parameters:**
- `schema` (Optional[str]): Filter by schema name
- `table` (Optional[str]): Filter by table name
- `status` (Optional[str]): Filter by status
- `environment` (Optional[str]): Filter by environment
- `days` (Optional[int]): Number of days to look back
- `limit` (int): Maximum results (default: 100)
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

#### `query_drift(table=None, schema=None, severity=None, days=7, limit=100, offset=0) -> List[DriftEvent]`

Query drift events.

**Parameters:**
- `table` (Optional[str]): Filter by table name
- `schema` (Optional[str]): Filter by schema name
- `severity` (Optional[str]): Filter by severity (low/medium/high)
- `days` (int): Number of days to look back (default: 7)
- `limit` (int): Maximum results (default: 100)
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

# Access event information
for event in drift_events:
    print(f"{event.table_name}.{event.column_name}:")
    print(f"  Metric: {event.metric_name}")
    print(f"  Change: {event.change_percent:.2f}%")
    print(f"  Severity: {event.drift_severity}")
```

#### `query_anomalies(table=None, schema=None, run_id=None, severity=None, days=7, limit=100, offset=0) -> List[Dict[str, Any]]`

Query anomaly events. Anomalies are automatically detected during profiling if enabled in config.

**Parameters:**
- `table` (Optional[str]): Filter by table name
- `schema` (Optional[str]): Filter by schema name
- `run_id` (Optional[str]): Filter by specific run ID
- `severity` (Optional[str]): Filter by severity (low/medium/high)
- `days` (int): Number of days to look back (default: 7)
- `limit` (int): Maximum results (default: 100)
- `offset` (int): Pagination offset (default: 0)

**Returns:** List of anomaly event dictionaries

**Example:**
```python
# Recent anomalies
anomalies = client.query_anomalies(days=7)

# High severity anomalies for specific table
high_anomalies = client.query_anomalies(
    table="customers",
    severity="high",
    days=7
)

# Anomalies for specific run
run_anomalies = client.query_anomalies(run_id="abc-123")

# Access anomaly information
for anomaly in anomalies:
    print(f"{anomaly['table_name']}.{anomaly['column_name']}:")
    print(f"  Metric: {anomaly['metric_name']}")
    print(f"  Value: {anomaly['current_value']}")
    print(f"  Timestamp: {anomaly['timestamp']}")
```

#### `query_run_details(run_id, dataset_name=None) -> Optional[Dict[str, Any]]`

Get detailed information about a specific run.

**Parameters:**
- `run_id` (str): Run ID to query
- `dataset_name` (Optional[str]): Optional dataset name (required if run has multiple tables)

**Returns:** Dictionary with run metadata and metrics, or None if not found

**Example:**
```python
details = client.query_run_details("abc-123-def")

if details:
    run = details['run']
    print(f"Table: {run['dataset_name']}")
    print(f"Profiled at: {run['profiled_at']}")
    print(f"Row count: {run['row_count']}")
    
    # Access metrics
    metrics = details['metrics']
    for column_name, column_metrics in metrics.items():
        print(f"{column_name}:")
        for metric_name, value in column_metrics.items():
            print(f"  {metric_name}: {value}")
```

#### `query_table_history(table, schema=None, days=30, limit=100) -> Dict[str, Any]`

Get profiling history for a table over time.

**Parameters:**
- `table` (str): Table name
- `schema` (Optional[str]): Optional schema name
- `days` (int): Number of days of history (default: 30)
- `limit` (int): Maximum results (default: 100)

**Returns:** Dictionary with table history data

**Example:**
```python
history = client.query_table_history("customers", days=90)

print(f"Table: {history['table_name']}")
print(f"Run count: {history['run_count']}")

# Access historical runs
for run in history['runs']:
    print(f"{run['profiled_at']}: {run['row_count']} rows")
```

### Status Monitoring

#### `get_status(drift_only=False, days=7, limit=10) -> Dict[str, Any]`

Get status summary (recent runs + drift summary).

**Parameters:**
- `drift_only` (bool): If True, only return drift summary (default: False)
- `days` (int): Number of days to look back (default: 7)
- `limit` (int): Maximum number of recent runs (default: 10)

**Returns:** Dictionary with runs_data and drift_summary

**Example:**
```python
# Full status
status = client.get_status(days=7, limit=20)

print(f"Recent runs: {len(status['runs_data'])}")
print(f"Active drift events: {len(status['drift_summary'])}")

# Access run details
for run in status['runs_data']:
    print(f"{run['table_name']}:")
    print(f"  Has drift: {run['has_drift']}")
    print(f"  Anomalies: {run['anomalies_count']}")
    print(f"  Status: {run['status_indicator']}")

# Drift-only status
drift_status = client.get_status(drift_only=True)
```

### Schema Migration

#### `migrate_status() -> Dict[str, Any]`

Check schema migration status.

**Returns:** Dictionary with current version and pending migrations

**Example:**
```python
status = client.migrate_status()

print(f"Current version: {status['current_version']}")
print(f"Latest version: {status['latest_version']}")
print(f"Pending migrations: {status['pending_migrations']}")
```

#### `migrate_apply(target_version=None, dry_run=False) -> Dict[str, Any]`

Apply schema migrations.

**Parameters:**
- `target_version` (Optional[int]): Target schema version (None = latest)
- `dry_run` (bool): If True, preview without applying (default: False)

**Returns:** Dictionary with migration results

**Example:**
```python
# Preview migrations
preview = client.migrate_apply(target_version=1, dry_run=True)
print(f"Would apply: {preview['migrations_to_apply']}")

# Apply migrations
result = client.migrate_apply(target_version=1)
print(f"Applied to version: {result['target_version']}")
```

#### `migrate_validate() -> Dict[str, Any]`

Validate schema integrity.

**Returns:** Dictionary with validation results

**Example:**
```python
result = client.migrate_validate()

if result['is_valid']:
    print("Schema is valid")
else:
    print(f"Schema errors: {result['errors']}")
    print(f"Warnings: {result['warnings']}")
```

## Advanced Usage

### Progress Callbacks

Monitor profiling progress with custom callbacks:

```python
def progress_callback(current, total, table_name):
    percentage = (current / total) * 100
    print(f"[{percentage:.1f}%] Profiling {table_name}...")

results = client.profile(progress_callback=progress_callback)
```

### Custom Configuration

Initialize with a configuration dictionary:

```python
config = {
    "environment": "production",
    "source": {
        "type": "postgres",
        "host": "prod-db.example.com",
        "database": "analytics",
        "username": "user",
        "password": "secret",
    },
    "storage": {
        "connection": {
            "type": "postgres",
            "host": "prod-db.example.com",
            "database": "analytics",
        },
        "runs_table": "baselinr_runs",
        "results_table": "baselinr_results",
        "create_tables": True,
    },
    "profiling": {
        "tables": [
            {"table": "customers"},
            {"table": "orders"},
        ],
    },
}

client = BaselinrClient(config=config)
```

### Error Handling

Handle errors gracefully:

```python
from baselinr import BaselinrClient

try:
    client = BaselinrClient(config_path="config.yml")
    
    # Profiling might fail if tables don't exist
    results = client.profile()
    
except FileNotFoundError:
    print("Configuration file not found")
except ValueError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Profiling failed: {e}")
```

### Drift Detection with Custom Baselines

Specify exact runs for drift comparison:

```python
# Get run IDs first
runs = client.query_runs(table="customers", days=30)

if len(runs) >= 2:
    baseline_id = runs[1].run_id  # Second-most recent
    current_id = runs[0].run_id   # Most recent
    
    report = client.detect_drift(
        dataset_name="customers",
        baseline_run_id=baseline_id,
        current_run_id=current_id
    )
```

### Batch Processing

Process multiple tables:

```python
tables = ["customers", "orders", "products"]

for table in tables:
    print(f"Profiling {table}...")
    # Note: profile() profiles all tables in config by default
    # For single table, you'd need to filter config or use table_patterns
    
# Or detect drift for all tables
for table in tables:
    try:
        report = client.detect_drift(table)
        if report.summary['total_drifts'] > 0:
            print(f"⚠️  Drift detected in {table}")
    except ValueError as e:
        print(f"ℹ️  Skipping {table}: {e}")
```

### Integration with Data Pipelines

Use in ETL pipelines:

```python
from baselinr import BaselinrClient

def data_quality_check():
    """Run data quality checks after ETL."""
    client = BaselinrClient(config_path="config.yml")
    
    # Profile new data
    results = client.profile()
    
    # Check for drift
    for result in results:
        try:
            report = client.detect_drift(result.dataset_name)
            
            if report.summary['drift_by_severity']['high'] > 0:
                # Alert on high-severity drift
                send_alert(f"High-severity drift in {result.dataset_name}")
                
        except ValueError:
            pass  # First run, no baseline yet
    
    return results
```

## Best Practices

### 1. Connection Management

The SDK manages connections automatically using lazy loading. Connections are created only when needed and reused efficiently.

```python
# Connections created on first query
client = BaselinrClient(config_path="config.yml")
runs = client.query_runs()  # Connection created here
drift = client.query_drift()  # Reuses same connection
```

### 2. Error Handling

Always wrap SDK calls in try-except blocks:

```python
try:
    results = client.profile()
except Exception as e:
    logger.error(f"Profiling failed: {e}")
    # Handle gracefully
```

### 3. Configuration Caching

The SDK caches configuration. If you need to reload config, create a new client:

```python
# Config is cached in client
client = BaselinrClient(config_path="config.yml")
config1 = client.config

# Update config file externally...

# Create new client to reload
client2 = BaselinrClient(config_path="config.yml")
config2 = client2.config  # Fresh config
```

### 4. Resource Cleanup

The SDK handles resource cleanup automatically. No explicit cleanup needed:

```python
# Connections are managed internally
client = BaselinrClient(config_path="config.yml")
results = client.profile()
# Connections cleaned up automatically
```

### 5. Thread Safety

The SDK client is not thread-safe. Use separate client instances for concurrent operations:

```python
from concurrent.futures import ThreadPoolExecutor

def profile_table(config_path, table):
    client = BaselinrClient(config_path=config_path)
    # Profile specific table...
    pass

# Use separate clients per thread
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(profile_table, "config.yml", table)
        for table in ["customers", "orders", "products"]
    ]
```

## Examples

### Complete Workflow Example

```python
from baselinr import BaselinrClient

# Initialize
client = BaselinrClient(config_path="config.yml")

# 1. Check current status
status = client.get_status(days=7)
print(f"Recent runs: {len(status['runs_data'])}")

# 2. Build plan
plan = client.plan()
print(f"Will profile {plan.total_tables} tables")

# 3. Profile with progress
def progress(current, total, table_name):
    print(f"Progress: {current}/{total} - {table_name}")

results = client.profile(progress_callback=progress)

# 4. Detect drift for each table
for result in results:
    try:
        report = client.detect_drift(result.dataset_name)
        
        if report.summary['total_drifts'] > 0:
            print(f"⚠️  Drift in {result.dataset_name}:")
            print(f"   High: {report.summary['drift_by_severity']['high']}")
            print(f"   Medium: {report.summary['drift_by_severity']['medium']}")
    except ValueError:
        print(f"ℹ️  First run for {result.dataset_name}")

# 5. Query anomalies
anomalies = client.query_anomalies(severity="high", days=7)
if anomalies:
    print(f"⚠️  Found {len(anomalies)} high-severity anomalies")

# 6. Get updated status
final_status = client.get_status()
print(f"Final status: {len(final_status['drift_summary'])} active drift events")
```

### CI/CD Integration

```python
from baselinr import BaselinrClient
import sys

def ci_quality_check():
    """Run in CI pipeline to check data quality."""
    client = BaselinrClient(config_path="config.yml")
    
    # Profile
    results = client.profile()
    
    # Check for critical issues
    critical_issues = []
    
    for result in results:
        try:
            report = client.detect_drift(result.dataset_name)
            
            # Fail on high-severity drift
            if report.summary['drift_by_severity']['high'] > 0:
                critical_issues.append(
                    f"High-severity drift in {result.dataset_name}"
                )
                
        except ValueError:
            pass
    
    # Check for anomalies
    anomalies = client.query_anomalies(severity="high", days=1)
    if anomalies:
        critical_issues.append(f"Found {len(anomalies)} high-severity anomalies")
    
    # Fail CI if critical issues found
    if critical_issues:
        print("❌ Data quality check failed:")
        for issue in critical_issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("✅ Data quality check passed")

if __name__ == "__main__":
    ci_quality_check()
```

## Additional Resources

- **Quick Start Example**: [examples/sdk_quickstart.py](../../examples/sdk_quickstart.py)
- **Advanced Example**: [examples/sdk_advanced.py](../../examples/sdk_advanced.py)
- **CLI Documentation**: [Status Command](../schemas/STATUS_COMMAND.md)
- **Configuration Guide**: [Main README](../../README.md#configuration-options)

## See Also

- [Drift Detection Guide](DRIFT_DETECTION.md) - Understanding drift detection
- [Anomaly Detection Guide](ANOMALY_DETECTION.md) - Automatic anomaly detection
- [Getting Started](../getting-started/QUICKSTART.md) - Initial setup guide

