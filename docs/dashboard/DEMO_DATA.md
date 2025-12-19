# Demo Data for Baselinr Quality Studio

This directory contains pre-generated demo data for the Cloudflare Pages deployment of the Quality Studio.

## Generated Files

### Data Files

- **`runs.json`** (43.3 KB) - 120 profiling runs across multiple warehouses and schemas spanning 60 days
- **`metrics.json`** (172.7 KB) - 582 column-level metrics for successful runs
- **`drift_events.json`** (20.4 KB) - 54 drift detection events with varying severity levels
- **`tables.json`** (33.9 KB) - Metadata for 95 unique tables
- **`validation_results.json`** (61.1 KB) - 156 validation results with ~80% pass rate
- **`lineage.json`** (8.3 KB) - Lineage graph with 16 nodes and 14 edges

### Metadata

- **`metadata.json`** (0.6 KB) - Generation metadata, statistics, and date ranges

## Data Structure

### runs.json
```json
{
  "run_id": "run_xxx",
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

### metrics.json
```json
{
  "run_id": "run_xxx",
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

### drift_events.json
```json
{
  "event_id": "evt_xxx",
  "run_id": "run_xxx",
  "table_name": "customers",
  "column_name": "email",
  "metric_name": "null_percent",
  "baseline_value": 0.15,
  "current_value": 0.45,
  "change_percent": 200.0,
  "severity": "high",
  "timestamp": "2025-12-16T00:00:00+00:00",
  "warehouse_type": "snowflake"
}
```

### tables.json
```json
{
  "table_name": "customers",
  "schema_name": "raw",
  "warehouse_type": "snowflake",
  "last_profiled": "2025-12-16T00:00:00+00:00",
  "row_count": 1000000,
  "column_count": 8,
  "total_runs": 5,
  "drift_count": 2,
  "validation_pass_rate": 0.85,
  "has_recent_drift": true,
  "has_failed_validations": false
}
```

### validation_results.json
```json
{
  "id": 1,
  "run_id": "run_xxx",
  "table_name": "customers",
  "schema_name": "raw",
  "column_name": "email",
  "rule_type": "format",
  "passed": false,
  "failure_reason": "Found 50 values not matching expected format in email",
  "total_rows": 1000000,
  "failed_rows": 50,
  "failure_rate": 0.00005,
  "severity": "medium",
  "validated_at": "2025-12-16T00:00:00+00:00"
}
```

### lineage.json
```json
{
  "nodes": [
    {
      "id": "raw.customers",
      "type": "table",
      "label": "raw.customers",
      "schema": "raw",
      "table": "customers",
      "database": null,
      "metadata": {
        "warehouse_type": "snowflake",
        "row_count": 1000000,
        "column_count": 8
      }
    }
  ],
  "edges": [
    {
      "source": "raw.customers",
      "target": "staging.customers",
      "relationship_type": "derives_from",
      "confidence": 0.95,
      "transformation": null,
      "provider": "manual",
      "metadata": {}
    }
  ],
  "root_id": null,
  "direction": "both"
}
```

## Statistics

- **Date Range**: 60 days (Oct 17, 2025 - Dec 16, 2025)
- **Warehouses**: Snowflake, BigQuery, PostgreSQL, Redshift
- **Schemas**: raw, staging, analytics, production
- **Total Data Size**: ~340 KB (all JSON files combined)

## Regenerating Data

To regenerate the demo data:

```bash
cd dashboard/backend
python generate_demo_data.py
```

This will:
1. Generate new profiling runs, metrics, and events
2. Validate data consistency
3. Export to JSON files in this directory
4. Update metadata.json with generation timestamp

## Data Characteristics

- **Runs**: Mix of completed (65%), success (20%), failed (10%), and running (5%) statuses
- **Drift Events**: ~30% of successful runs have drift, with 50% low, 35% medium, 15% high severity
- **Validations**: ~80% pass rate across 6 rule types (not_null, unique, range, format, enum, referential)
- **Lineage**: Realistic data pipeline (raw → staging → analytics/production)
- **Metrics**: Realistic distributions based on column types (IDs have 0% nulls, emails have &lt;3% nulls, etc.)

## Usage in Demo

These files are loaded by the demo data service (`demo_data.py`) and served through Cloudflare Pages Functions to provide a fully functional demo of the Quality Studio without requiring a database backend.

