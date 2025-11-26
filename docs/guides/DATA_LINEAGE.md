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
- **Future Providers**: Dagster, Airflow, and other orchestration tools

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
- View definition parsing requires database access (coming soon)
- Complex SQL with dynamic table names may not be fully parsed

## Configuration

### Full Configuration Example

```yaml
profiling:
  extract_lineage: true  # Enable lineage extraction during profiling

lineage:
  enabled: true
  providers:
    # dbt provider
    - name: dbt_manifest
      enabled: true
      config:
        manifest_path: "target/manifest.json"
    
    # SQL parser provider
    - name: sql_parser
      enabled: true
  
  # Optional: Only use specific providers
  enabled_providers:
    - dbt_manifest
    - sql_parser
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
└────────────────┴────────────────────┘
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
  providers:
    - name: dbt_manifest
      enabled: true
    - name: sql_parser
      enabled: true
```

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
3. Check provider-specific requirements in logs

### Incomplete Lineage

**Problem**: Lineage graph is incomplete or missing relationships.

**Solutions**:
1. Enable multiple providers for better coverage
2. For dbt: Ensure all models are compiled
3. For SQL parser: Provide explicit SQL when possible
4. Check confidence scores - low confidence may indicate parsing issues

## Future Enhancements

- **Column-Level Lineage**: Track dependencies at the column level
- **View Definition Parsing**: Automatically extract lineage from view definitions
- **Query History Integration**: Extract lineage from warehouse query logs
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

