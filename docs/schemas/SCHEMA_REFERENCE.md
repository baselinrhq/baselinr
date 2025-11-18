# Baselinr Storage Schema Reference

**Version:** 1.0  
**Last Updated:** 2024-11-16  
**Status:** Production Ready

## Overview

Baselinr stores profiling results, run metadata, drift events, and incremental state in five core tables. All tables use a consistent naming convention (`baselinr_*`) and are designed for multi-tenant, multi-warehouse deployments.

### Schema Philosophy

- **Immutable History**: Profiling results are never updated, only inserted
- **Composite Keys**: Support multiple tables per profiling run
- **Flexible Metadata**: TEXT/VARIANT columns for extensibility
- **Query Optimization**: Indexes designed for common access patterns

---

## Core Tables

### 1. baselinr_schema_version

**Purpose:** Tracks schema version for migration management and compatibility checking.

**Schema:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| version | INTEGER | PRIMARY KEY | Schema version number (sequential) |
| applied_at | TIMESTAMP | NOT NULL | When migration was applied |
| description | VARCHAR(500) | NULL | Human-readable description |
| migration_script | VARCHAR(255) | NULL | Migration file name |
| checksum | VARCHAR(64) | NULL | Optional integrity check |

**Indexes:** None (small table, PK sufficient)

**Use Cases:**
- Check current schema version on startup
- Track migration history
- Ensure code/database compatibility

**Example Queries:**

```sql
-- Get current schema version
SELECT version, description, applied_at 
FROM baselinr_schema_version 
ORDER BY version DESC 
LIMIT 1;

-- View migration history
SELECT * FROM baselinr_schema_version 
ORDER BY version;
```

---

### 2. baselinr_runs

**Purpose:** Tracks metadata for each profiling run, including execution time, row counts, and status.

**Schema:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| run_id | VARCHAR(36) | PRIMARY KEY | UUID identifying the profiling run |
| dataset_name | VARCHAR(255) | PRIMARY KEY | Table name that was profiled |
| schema_name | VARCHAR(255) | NULL | Schema/database name |
| profiled_at | TIMESTAMP | NOT NULL | When profiling executed |
| environment | VARCHAR(50) | NULL | Environment (dev/staging/prod) |
| status | VARCHAR(20) | NULL | Run status (completed/failed) |
| row_count | INTEGER | NULL | Number of rows profiled |
| column_count | INTEGER | NULL | Number of columns profiled |

**Composite Primary Key:** (run_id, dataset_name)  
*Rationale:* Allows multiple tables to be profiled in a single run while maintaining unique records per table.

**Indexes:**
- `idx_dataset_profiled` on (dataset_name, profiled_at DESC) - Optimizes historical queries per table

**Use Cases:**
- Query run history for a specific table
- Track profiling frequency and status
- Identify failed runs
- Power dashboard overview
- Filter by environment for multi-env deployments

**Example Queries:**

```sql
-- Get last 10 runs for a table
SELECT run_id, profiled_at, status, row_count 
FROM baselinr_runs 
WHERE dataset_name = 'customers' 
ORDER BY profiled_at DESC 
LIMIT 10;

-- Find failed runs in last 7 days
SELECT * FROM baselinr_runs 
WHERE status = 'failed' 
  AND profiled_at > CURRENT_TIMESTAMP - INTERVAL '7 days';

-- Count runs by environment
SELECT environment, COUNT(*) as run_count
FROM baselinr_runs
WHERE profiled_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY environment;
```

---

### 3. baselinr_results

**Purpose:** Stores individual column-level metrics for each profiling run.

**Schema:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique metric record ID |
| run_id | VARCHAR(36) | NOT NULL | References baselinr_runs |
| dataset_name | VARCHAR(255) | NOT NULL | Table name |
| schema_name | VARCHAR(255) | NULL | Schema name |
| column_name | VARCHAR(255) | NOT NULL | Column that was profiled |
| column_type | VARCHAR(100) | NULL | Column data type |
| metric_name | VARCHAR(100) | NOT NULL | Metric identifier (e.g., "null_count") |
| metric_value | TEXT | NULL | Metric value as string |
| profiled_at | TIMESTAMP | NOT NULL | When metric was captured |

**Foreign Key:** (run_id, dataset_name) → baselinr_runs(run_id, dataset_name)

**Indexes:**
- `idx_run_id` on (run_id) - Fast lookup by run
- `idx_dataset_column` on (dataset_name, column_name) - Column history queries
- `idx_metric` on (dataset_name, column_name, metric_name) - Specific metric trends

**Metric Names (Standard):**
- `null_count`, `null_percent` - Null value statistics
- `distinct_count`, `distinct_percent` - Cardinality
- `min_value`, `max_value` - Range
- `mean`, `stddev` - Statistical moments
- `histogram` - Distribution (JSON string)
- `min_length`, `max_length`, `avg_length` - String statistics

**Use Cases:**
- Retrieve all metrics for a run
- Track metric trends over time
- Compare metrics across runs
- Detect drift in specific metrics

**Example Queries:**

```sql
-- Get all metrics for a run
SELECT column_name, metric_name, metric_value 
FROM baselinr_results 
WHERE run_id = 'abc-123-def-456'
ORDER BY column_name, metric_name;

-- Track null_percent trend for a column
SELECT profiled_at, metric_value::FLOAT as null_percent
FROM baselinr_results
WHERE dataset_name = 'customers'
  AND column_name = 'email'
  AND metric_name = 'null_percent'
ORDER BY profiled_at DESC
LIMIT 30;

-- Find columns with high null rates
SELECT DISTINCT column_name, metric_value::FLOAT as null_percent
FROM baselinr_results
WHERE dataset_name = 'orders'
  AND metric_name = 'null_percent'
  AND metric_value::FLOAT > 10
ORDER BY null_percent DESC;
```

---

### 4. baselinr_events

**Purpose:** Stores drift detection alerts and other profiling events for historical tracking and analysis.

**Schema:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| event_id | VARCHAR(36) | PRIMARY KEY | Unique event identifier (UUID) |
| event_type | VARCHAR(100) | NOT NULL | Event type (e.g., "drift_detected") |
| table_name | VARCHAR(255) | NULL | Affected table |
| column_name | VARCHAR(255) | NULL | Affected column |
| metric_name | VARCHAR(100) | NULL | Affected metric |
| baseline_value | FLOAT | NULL | Previous/baseline value |
| current_value | FLOAT | NULL | New/current value |
| change_percent | FLOAT | NULL | Percentage change |
| drift_severity | VARCHAR(20) | NULL | Severity (low/medium/high) |
| timestamp | TIMESTAMP | NOT NULL | When event occurred |
| metadata | TEXT/VARIANT | NULL | Additional context (JSON) |
| created_at | TIMESTAMP | DEFAULT NOW | Record creation time |

**Indexes:**
- `idx_event_type` on (event_type) - Filter by event type
- `idx_table_name` on (table_name) - Table-specific events
- `idx_timestamp` on (timestamp DESC) - Recent events
- `idx_drift_severity` on (drift_severity) - High-priority alerts

**Event Types:**
- `drift_detected` - Metric drift alert
- `schema_change` - Table schema modification
- `profiling_failure` - Failed profiling attempt
- `data_quality_issue` - Quality check failure

**Use Cases:**
- Query recent drift events
- Alert on high-severity issues
- Audit trail for data changes
- Drift detection history

**Example Queries:**

```sql
-- Recent high-severity drift events
SELECT table_name, column_name, metric_name, 
       change_percent, timestamp
FROM baselinr_events
WHERE drift_severity = 'high'
  AND timestamp > CURRENT_TIMESTAMP - INTERVAL '7 days'
ORDER BY timestamp DESC;

-- Drift frequency by table
SELECT table_name, COUNT(*) as drift_count
FROM baselinr_events
WHERE event_type = 'drift_detected'
  AND timestamp > CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY table_name
ORDER BY drift_count DESC;

-- All events for a specific column
SELECT event_type, drift_severity, change_percent, timestamp
FROM baselinr_events
WHERE table_name = 'orders'
  AND column_name = 'total_amount'
ORDER BY timestamp DESC;
```

---

### 5. baselinr_table_state

**Purpose:** Tracks incremental profiling state per table for change detection and cost optimization.

**Schema:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| schema_name | VARCHAR(255) | PRIMARY KEY | Schema name |
| table_name | VARCHAR(255) | PRIMARY KEY | Table name |
| last_run_id | VARCHAR(36) | NULL | Most recent run ID |
| snapshot_id | VARCHAR(255) | NULL | Change tracking snapshot |
| change_token | VARCHAR(255) | NULL | Change detection token |
| decision | VARCHAR(50) | NULL | Profiling decision (full/partial/skip) |
| decision_reason | VARCHAR(255) | NULL | Why decision was made |
| last_profiled_at | TIMESTAMP | NULL | Last profiling time |
| staleness_score | INTEGER | NULL | How stale the profile is |
| row_count | BIGINT | NULL | Last known row count |
| bytes_scanned | BIGINT | NULL | Bytes scanned in last run |
| metadata | TEXT/VARIANT | NULL | Additional state (JSON) |

**Composite Primary Key:** (schema_name, table_name)

**Indexes:** None (small table, accessed by PK)

**Use Cases:**
- Incremental profiling decisions
- Cost tracking and optimization
- Detect unchanged tables (skip profiling)
- Profile freshness monitoring

**Example Queries:**

```sql
-- Find stale tables (not profiled in 7+ days)
SELECT table_name, last_profiled_at, 
       CURRENT_TIMESTAMP - last_profiled_at as staleness
FROM baselinr_table_state
WHERE last_profiled_at < CURRENT_TIMESTAMP - INTERVAL '7 days'
ORDER BY staleness DESC;

-- Total bytes scanned by schema
SELECT schema_name, SUM(bytes_scanned) as total_bytes
FROM baselinr_table_state
GROUP BY schema_name;

-- Tables profiled today
SELECT table_name, decision, decision_reason
FROM baselinr_table_state
WHERE last_profiled_at > CURRENT_DATE;
```

---

## Schema Versioning

### Current Version: 1

Baselinr uses integer versioning starting at 1. The `baselinr_schema_version` table tracks all applied migrations.

### Versioning Policy

**Version Increments When:**
- Adding required columns (breaking)
- Removing columns (breaking)
- Renaming columns (breaking)
- Changing column types (breaking)
- Modifying primary keys (breaking)

**Version DOES NOT Increment When:**
- Adding nullable/optional columns
- Adding indexes
- Adding new tables
- Expanding column sizes
- Adding comments

### Compatibility

Baselinr supports **N-1 compatibility** (code can read one version behind):
- **Current Version:** Code reads and writes v1
- **Supported Reading:** Code can read v1 (no previous versions yet)
- **Migration Required:** Warning shown if DB version ≠ code version

### Version History

| Version | Date | Description | Breaking |
|---------|------|-------------|----------|
| 1 | 2024-11-16 | Initial schema with all core tables | No |

---

## Database-Specific Notes

### PostgreSQL
- Uses `SERIAL` for auto-increment
- `TIMESTAMP` for datetime
- `TEXT` for flexible metadata

### Snowflake
- Uses `AUTOINCREMENT` for auto-increment
- `TIMESTAMP_NTZ` (no timezone) for datetime
- `VARIANT` for structured metadata (JSON)

### MySQL
- Uses `AUTO_INCREMENT` for auto-increment
- `DATETIME` for datetime
- `TEXT` for flexible metadata

### SQLite
- Uses `INTEGER PRIMARY KEY` for auto-increment
- `TEXT` for datetime (ISO8601 strings)
- `TEXT` for flexible metadata

---

## Query Performance Optimization

### Index Usage Guidelines

1. **Time-based queries**: Always use indexed timestamp columns
2. **Table lookups**: Use `dataset_name` in WHERE clause
3. **Column history**: Include both `dataset_name` and `column_name`
4. **Pagination**: Use LIMIT/OFFSET with ORDER BY

### Query Best Practices

```sql
-- ✅ GOOD: Uses index
SELECT * FROM baselinr_runs 
WHERE dataset_name = 'customers' 
ORDER BY profiled_at DESC 
LIMIT 10;

-- ❌ BAD: No index on status alone
SELECT * FROM baselinr_runs 
WHERE status = 'completed';

-- ✅ BETTER: Combine with indexed column
SELECT * FROM baselinr_runs 
WHERE dataset_name = 'customers' 
  AND status = 'completed'
ORDER BY profiled_at DESC;
```

---

## Migration Management

See [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) for:
- Creating new migrations
- Testing migrations
- Rolling back changes
- Version upgrade procedures

---

## Security Considerations

1. **Access Control**: Restrict write access to Baselinr service account only
2. **Read Access**: Grant read-only access to dashboard/query users
3. **Sensitive Data**: Metric values stored as strings—avoid storing PII
4. **Audit Trail**: All events logged in `baselinr_events`

---

## Maintenance

### Recommended Practices

1. **Retention Policy**: Archive runs older than 90 days
2. **Index Maintenance**: Rebuild indexes monthly
3. **Vacuum/Analyze**: Run weekly (PostgreSQL)
4. **Monitor Growth**: Track table sizes

### Cleanup Queries

```sql
-- Archive old runs (example)
DELETE FROM baselinr_results 
WHERE profiled_at < CURRENT_TIMESTAMP - INTERVAL '90 days';

DELETE FROM baselinr_runs 
WHERE profiled_at < CURRENT_TIMESTAMP - INTERVAL '90 days';

-- Archive old events
DELETE FROM baselinr_events 
WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '365 days';
```

---

## Additional Resources

- [Migration Guide](./MIGRATION_GUIDE.md) - Schema upgrade procedures
- [Query Examples](./QUERY_EXAMPLES.md) - Common query patterns
- [API Documentation](../dashboard/README.md) - REST API reference

---

**Maintained by:** Baselinr Team  
**Questions?** Open an issue on GitHub
