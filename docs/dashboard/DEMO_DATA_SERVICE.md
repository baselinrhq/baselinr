# DemoDataService Documentation

## Overview

`DemoDataService` is a drop-in replacement for `DatabaseClient` that serves data from pre-generated JSON files instead of a database. It provides the same interface and response models, enabling the Quality Studio demo to run without database dependencies.

## Features

- **Zero Database Dependencies**: Loads all data from JSON files
- **Full API Compatibility**: Implements all 18 methods from `DatabaseClient`
- **High Performance**: All queries complete in &lt;5ms (avg 0.59ms)
- **In-Memory Filtering**: Fast filtering, sorting, and pagination
- **Async Interface**: Maintains async/await compatibility with FastAPI

## Usage

### Basic Initialization

```python
from demo_data_service import DemoDataService

# Initialize with default data directory
service = DemoDataService()

# Or specify custom data directory
service = DemoDataService(data_dir="/path/to/demo_data")
```

### Example Queries

#### Get Profiling Runs

```python
# Get all runs
runs = await service.get_runs(limit=100)

# Filter by warehouse
runs = await service.get_runs(warehouse="snowflake", limit=50)

# Filter by date range
from datetime import datetime, timedelta
start_date = datetime.now() - timedelta(days=30)
runs = await service.get_runs(start_date=start_date)

# Multiple filters
runs = await service.get_runs(
    warehouse="bigquery",
    schema="analytics",
    table="customers",
    status="completed",
    sort_by="profiled_at",
    sort_order="desc",
    limit=20
)
```

#### Get Run Details

```python
# Get detailed metrics for a specific run
details = await service.get_run_details("run_abc123")
print(f"Table: {details.dataset_name}")
print(f"Columns: {len(details.columns)}")
for col in details.columns:
    print(f"  {col.column_name}: {col.null_percent}% nulls")
```

#### Get Dashboard Metrics

```python
# Get aggregate metrics for dashboard
metrics = await service.get_dashboard_metrics()
print(f"Total Runs: {metrics.total_runs}")
print(f"Total Tables: {metrics.total_tables}")
print(f"Drift Events: {metrics.total_drift_events}")
print(f"Validation Pass Rate: {metrics.validation_pass_rate}%")
```

#### Get Drift Alerts

```python
# Get all drift alerts
alerts = await service.get_drift_alerts(limit=100)

# Filter by severity
high_severity = await service.get_drift_alerts(severity="high")

# Filter by table
table_drift = await service.get_drift_alerts(table="customers", schema="raw")
```

#### Get Tables

```python
# List all tables
response = await service.get_tables(limit=50)
print(f"Total tables: {response.total}")
for table in response.tables:
    print(f"{table.schema_name}.{table.table_name}: {table.row_count} rows")

# Search tables
response = await service.get_tables(search="customer")

# Filter by warehouse
response = await service.get_tables(warehouse="snowflake")
```

#### Get Validation Results

```python
# Get validation summary
summary = await service.get_validation_summary()
print(f"Pass Rate: {summary.pass_rate}%")
print(f"Failed: {summary.failed_count}")

# Get validation results
results = await service.get_validation_results(
    passed=False,  # Only failed validations
    severity="high",
    limit=50
)
```

## API Methods

### Core Methods

| Method | Description | Filters |
|--------|-------------|---------|
| `get_runs()` | Get profiling run history | warehouse, schema, table, status, dates, duration |
| `get_run_details()` | Get detailed run metrics | run_id |
| `get_dashboard_metrics()` | Get aggregate KPIs | none |

### Table Methods

| Method | Description | Filters |
|--------|-------------|---------|
| `get_warehouses()` | List unique warehouses | none |
| `get_tables()` | List tables with pagination | warehouse, schema, search, has_drift |
| `get_table_overview()` | Get detailed table info | table, schema, warehouse |
| `get_table_metrics()` | Get table metrics | table, schema, warehouse |
| `get_table_validation_results()` | Get validation results for table | table, schema |

### Drift Methods

| Method | Description | Filters |
|--------|-------------|---------|
| `get_drift_alerts()` | Get drift detection alerts | warehouse, schema, table, severity, dates |
| `get_drift_summary()` | Get drift statistics | warehouse, schema, dates |
| `get_drift_details()` | Get detailed drift info | event_id |
| `get_drift_impact()` | Get drift impact analysis | event_id |

### Validation Methods

| Method | Description | Filters |
|--------|-------------|---------|
| `get_validation_summary()` | Get validation statistics | warehouse, schema, dates |
| `get_validation_results()` | List validation results | warehouse, schema, table, rule_type, passed, severity, dates |
| `get_validation_result_details()` | Get detailed validation info | result_id |
| `get_validation_failure_samples()` | Get failure samples | result_id, limit |

### Lineage Methods

| Method | Description | Filters |
|--------|-------------|---------|
| `get_lineage_impact()` | Get lineage-based impact | table, schema |

## Performance

Based on benchmarks with 120 runs, 582 metrics, 54 drift events, 95 tables, and 156 validation results:

- **Initialization**: 4.5ms
- **Average Query Time**: 0.59ms
- **Max Query Time**: 4.5ms
- **All Queries**: &lt;5ms (target was &lt;100ms)

### Performance by Operation Type

- **Simple Filters**: 0-1ms
- **Complex Filters**: 1-2ms
- **Aggregations**: 2-5ms
- **Pagination**: &lt;1ms overhead

## Data Loading

### On Initialization

The service loads all JSON files into memory:

1. **runs.json** → `self.runs_raw` (list)
2. **metrics.json** → `self.metrics_raw` (list)
3. **drift_events.json** → `self.drift_events_raw` (list)
4. **tables.json** → `self.tables_raw` (list)
5. **validation_results.json** → `self.validation_results_raw` (list)
6. **lineage.json** → `self.lineage_raw` (dict)
7. **metadata.json** → `self.metadata` (dict)

### Lookup Indices

For fast O(1) access, the service builds indices:

- `runs_by_id`: `{run_id: run_data}`
- `metrics_by_run_id`: `{run_id: [metrics]}`
- `drift_by_run_id`: `{run_id: [drift_events]}`
- `validations_by_run_id`: `{run_id: [validations]}`

## Filtering Implementation

### Supported Filter Types

1. **Equality**: `warehouse == "snowflake"`
2. **Date Ranges**: `start_date <= profiled_at <= end_date`
3. **Text Search**: `"customer" in table_name.lower()`
4. **Set Membership**: `status in ["completed", "success"]`
5. **Numeric Ranges**: `min_duration <= duration <= max_duration`

### Filter Pipeline

```
Raw Data → Filter → Sort → Paginate → Convert to Models → Return
```

## Sorting

Supports sorting by any field with ascending/descending order:

```python
# Sort by date descending (newest first)
runs = await service.get_runs(sort_by="profiled_at", sort_order="desc")

# Sort by row count ascending
tables = await service.get_tables(sort_by="row_count", sort_order="asc")
```

## Pagination

Standard offset/limit pagination:

```python
# First page (items 0-49)
page1 = await service.get_runs(offset=0, limit=50)

# Second page (items 50-99)
page2 = await service.get_runs(offset=50, limit=50)

# Response includes pagination metadata
print(f"Page: {page1.page}")
print(f"Total: {page1.total}")
```

## Integration with FastAPI

### Replace DatabaseClient

```python
# Before (database mode)
from database import DatabaseClient
db_client = DatabaseClient()

# After (demo mode)
from demo_data_service import DemoDataService
db_client = DemoDataService()

# All API routes work the same!
@app.get("/api/runs")
async def get_runs():
    return await db_client.get_runs(limit=100)
```

### Environment-Based Selection

```python
import os
from database import DatabaseClient
from demo_data_service import DemoDataService

# Choose client based on environment
if os.getenv("DEMO_MODE") == "true":
    db_client = DemoDataService()
else:
    db_client = DatabaseClient()
```

## Testing

### Run Unit Tests

```bash
cd dashboard/backend
pytest test_demo_data_service.py -v
```

### Run Smoke Test

```bash
python test_demo_data_service.py
```

### Run Benchmarks

```bash
python benchmark_demo_service.py
```

## Data Structure

### Demo Data Files

All files are in `dashboard/backend/demo_data/`:

- **runs.json**: Array of run objects
- **metrics.json**: Array of metric objects
- **drift_events.json**: Array of drift event objects
- **tables.json**: Array of table metadata objects
- **validation_results.json**: Array of validation result objects
- **lineage.json**: Object with `nodes` and `edges` arrays
- **metadata.json**: Generation metadata

### Example Data Structures

**Run Object**:
```json
{
  "run_id": "run_abc123",
  "dataset_name": "customers",
  "schema_name": "raw",
  "warehouse_type": "snowflake",
  "profiled_at": "2025-12-16T00:00:00+00:00",
  "status": "completed",
  "row_count": 1000000,
  "column_count": 8,
  "duration_seconds": 45.2,
  "environment": "production",
  "has_drift": false
}
```

**Metric Object**:
```json
{
  "run_id": "run_abc123",
  "column_name": "email",
  "column_type": "VARCHAR",
  "null_count": 150,
  "null_percent": 0.15,
  "distinct_count": 999000,
  "distinct_percent": 99.9,
  "min_value": "a@example.com",
  "max_value": "z@example.com"
}
```

## Limitations

1. **Read-Only**: Demo service doesn't support write operations
2. **Static Data**: Data doesn't change unless JSON files are regenerated
3. **No Real-Time Updates**: No live data streaming
4. **Fixed Dataset**: Limited to pre-generated demo data

## Troubleshooting

### Data Not Loading

```python
# Check data directory
service = DemoDataService()
print(f"Data dir: {service.data_dir}")
print(f"Runs loaded: {len(service.runs_raw)}")
```

### Slow Queries

```python
# Profile a query
import time
start = time.time()
results = await service.get_runs(limit=100)
print(f"Query time: {(time.time() - start) * 1000:.2f}ms")
```

### Missing Data

```python
# Check if data exists
print(f"Total runs: {len(service.runs_raw)}")
print(f"Total metrics: {len(service.metrics_raw)}")
print(f"Total drift events: {len(service.drift_events_raw)}")
```

## Future Enhancements

- [ ] Add caching for expensive aggregations
- [ ] Support for custom data transformations
- [ ] Data refresh mechanism
- [ ] Query result caching
- [ ] Compressed data loading

## See Also

- [Demo Data Generator](generate_demo_data.py) - Script to regenerate demo data
- [Unit Tests](test_demo_data_service.py) - Comprehensive test suite
- [Benchmarks](benchmark_demo_service.py) - Performance benchmarks
- [Demo Data README](demo_data/README.md) - Data structure documentation

