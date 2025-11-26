# Baselinr Query Examples

Common query patterns and CLI usage examples for Baselinr metadata.

## CLI Query Commands

Baselinr provides powerful CLI commands for querying profiling metadata without writing SQL.

### Available Commands

```bash
baselinr query runs      # Query profiling run history
baselinr query drift     # Query drift detection events
baselinr query run       # Get details for specific run
baselinr query table     # Query table profiling history
baselinr lineage upstream    # Get upstream dependencies
baselinr lineage downstream # Get downstream dependencies
baselinr lineage path        # Find path between tables
baselinr lineage providers  # List available providers
```

---

## Query Runs

### Basic Usage

```bash
# Get last 10 runs
baselinr query runs --config config.yml
```

### Filter by Table

```bash
# Runs for specific table
baselinr query runs --config config.yml --table customers

# With schema
baselinr query runs --config config.yml --schema public --table orders
```

### Filter by Time Range

```bash
# Last 7 days
baselinr query runs --config config.yml --days 7

# Last 24 hours
baselinr query runs --config config.yml --days 1
```

### Filter by Status

```bash
# Only successful runs
baselinr query runs --config config.yml --status completed

# Only failed runs
baselinr query runs --config config.yml --status failed --days 7
```

### Filter by Environment

```bash
# Production runs only
baselinr query runs --config config.yml --environment production

# Staging runs
baselinr query runs --config config.yml --environment staging --days 30
```

### Pagination

```bash
# First 50 results
baselinr query runs --config config.yml --limit 50

# Next 50 results (pagination)
baselinr query runs --config config.yml --limit 50 --offset 50
```

### Output Formats

```bash
# Table format (default)
baselinr query runs --config config.yml --format table

# JSON format
baselinr query runs --config config.yml --format json

# CSV format
baselinr query runs --config config.yml --format csv
```

### Save to File

```bash
# Save JSON output
baselinr query runs --config config.yml --format json --output runs.json

# Save CSV for Excel
baselinr query runs --config config.yml --format csv --output runs.csv
```

### Complex Example

```bash
# Production runs for specific table in last 7 days, save as JSON
baselinr query runs \
  --config config.yml \
  --table customers \
  --schema public \
  --environment production \
  --days 7 \
  --status completed \
  --format json \
  --output prod_runs.json
```

---

## Query Drift Events

### Basic Usage

```bash
# Recent drift events
baselinr query drift --config config.yml
```

### Filter by Table

```bash
# Drift for specific table
baselinr query drift --config config.yml --table orders
```

### Filter by Severity

```bash
# Only high-severity drift
baselinr query drift --config config.yml --severity high

# Medium and high
baselinr query drift --config config.yml --severity medium --days 7
```

### Time-Based Queries

```bash
# Drift in last 24 hours
baselinr query drift --config config.yml --days 1

# Last week's drift
baselinr query drift --config config.yml --days 7
```

### Multiple Filters

```bash
# High-severity drift for specific table in last 3 days
baselinr query drift \
  --config config.yml \
  --table customers \
  --severity high \
  --days 3 \
  --format table
```

### Export for Analysis

```bash
# Export all drift events as CSV
baselinr query drift \
  --config config.yml \
  --days 90 \
  --format csv \
  --output drift_report.csv
```

---

## Query Specific Run

### Get Run Details

```bash
# Full run details
baselinr query run \
  --config config.yml \
  --run-id abc-123-def-456

# JSON output
baselinr query run \
  --config config.yml \
  --run-id abc-123-def-456 \
  --format json

# Save details
baselinr query run \
  --config config.yml \
  --run-id abc-123-def-456 \
  --format json \
  --output run_details.json
```

### Run with Multiple Tables

```bash
# Specify table if run profiled multiple tables
baselinr query run \
  --config config.yml \
  --run-id abc-123-def-456 \
  --table customers
```

**Output Example:**
```
RUN DETAILS
================================================================================
Run ID: abc-123-def-456
Dataset: customers
Schema: public
Profiled: 2024-11-16T10:30:00
Status: completed
Environment: production
Row Count: 1,234,567
Column Count: 15

COLUMN METRICS:

  customer_id (INTEGER):
    null_count: 0
    null_percent: 0.0
    distinct_count: 1234567
    distinct_percent: 100.0

  email (VARCHAR):
    null_count: 123
    null_percent: 0.01
    distinct_count: 1234400
    min_length: 5
    max_length: 128
    avg_length: 24.5
```

---

## Query Table History

### Basic Table History

```bash
# Last 30 days (default)
baselinr query table --config config.yml --table customers

# Last 90 days
baselinr query table \
  --config config.yml \
  --table customers \
  --days 90
```

### With Schema

```bash
# Specific schema
baselinr query table \
  --config config.yml \
  --table orders \
  --schema public
```

### Export History

```bash
# JSON export
baselinr query table \
  --config config.yml \
  --table customers \
  --format json \
  --output customers_history.json

# CSV for charting
baselinr query table \
  --config config.yml \
  --table customers \
  --days 90 \
  --format csv \
  --output customers_90days.csv
```

---

## SQL Query Examples

If you prefer SQL over CLI, here are common patterns.

### Recent Runs

```sql
-- Last 10 runs across all tables
SELECT run_id, dataset_name, profiled_at, status, row_count
FROM baselinr_runs
ORDER BY profiled_at DESC
LIMIT 10;
```

### Table Profiling Frequency

```sql
-- How often each table is profiled
SELECT 
    dataset_name,
    COUNT(*) as run_count,
    MAX(profiled_at) as last_profiled,
    MIN(profiled_at) as first_profiled,
    AVG(row_count) as avg_row_count
FROM baselinr_runs
WHERE profiled_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY dataset_name
ORDER BY run_count DESC;
```

### Failed Runs

```sql
-- All failed runs with details
SELECT 
    run_id,
    dataset_name,
    schema_name,
    profiled_at,
    environment
FROM baselinr_runs
WHERE status = 'failed'
ORDER BY profiled_at DESC;
```

### Row Count Trends

```sql
-- Track row count over time for a table
SELECT 
    profiled_at::DATE as date,
    AVG(row_count) as avg_rows,
    MIN(row_count) as min_rows,
    MAX(row_count) as max_rows
FROM baselinr_runs
WHERE dataset_name = 'customers'
  AND profiled_at > CURRENT_TIMESTAMP - INTERVAL '90 days'
GROUP BY profiled_at::DATE
ORDER BY date;
```

### Metric Trends

```sql
-- Null percentage trend for a column
SELECT 
    profiled_at,
    metric_value::FLOAT as null_percent
FROM baselinr_results
WHERE dataset_name = 'customers'
  AND column_name = 'email'
  AND metric_name = 'null_percent'
ORDER BY profiled_at DESC
LIMIT 30;
```

### Drift Detection

```sql
-- All high-severity drift in last 7 days
SELECT 
    table_name,
    column_name,
    metric_name,
    baseline_value,
    current_value,
    change_percent,
    timestamp
FROM baselinr_events
WHERE event_type = 'drift_detected'
  AND drift_severity = 'high'
  AND timestamp > CURRENT_TIMESTAMP - INTERVAL '7 days'
ORDER BY ABS(change_percent) DESC;
```

### Drift Frequency

```sql
-- Tables with most frequent drift
SELECT 
    table_name,
    COUNT(*) as drift_count,
    COUNT(CASE WHEN drift_severity = 'high' THEN 1 END) as high_severity_count,
    COUNT(CASE WHEN drift_severity = 'medium' THEN 1 END) as medium_severity_count,
    COUNT(CASE WHEN drift_severity = 'low' THEN 1 END) as low_severity_count
FROM baselinr_events
WHERE event_type = 'drift_detected'
  AND timestamp > CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY table_name
ORDER BY drift_count DESC;
```

### Column-Level Analysis

```sql
-- All metrics for a specific column in latest run
SELECT 
    r.run_id,
    r.profiled_at,
    res.column_name,
    res.metric_name,
    res.metric_value
FROM baselinr_runs r
JOIN baselinr_results res 
    ON r.run_id = res.run_id 
    AND r.dataset_name = res.dataset_name
WHERE r.dataset_name = 'customers'
  AND res.column_name = 'email'
ORDER BY r.profiled_at DESC, res.metric_name
LIMIT 100;
```

### Data Quality Metrics

```sql
-- Find columns with high null rates
SELECT 
    r.dataset_name,
    res.column_name,
    res.metric_value::FLOAT as null_percent,
    r.profiled_at
FROM baselinr_runs r
JOIN baselinr_results res 
    ON r.run_id = res.run_id 
    AND r.dataset_name = res.dataset_name
WHERE res.metric_name = 'null_percent'
  AND res.metric_value::FLOAT > 10
  AND r.profiled_at = (
      SELECT MAX(profiled_at) 
      FROM baselinr_runs 
      WHERE dataset_name = r.dataset_name
  )
ORDER BY null_percent DESC;
```

### Cardinality Analysis

```sql
-- Find low-cardinality columns (potential enum candidates)
SELECT 
    r.dataset_name,
    res.column_name,
    res.metric_value::INTEGER as distinct_count,
    r.row_count,
    (res.metric_value::FLOAT / r.row_count * 100) as distinct_percent
FROM baselinr_runs r
JOIN baselinr_results res 
    ON r.run_id = res.run_id 
    AND r.dataset_name = res.dataset_name
WHERE res.metric_name = 'distinct_count'
  AND res.metric_value::INTEGER < 100
  AND r.profiled_at = (
      SELECT MAX(profiled_at) 
      FROM baselinr_runs 
      WHERE dataset_name = r.dataset_name
  )
ORDER BY distinct_count;
```

---

## Programmatic Access (Python)

Use the Baselinr SDK for programmatic queries:

```python
from baselinr.config.loader import ConfigLoader
from baselinr.query import MetadataQueryClient
from baselinr.connectors.factory import create_connector

# Load config
config = ConfigLoader.load_from_file("config.yml")

# Create client
connector = create_connector(config.storage.connection, config.retry)
client = MetadataQueryClient(connector.engine)

# Query runs
runs = client.query_runs(
    table="customers",
    days=7,
    status="completed"
)

for run in runs:
    print(f"{run.run_id}: {run.profiled_at} - {run.row_count} rows")

# Query drift
drift_events = client.query_drift_events(
    table="orders",
    severity="high",
    days=7
)

for event in drift_events:
    print(f"{event.table_name}.{event.column_name}: {event.change_percent}%")

# Get run details
details = client.query_run_details("abc-123-def-456")
print(f"Run: {details['run_id']}")
print(f"Columns: {len(details['columns'])}")

# Table history
history = client.query_table_history("customers", days=30)
print(f"Runs in last 30 days: {history['run_count']}")
```

---

## Dashboard API

Query via REST API (for dashboard integration):

```bash
# Get runs
curl http://localhost:8000/api/runs?table=customers&days=7

# Get drift events
curl http://localhost:8000/api/drift?severity=high&days=7

# Get specific run
curl http://localhost:8000/api/runs/{run_id}

# Get table metrics
curl http://localhost:8000/api/tables/customers/metrics
```

See [Dashboard API Documentation](../dashboard/README.md) for full API reference.

---

## Tips and Tricks

### Combine with jq for JSON Processing

```bash
# Get just run IDs
baselinr query runs --config config.yml --format json | jq -r '.[].run_id'

# Count runs by status
baselinr query runs --config config.yml --format json | jq 'group_by(.status) | map({status: .[0].status, count: length})'

# Extract drift for specific column
baselinr query drift --config config.yml --format json | jq '.[] | select(.column_name == "email")'
```

### Create Reports

```bash
# Weekly drift report
baselinr query drift \
  --config config.yml \
  --days 7 \
  --format csv \
  --output drift_weekly_$(date +%Y%m%d).csv

# Monthly run summary
baselinr query runs \
  --config config.yml \
  --days 30 \
  --format json \
  --output runs_monthly_$(date +%Y%m%d).json
```

### Monitoring Scripts

```bash
#!/bin/bash
# Check for high-severity drift

DRIFT_COUNT=$(baselinr query drift \
  --config config.yml \
  --severity high \
  --days 1 \
  --format json | jq 'length')

if [ "$DRIFT_COUNT" -gt 0 ]; then
    echo "⚠️  $DRIFT_COUNT high-severity drift events in last 24 hours!"
    baselinr query drift --config config.yml --severity high --days 1
    exit 1
fi

echo "✅ No high-severity drift detected"
```

---

## Additional Resources

- [Schema Reference](./SCHEMA_REFERENCE.md) - Full table documentation
- [Migration Guide](./MIGRATION_GUIDE.md) - Schema upgrade procedures
- [CLI Documentation](../README.md) - Complete CLI reference

---

**Questions?** Open an issue on GitHub or check the documentation.
