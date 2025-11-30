# Data Lineage Guide

Baselinr provides comprehensive data lineage tracking to help you understand data dependencies and perform root cause analysis when drift is detected.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Lineage Providers](#lineage-providers)
- [Configuration](#configuration)
- [CLI Usage](#cli-usage)
- [Python SDK Usage](#python-sdk-usage)
- [Use Cases](#use-cases)
- [Best Practices](#best-practices)

## Overview

Data lineage in Baselinr tracks relationships between tables, enabling you to:

- **Root Cause Analysis**: When drift is detected, traverse upstream to find the source of changes
- **Impact Analysis**: Understand which downstream tables are affected by changes to upstream sources
- **Intelligent Alert Grouping**: Group related drift events by their lineage relationships
- **LLM Context**: Provide lineage information to LLMs for better explanations and recommendations

Baselinr uses a provider-based architecture that supports multiple lineage sources:

- **dbt Manifest**: Extract lineage from dbt `manifest.json` files
- **SQL Parser**: Parse SQL queries and view definitions using SQLGlot
- **Query History**: Extract lineage from warehouse query execution history (Snowflake, BigQuery, PostgreSQL, Redshift, MySQL)
- **Dagster**: Extract lineage from Dagster assets using metadata database, code scanning, or GraphQL API

## Quick Start

### Enable Lineage Extraction

Add lineage configuration to your `config.yml`:

```yaml
profiling:
  extract_lineage: true

lineage:
  enabled: true
  providers:
    - name: dbt_manifest
      enabled: true
      config:
        manifest_path: "target/manifest.json"  # Optional, auto-detects if not specified
    - name: sql_parser
      enabled: true
```

### Extract Lineage During Profiling

Lineage is automatically extracted when you profile tables:

```bash
baselinr profile --config config.yml
```

### Query Lineage

```bash
# Get upstream dependencies
baselinr lineage upstream --config config.yml --table customers

# Get downstream dependencies
baselinr lineage downstream --config config.yml --table raw_events

# Find path between two tables
baselinr lineage path --config config.yml --from raw.events --to analytics.revenue

# List available providers
baselinr lineage providers --config config.yml

# Sync lineage from query history (bulk operation)
baselinr lineage sync --config config.yml --provider postgres_query_history

# Sync all query history providers
baselinr lineage sync --config config.yml --all

# Clean up stale lineage edges
baselinr lineage cleanup --config config.yml --provider postgres_query_history
```

## Lineage Providers

### dbt Manifest Provider

The dbt provider extracts lineage from dbt's `manifest.json` file, which contains complete dependency information for all models and sources.

**Configuration:**

```yaml
lineage:
  providers:
    - name: dbt_manifest
      enabled: true
      config:
        manifest_path: "target/manifest.json"  # Optional
        project_path: "."  # Optional, for auto-detection
```

**How it works:**

- Reads dbt `manifest.json` after `dbt compile` or `dbt run`
- Extracts `ref()` and `source()` dependencies
- Maps dbt models to database tables using your dbt project configuration
- Provides high-confidence lineage (confidence_score: 1.0)

**Requirements:**

- dbt project must be compiled (`dbt compile` or `dbt run`)
- `manifest.json` must be accessible
- Install with: `pip install baselinr[dbt]`

### SQL Parser Provider

The SQL parser provider extracts table references from SQL queries using SQLGlot.

**Configuration:**

```yaml
lineage:
  providers:
    - name: sql_parser
      enabled: true
```

**How it works:**

- Parses SQL queries to extract table references
- Currently supports explicit SQL parsing (future: view definitions, query history)
- Provides medium-confidence lineage (confidence_score: 0.8)

**Requirements:**

- SQLGlot library (included in baselinr dependencies)

**Limitations:**

- Requires SQL to be provided explicitly
- View definition parsing requires database access
- Complex SQL with dynamic table names may not be fully parsed

### Query History Providers

Query history providers extract lineage from actual query execution history in your warehouse. This captures real-world data dependencies based on queries that have been executed, complementing dbt and SQL parsing providers.

**Supported Warehouses:**

- **PostgreSQL**: Uses `pg_stat_statements` extension
- **Snowflake**: Uses `SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY`
- **BigQuery**: Uses `INFORMATION_SCHEMA.JOBS_BY_PROJECT`
- **Redshift**: Uses `STL_QUERY` and `STL_SCAN` tables
- **MySQL**: Uses `performance_schema.events_statements_history_long`

**Configuration:**

```yaml
lineage:
  enabled: true
  providers: [dbt, sql_parser, postgres_query_history]
  query_history:
    enabled: true
    incremental: true  # Enable incremental updates during profiling
    lookback_days: 30  # Days of history for bulk sync
    min_query_count: 2  # Minimum queries to establish relationship
    exclude_patterns:
      - ".*INFORMATION_SCHEMA.*"
      - ".*SHOW.*"
    edge_expiration_days: 90  # Auto-cleanup edges not seen for 90+ days (None = never)
    warn_stale_days: 90  # Warn about edges not seen for 90+ days
    postgres:
      require_extension: true  # Fail if pg_stat_statements not installed
    snowflake:
      use_account_usage: true
    bigquery:
      region: "us"
```

**How it works:**

1. **Initial Bulk Sync**: Run `baselinr lineage sync` to populate lineage from query history (last 30 days by default)
2. **Incremental Updates**: During profiling, query history providers automatically extract new lineage from queries executed since the last sync
3. **Staleness Detection**: System warns about edges not seen in query history for extended periods
4. **Cleanup**: Optionally remove stale edges that haven't been observed recently

**Workflow:**

```bash
# Initial setup: Bulk sync lineage from query history
baselinr lineage sync --provider postgres_query_history

# Regular profiling: Automatically updates lineage incrementally
baselinr profile --config config.yml

# Periodic refresh: Re-sync to catch any missed queries
baselinr lineage sync --provider postgres_query_history

# Cleanup stale edges
baselinr lineage cleanup --provider postgres_query_history
```

**Requirements:**

- **PostgreSQL**: Requires `CREATE EXTENSION pg_stat_statements;` (run by DBA)
- **Snowflake**: Requires `ACCOUNTADMIN` role or access to `SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY`
- **BigQuery**: Requires `bigquery.jobs.listAll` permission
- **Redshift**: Requires appropriate IAM permissions for `STL_QUERY` access
- **MySQL**: Requires `performance_schema = ON` in MySQL configuration

**Benefits:**

- Captures real-world dependencies from actual query execution
- High confidence (0.95) since based on executed queries
- Automatic incremental updates during profiling
- Complements dbt/SQL parsing by capturing ad-hoc queries

**Limitations:**

- Query history may have latency (Snowflake ACCESS_HISTORY can lag by hours)
- Data retention varies by warehouse (Redshift: 2-5 days, others: longer)
- Requires appropriate permissions/extensions
- PostgreSQL `pg_stat_statements` doesn't track individual query timestamps (aggregate stats only)

### Dagster Provider

The Dagster provider extracts lineage from Dagster assets using multiple data sources with intelligent fallback logic. It supports both table-level and column-level lineage extraction.

**Data Sources (in priority order):**

1. **Metadata Database**: Query Dagster's metadata database (PostgreSQL/SQLite) for asset dependencies and materialization events
2. **Code Scanning**: Scan Python files for `@asset` decorators and extract dependencies from AST
3. **GraphQL API**: Query Dagster's GraphQL API for asset lineage information

**Configuration:**

```yaml
lineage:
  enabled: true
  extract_column_lineage: true
  providers: [dbt, sql_parser, dagster]
  dagster:
    # Option 1: Metadata database (recommended for production)
    metadata_db_url: "postgresql://user:pass@localhost:5432/dagster"
    auto_detect_metadata_db: true  # Auto-detect from DAGSTER_POSTGRES_URL env var
    
    # Option 2: Code scanning (works without Dagster running)
    code_locations:
      - "dagster_definitions/"
      - "src/assets/"
    
    # Option 3: GraphQL API (requires Dagster UI running)
    graphql_url: "http://localhost:3000/graphql"
    
    # Optional: Explicit asset-to-table mapping
    asset_table_mapping:
      "schema::table_name": ["schema", "table_name"]
      "my_asset": ["public", "my_table"]
```

**How it works:**

1. **Metadata Database**: Queries `event_log_entries` table for asset dependencies and materialization events. Extracts column-level lineage from `MaterializeResult` metadata.
2. **Code Scanning**: Parses Python files to find `@asset` decorators, extracts `deps` parameters, and maps assets to tables using naming conventions or metadata.
3. **GraphQL API**: Queries Dagster's GraphQL endpoint for asset dependencies and metadata.

**Asset-to-Table Mapping:**

The provider uses multiple strategies to map Dagster assets to database tables:

1. **Explicit Mapping**: Use `asset_table_mapping` in config for precise control
2. **Metadata-based**: Check asset metadata for `table`, `schema`, `database` keys
3. **Naming Convention**: Parse AssetKey segments (e.g., `AssetKey(["schema", "table"])` → `schema.table`)
4. **Fallback**: If no mapping found, skip lineage extraction for that asset

**Column-Level Lineage:**

Dagster supports column-level lineage via `MaterializeResult` metadata:

```python
from dagster import asset, MaterializeResult, TableColumnLineage, TableColumnDep, AssetKey

@asset
def my_asset():
    yield MaterializeResult(
        metadata={
            "dagster/column_lineage": TableColumnLineage(
                deps_by_column={
                    "output_col": [
                        TableColumnDep(
                            asset_key=AssetKey("source"),
                            column_name="source_col"
                        )
                    ]
                }
            )
        }
    )
```

The provider extracts this metadata from:
- Latest materialization events in metadata DB
- Code analysis (if MaterializeResult is returned)
- GraphQL API asset metadata

**Requirements:**

- Install with: `pip install baselinr[dagster]`
- For metadata DB: Access to Dagster's metadata database
- For code scanning: Read access to Python files with asset definitions
- For GraphQL API: Dagster UI must be running and accessible

**Benefits:**

- Captures lineage from Dagster's first-class asset model
- Supports multiple data sources with automatic fallback
- High confidence (1.0) for metadata DB and GraphQL sources
- Medium confidence (0.9) for code scanning
- Supports column-level lineage when available

**Limitations:**

- Code scanning may miss dynamic dependencies
- GraphQL API requires Dagster UI to be running
- Metadata DB requires appropriate database permissions
- Asset-to-table mapping may need manual configuration for complex setups

## Configuration

### Full Configuration Example

```yaml
profiling:
  extract_lineage: true  # Enable lineage extraction during profiling

lineage:
  enabled: true
  providers: [dbt, sql_parser, postgres_query_history]
  
  # dbt provider configuration
  dbt:
    manifest_path: "target/manifest.json"
  
  # Query history provider configuration
  query_history:
    enabled: true
    incremental: true  # Enable incremental updates during profiling
    lookback_days: 30  # Days of history for bulk sync
    min_query_count: 2  # Minimum queries to establish relationship
    exclude_patterns:
      - ".*INFORMATION_SCHEMA.*"
      - ".*SHOW.*"
      - ".*pg_stat.*"
    edge_expiration_days: 90  # Auto-cleanup edges not seen for 90+ days (None = never)
    warn_stale_days: 90  # Warn about edges not seen for 90+ days
    
    # Warehouse-specific configs
    postgres:
      require_extension: true  # Fail if pg_stat_statements not installed
    snowflake:
      use_account_usage: true
    bigquery:
      region: "us"
```

### Provider-Specific Configuration

Each provider can have its own configuration:

```yaml
lineage:
  providers:
    - name: dbt_manifest
      enabled: true
      config:
        manifest_path: "/path/to/manifest.json"
        project_path: "/path/to/dbt/project"
    
    - name: sql_parser
      enabled: true
      config:
        # Future: SQL parser-specific options
```

## CLI Usage

### Upstream Dependencies

Get all upstream tables that feed into a table:

```bash
# Basic usage
baselinr lineage upstream --config config.yml --table customers

# With schema
baselinr lineage upstream --config config.yml --table customers --schema public

# Limit depth
baselinr lineage upstream --config config.yml --table analytics.revenue --max-depth 2

# JSON output
baselinr lineage upstream --config config.yml --table customers --format json

# Save to file
baselinr lineage upstream --config config.yml --table customers --output upstream.json
```

**Output Example:**

```
Upstream Lineage: customers
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Schema     ┃ Table               ┃ Depth ┃ Provider   ┃ Type                ┃ Confidence   ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ raw        │ events              │ 1     │ dbt_manifest│ dbt_ref             │ 1.00         │
│ raw        │ users               │ 1     │ dbt_manifest│ dbt_ref             │ 1.00         │
│ staging    │ events_enriched     │ 2     │ dbt_manifest│ dbt_ref             │ 1.00         │
└────────────┴─────────────────────┴───────┴────────────┴─────────────────────┴──────────────┘
```

### Downstream Dependencies

Get all downstream tables that depend on a table:

```bash
baselinr lineage downstream --config config.yml --table raw.events

# With max depth
baselinr lineage downstream --config config.yml --table raw.events --max-depth 3
```

### Find Path Between Tables

Find if there's a dependency path between two tables:

```bash
baselinr lineage path \
  --config config.yml \
  --from raw.events \
  --to analytics.revenue

# With max depth
baselinr lineage path \
  --config config.yml \
  --from raw.events \
  --to analytics.revenue \
  --max-depth 5
```

**Output Example:**

```
Lineage Path: raw.events → analytics.revenue
┏━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ Step  ┃ Schema     ┃ Table              ┃
┡━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ 1     │ raw        │ events             │
│ 2     │ staging    │ events_enriched    │
│ 3     │ analytics  │ revenue            │
└───────┴────────────┴────────────────────┘
```

### List Providers

Check which lineage providers are available:

```bash
baselinr lineage providers --config config.yml
```

**Output Example:**

```
Lineage Providers
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ Provider       ┃ Status             ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ dbt_manifest   │ Available          │
│ sql_parser     │ Available          │
│ postgres_query_history │ Available  │
└────────────────┴────────────────────┘
```

### Sync Query History Lineage

Sync lineage from warehouse query history (bulk operation):

```bash
# Sync specific provider
baselinr lineage sync --config config.yml --provider postgres_query_history

# Sync all query history providers
baselinr lineage sync --config config.yml --all

# Override lookback days
baselinr lineage sync --config config.yml --provider snowflake_query_history --lookback-days 60

# Dry run (show what would be extracted)
baselinr lineage sync --config config.yml --provider postgres_query_history --dry-run

# Force full resync (ignore last sync timestamp)
baselinr lineage sync --config config.yml --provider postgres_query_history --force
```

**Output Example:**

```
Syncing lineage from postgres_query_history...
  Extracted 142 lineage edges

Sync complete: 142 edges extracted
```

### Cleanup Stale Lineage Edges

Remove lineage edges that haven't been seen in query history for extended periods:

```bash
# Clean up stale edges (uses edge_expiration_days from config)
baselinr lineage cleanup --config config.yml --provider postgres_query_history

# Override expiration days
baselinr lineage cleanup --config config.yml --provider postgres_query_history --expiration-days 60

# Dry run (show what would be deleted)
baselinr lineage cleanup --config config.yml --provider postgres_query_history --dry-run
```

**Output Example:**

```
Cleaned up 23 stale edges
```

## Python SDK Usage

### Get Upstream Lineage

```python
from baselinr import BaselinrClient

client = BaselinrClient(config_path="config.yml")

# Get upstream dependencies
upstream = client.get_upstream_lineage(
    table="customers",
    schema="public",
    max_depth=3
)

for dep in upstream:
    print(f"{dep['schema']}.{dep['table']} (depth: {dep['depth']})")
    print(f"  Provider: {dep['provider']}")
    print(f"  Confidence: {dep['confidence_score']}")
```

### Get Downstream Lineage

```python
# Get downstream dependencies
downstream = client.get_downstream_lineage(
    table="raw_events",
    schema="raw",
    max_depth=2
)

for dep in downstream:
    print(f"{dep['schema']}.{dep['table']} depends on raw_events")
```

### Find Lineage Path

```python
# Find path between two tables
path = client.get_lineage_path(
    from_table=("raw", "events"),
    to_table=("analytics", "revenue"),
    max_depth=5
)

if path:
    print("Path found:")
    for step in path:
        print(f"  {step['schema']}.{step['table']}")
else:
    print("No path found")
```

### Get All Lineage

```python
# Get all lineage edges
all_lineage = client.get_all_lineage()

for edge in all_lineage:
    print(f"{edge['upstream_schema']}.{edge['upstream_table']} → "
          f"{edge['downstream_schema']}.{edge['downstream_table']}")
```

### Check Available Providers

```python
# Get available lineage providers
providers = client.get_available_lineage_providers()

for provider in providers:
    print(f"{provider['name']}: {provider['available']}")
```

## Use Cases

### Root Cause Analysis

When drift is detected, trace upstream to find the source:

```python
from baselinr import BaselinrClient

client = BaselinrClient(config_path="config.yml")

# Detect drift
drift_report = client.detect_drift(
    dataset_name="analytics.revenue",
    baseline_run_id="baseline-run-id",
    current_run_id="current-run-id"
)

if drift_report.summary["total_drifts"] > 0:
    # Get upstream dependencies
    upstream = client.get_upstream_lineage(
        table="revenue",
        schema="analytics"
    )
    
    print("Upstream tables to investigate:")
    for dep in upstream:
        print(f"  - {dep['schema']}.{dep['table']}")
```

### Impact Analysis

Understand which tables are affected by changes:

```python
# Check what depends on a table you're about to modify
downstream = client.get_downstream_lineage(
    table="raw_events",
    schema="raw"
)

print(f"Warning: {len(downstream)} tables depend on raw.events")
for dep in downstream:
    print(f"  - {dep['schema']}.{dep['table']}")
```

### Intelligent Alert Grouping

Group related drift events by lineage:

```python
# Get all drift events
drift_events = client.query_drift_events(days=7)

# Group by lineage relationships
lineage_groups = {}
for event in drift_events:
    upstream = client.get_upstream_lineage(
        table=event.table_name,
        schema=event.schema_name
    )
    
    # Group events that share upstream dependencies
    for dep in upstream:
        key = f"{dep['schema']}.{dep['table']}"
        if key not in lineage_groups:
            lineage_groups[key] = []
        lineage_groups[key].append(event)

# Report grouped alerts
for upstream_table, events in lineage_groups.items():
    if len(events) > 1:
        print(f"Root cause: {upstream_table}")
        print(f"  Affected {len(events)} downstream tables")
```

## Best Practices

### 1. Enable Multiple Providers

Use multiple providers for comprehensive coverage:

```yaml
lineage:
  enabled: true
  providers: [dbt, sql_parser, postgres_query_history]
  query_history:
    enabled: true
    incremental: true
```

This combination provides:
- **dbt**: High-confidence lineage from dbt models
- **sql_parser**: Lineage from view definitions and explicit SQL
- **query_history**: Real-world dependencies from executed queries

### 2. Keep dbt Manifest Updated

If using dbt, ensure manifest is up to date:

```bash
# Before profiling, compile dbt
dbt compile

# Or run dbt (which also compiles)
dbt run
```

### 3. Use Confidence Scores

Filter lineage by confidence when needed:

```python
# Only use high-confidence lineage
upstream = client.get_upstream_lineage(table="customers")
high_confidence = [d for d in upstream if d['confidence_score'] >= 0.9]
```

### 4. Limit Depth for Performance

Use `max_depth` to limit traversal:

```python
# Only go 2 levels deep
upstream = client.get_upstream_lineage(
    table="customers",
    max_depth=2
)
```

### 5. Combine with Drift Detection

Use lineage for root cause analysis:

```python
# When drift detected, check upstream
drift = client.detect_drift(...)
if drift.summary["total_drifts"] > 0:
    upstream = client.get_upstream_lineage(
        table=drift.dataset_name
    )
    # Investigate upstream tables
```

## Troubleshooting

### No Lineage Extracted

**Problem**: `baselinr lineage upstream` returns no results.

**Solutions**:
1. Check if lineage extraction is enabled: `profiling.extract_lineage: true`
2. Verify providers are available: `baselinr lineage providers`
3. For dbt: Ensure `manifest.json` exists and is accessible
4. Check logs for extraction errors

### Provider Not Available

**Problem**: Provider shows as "Unavailable" in `baselinr lineage providers`.

**Solutions**:
1. **dbt_manifest**: Ensure dbt is installed and manifest.json exists
2. **sql_parser**: SQLGlot should be installed automatically with baselinr
3. **postgres_query_history**: Ensure `pg_stat_statements` extension is installed (`CREATE EXTENSION pg_stat_statements;`)
4. **snowflake_query_history**: Ensure `ACCOUNTADMIN` role or access to `SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY`
5. **bigquery_query_history**: Ensure `bigquery.jobs.listAll` permission
6. **redshift_query_history**: Ensure appropriate IAM permissions for `STL_QUERY` access
7. **mysql_query_history**: Ensure `performance_schema = ON` in MySQL configuration
8. Check provider-specific requirements in logs

### Incomplete Lineage

**Problem**: Lineage graph is incomplete or missing relationships.

**Solutions**:
1. Enable multiple providers for better coverage (dbt + sql_parser + query_history)
2. For dbt: Ensure all models are compiled
3. For SQL parser: Provide explicit SQL when possible
4. For query history: Run initial bulk sync: `baselinr lineage sync --all`
5. Check confidence scores - low confidence may indicate parsing issues
6. Query history captures real-world usage but may miss rarely-executed queries

### 6. Use Query History for Real-World Dependencies

Query history providers capture dependencies from actual query execution:

```bash
# Initial bulk sync
baselinr lineage sync --provider postgres_query_history

# Regular profiling automatically updates incrementally
baselinr profile --config config.yml

# Periodic refresh
baselinr lineage sync --provider postgres_query_history
```

This captures ad-hoc queries and real-world usage patterns that may not be in dbt or view definitions.

### 7. Monitor Stale Lineage

Query history lineage includes staleness detection:

```python
# System automatically warns about stale edges
upstream = client.get_upstream_lineage(table="customers")
# Warning logged if edges haven't been seen in query history for >90 days
```

Clean up stale edges periodically:

```bash
baselinr lineage cleanup --provider postgres_query_history
```

## Future Enhancements

- **Column-Level Lineage**: Track dependencies at the column level
- **Dagster Provider**: Native integration with Dagster
- **Airflow Provider**: Extract lineage from Airflow DAGs
- **Lineage Visualization**: Visual graph representation in dashboard

## Additional Resources

- [CLI Reference](../README.md) - Complete CLI documentation
- [Python SDK Guide](./PYTHON_SDK.md) - SDK usage examples
- [dbt Integration Guide](./DBT_INTEGRATION.md) - dbt-specific configuration
- [Schema Reference](../schemas/SCHEMA_REFERENCE.md) - Database schema documentation

---

**Questions?** Open an issue on GitHub or check the documentation.

