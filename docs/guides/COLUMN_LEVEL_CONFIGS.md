# Column-Level Configuration Guide

Baselinr supports fine-grained column-level configurations for profiling, drift detection, and anomaly detection. This allows you to control exactly which columns are profiled, which metrics are computed, and how drift/anomaly detection behaves on a per-column basis.

## Overview

Column-level configurations are unified in a single `columns` field at the dataset level. All column configs (profiling, drift, validation, anomaly) are nested within each column definition:

```yaml
datasets:
  datasets:
    - table: customers
      schema: public
      columns:
        - name: email
          profiling:
            enabled: true
            metrics: [count, null_count, distinct_count]
          drift:
            enabled: true
            thresholds:
              low: 2.0
              medium: 5.0
              high: 10.0
          validation:
            rules:
              - type: format
                pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
                severity: high
              - type: not_null
                severity: high
          anomaly:
            enabled: true
            methods: [control_limits, iqr]
```

## Key Features

- **Column Selection**: Choose which columns to profile using explicit names or patterns
- **Per-Column Metrics**: Specify which metrics to compute for each column
- **Per-Column Drift Control**: Customize drift thresholds, strategies, and enable/disable per column
- **Per-Column Anomaly Control**: Configure anomaly detection methods and thresholds per column
- **Pattern Matching**: Use wildcards (`*_id`) or regex patterns for column names
- **Dependency Management**: Automatic handling of dependencies (drift/anomaly require profiling)

## Configuration Structure

### Unified Column Configuration Schema

All column-level configuration is unified in a single `columns` field at the dataset level:

```yaml
datasets:
  datasets:
    - table: <table_name>
      schema: <schema_name>
      columns:
        - name: <column_name_or_pattern>    # Required
          pattern_type: wildcard | regex     # Optional (default: wildcard)
          metrics: [<list_of_metrics>]       # Optional (overrides table-level)
          profiling:                         # Optional
            enabled: true | false            # Default: true
          drift:                             # Optional
            enabled: true | false            # Default: true
            strategy: <strategy_name>        # Override drift strategy
            thresholds:                      # Per-column thresholds
              low: <float>
              medium: <float>
              high: <float>
            baselines:                       # Override baseline selection
              strategy: <strategy>
              windows: {...}
          validation:                         # Optional (Phase 3.5)
            rules:                           # Column-specific validation rules
              - type: format | range | enum | not_null | unique | referential
                pattern: <regex_pattern>      # For format rules
                min_value: <float>            # For range rules
                max_value: <float>            # For range rules
                allowed_values: [...]        # For enum rules
                severity: low | medium | high
                enabled: true | false
          anomaly:                           # Optional
            enabled: true | false            # Default: true
            methods: [<list_of_methods>]     # Override enabled methods
            thresholds:                      # Per-column thresholds
              iqr_threshold: <float>
              mad_threshold: <float>
              ewma_deviation_threshold: <float>
```

**Important**: The unified `columns` field replaces the old structure. The following fields are no longer supported:
- `profiling.columns[]` - Use top-level `columns` field instead
- `drift.columns[]` - Use top-level `columns` field instead
- `anomaly.columns[]` - Use top-level `columns` field instead
- `validation.rules[]` with column specified - Use `columns[].validation.rules` instead

Use `baselinr migrate-config` to automatically consolidate column configs.

## Column Selection

### Explicit Column Names

Specify exact column names to configure:

```yaml
columns:
  - name: email
    metrics: [count, null_count, distinct_count]
  - name: age
    metrics: [count, mean, stddev, min, max]
```

### Wildcard Patterns

Use wildcard patterns to match multiple columns:

```yaml
columns:
  - name: "*_id"           # Matches: customer_id, order_id, product_id
    metrics: [count, null_count]
  - name: "email*"         # Matches: email, email_address, email_verified
    metrics: [count, null_count, distinct_count]
```

**Wildcard Syntax**:
- `*` matches any sequence of characters
- `?` matches a single character

### Regex Patterns

For more complex patterns, use regex:

```yaml
columns:
  - name: "^(customer|order|product)_id$"
    pattern_type: regex
    metrics: [count, null_count]
```

### Excluding Columns

To skip profiling specific columns, set `profiling.enabled: false`:

```yaml
columns:
  - name: internal_notes
    profiling:
      enabled: false  # Column won't be profiled
  - name: "*_temp"    # Skip all temporary columns
    profiling:
      enabled: false
```

## Profiling Configuration

### Select Which Columns to Profile

By default, all columns are profiled. When you specify `columns`, only matching columns are profiled (unless `include_defaults` is used).

```yaml
datasets:
  datasets:
    - table: customers
      schema: public
      profiling:
        columns:
          - name: email
          - name: age
          - name: name
          # Only email, age, and name will be profiled
```

Or using directory-based structure:

```yaml
# datasets/customers.yml
table: customers
schema: public
profiling:
  columns:
    - name: email
    - name: age
    - name: name
```

To profile everything except specific columns:

```yaml
datasets:
  datasets:
    - table: customers
      schema: public
      profiling:
        columns:
          - name: "*"              # Profile all columns
          - name: internal_notes   # Except this one
            profiling:
              enabled: false
```

### Custom Metrics Per Column

Override table-level metrics for specific columns:

```yaml
datasets:
  datasets:
    - table: customers
      schema: public
      profiling:
        columns:
          - name: email
            # Only compute these metrics for email
            metrics: [count, null_count, distinct_count]
          - name: age
            # Full metrics for age
            metrics: [count, mean, stddev, min, max, null_ratio]
          - name: metadata_json
            # Minimal metrics for large JSON columns
            metrics: [count, null_count]
```

**Available Metrics**:
- `count` - Total row count
- `null_count` - Number of null values
- `null_ratio` - Ratio of nulls (0.0-1.0)
- `distinct_count` - Number of distinct values
- `unique_ratio` - Ratio of distinct to total
- `approx_distinct_count` - Approximate distinct count
- `min` - Minimum value
- `max` - Maximum value
- `mean` - Average (numeric)
- `stddev` - Standard deviation (numeric)
- `histogram` - Distribution histogram (numeric)
- `data_type_inferred` - Inferred semantic type
- `min_length`, `max_length`, `avg_length` - String length metrics

## Drift Detection Configuration

### Per-Column Drift Thresholds

Override global drift thresholds for specific columns:

```yaml
datasets:
  datasets:
    - table: customers
      schema: public
      profiling:
        columns:
          - name: lifetime_value
            drift:
              enabled: true
              thresholds:
                low: 5.0      # 5% change = low severity
                medium: 10.0  # 10% change = medium severity
                high: 20.0    # 20% change = high severity
```

### Disable Drift Detection Per Column

Skip drift detection for specific columns:

```yaml
datasets:
  datasets:
    - table: customers
      schema: public
      profiling:
        columns:
          - name: internal_notes
            drift:
              enabled: false  # No drift detection for this column
          - name: "*_id"
            drift:
              enabled: false  # No drift for ID columns
```

### Per-Column Drift Strategy

Override drift strategy for specific columns:

```yaml
profiling:
  tables:
    - table: customers
      columns:
        - name: amount
          drift:
            strategy: statistical  # Use statistical tests for this column
            thresholds: {...}
        - name: status
          drift:
            strategy: absolute_threshold  # Use simple thresholds
            thresholds:
              low: 2.0
              medium: 5.0
              high: 10.0
```

### Per-Column Baseline Selection

Override baseline selection strategy per column:

```yaml
profiling:
  tables:
    - table: customers
      columns:
        - name: daily_revenue
          drift:
            baselines:
              strategy: prior_period  # Use prior period for seasonality
              windows:
                prior_period: 7       # Same day last week
```

## Anomaly Detection Configuration

### Per-Column Anomaly Methods

Enable specific anomaly detection methods per column:

```yaml
profiling:
  tables:
    - table: orders
      columns:
        - name: amount
          anomaly:
            enabled: true
            methods: [control_limits, iqr, mad]  # Only these methods
        - name: order_date
          anomaly:
            enabled: true
            methods: [seasonality, regime_shift]  # Focus on temporal patterns
```

### Per-Column Anomaly Thresholds

Customize anomaly detection sensitivity per column:

```yaml
profiling:
  tables:
    - table: orders
      columns:
        - name: amount
          anomaly:
            enabled: true
            thresholds:
              iqr_threshold: 2.0           # More sensitive (default: 1.5)
              mad_threshold: 3.5           # More sensitive (default: 3.0)
              ewma_deviation_threshold: 2.5 # More sensitive (default: 2.0)
        - name: quantity
          anomaly:
            enabled: true
            thresholds:
              iqr_threshold: 3.0           # Less sensitive
```

### Disable Anomaly Detection Per Column

```yaml
profiling:
  tables:
    - table: customers
      columns:
        - name: metadata_json
          anomaly:
            enabled: false  # Skip anomaly detection
```

## Dependency Management

### Understanding Dependencies

There's a critical dependency chain:

**Profiling → Drift Detection → Anomaly Detection**

1. **Profiling** must run first (produces metrics)
2. **Drift Detection** requires profiling (compares metrics across runs)
3. **Anomaly Detection** requires profiling (analyzes current run's metrics)

### Automatic Dependency Handling

Baselinr automatically handles dependencies:

- If a column is **not profiled** (`profiling.enabled: false`), drift and anomaly detection are automatically skipped
- If drift/anomaly is configured but profiling is disabled, a warning is issued
- Columns without profiling cannot have drift or anomaly detection enabled

### Example: Invalid Configuration (Will Warn)

```yaml
profiling:
  tables:
    - table: customers
      columns:
        - name: metadata
          profiling:
            enabled: false  # ❌ Profiling disabled
          drift:
            enabled: true   # ⚠️ Warning: Drift requires profiling
          anomaly:
            enabled: true   # ⚠️ Warning: Anomaly requires profiling
```

**Result**: Warnings are logged, and drift/anomaly are automatically skipped for this column.

## Complete Examples

### Example 1: Basic Column Selection

```yaml
profiling:
  tables:
    - table: customers
      schema: public
      columns:
        - name: email
          metrics: [count, null_count, distinct_count]
        - name: age
          metrics: [count, mean, stddev, min, max]
        - name: "*_id"
          metrics: [count, null_count]
```

### Example 2: Selective Profiling with Drift Control

```yaml
profiling:
  tables:
    - table: customers
      columns:
        - name: email
          metrics: [count, null_count, distinct_count]
          drift:
            enabled: true
            thresholds:
              low: 2.0
              medium: 5.0
              high: 10.0
        - name: lifetime_value
          metrics: [count, mean, stddev, min, max]
          drift:
            enabled: true
            thresholds:
              low: 5.0
              medium: 15.0
              high: 30.0
        - name: internal_notes
          profiling:
            enabled: false  # Not profiled
        - name: "*_id"
          drift:
            enabled: false  # No drift detection for IDs
```

### Example 3: Full Configuration with Anomaly Detection

```yaml
profiling:
  tables:
    - table: orders
      columns:
        - name: amount
          metrics: [count, mean, stddev, min, max]
          drift:
            enabled: true
            strategy: absolute_threshold
            thresholds:
              low: 5.0
              medium: 15.0
              high: 30.0
          anomaly:
            enabled: true
            methods: [control_limits, iqr, mad]
            thresholds:
              iqr_threshold: 2.0
              mad_threshold: 3.5
        - name: order_date
          metrics: [count, min, max]
          anomaly:
            enabled: true
            methods: [seasonality, regime_shift]
        - name: notes
          profiling:
            enabled: false  # Skip entirely
```

### Example 4: Pattern-Based Column Configuration

```yaml
profiling:
  tables:
    - table: events
      columns:
        # Profile all timestamp columns
        - name: "*_timestamp"
          metrics: [count, min, max]
          drift:
            enabled: true
        # Profile all ID columns with minimal metrics
        - name: "*_id"
          metrics: [count, null_count]
          drift:
            enabled: false  # IDs shouldn't drift
        # Use regex for complex patterns
        - name: "^(email|phone|address).*"
          pattern_type: regex
          metrics: [count, null_count, distinct_count]
```

## Schema-Level Configuration

Schema-level configurations allow you to apply settings to all tables within a specified schema, reducing configuration duplication and enabling organizational policy management.

### Overview

Schema-level configs support all the same options as table-level configs (partition, sampling, column configs, filters), and they merge with table-level configs following the precedence: **Schema → Table → Column**.

### Schema Configuration Structure

```yaml
profiling:
  tables:
    - table: orders
      schema: analytics

datasets:
  datasets:
    - schema: analytics
      database: warehouse  # Optional: database-specific schema config
      profiling:
        partition:
          strategy: latest
          key: date
        sampling:
          enabled: true
          fraction: 0.1
        columns:
          - name: "*_id"
            drift:
              enabled: false  # All ID columns in analytics schema skip drift
          - name: "*_metadata"
            profiling:
              enabled: false  # Skip metadata columns
        # Filter fields also supported
        min_rows: 100
        table_types: [table]
        exclude_patterns: ["*_temp"]

    - table: orders
      schema: analytics
      database: warehouse
      profiling:
        columns:
          - name: total_amount  # Override/add table-specific config
            drift:
              thresholds:
                low: 1.0
```

### How Schema Configs Work

1. **Schema Matching**: Schema configs match based on schema name (and optionally database name)
2. **Config Merging**: Schema configs are merged with table patterns before profiling
3. **Precedence**: Table-level configs override schema-level configs
4. **Column Configs**: Schema column configs are merged with table column configs (table takes precedence)

### Example: Schema-Level Column Configs

Apply column configurations to all tables in a schema:

```yaml
profiling:
  tables:
    - table: orders
      schema: analytics
    - table: customers
      schema: analytics

datasets:
  datasets:
    - schema: analytics
      profiling:
        columns:
          - name: "*_id"
            drift:
              enabled: false  # All ID columns skip drift detection
          - name: "*_metadata"
            profiling:
              enabled: false  # Skip metadata columns
  
    - table: customers
      schema: analytics
      profiling:
        columns:
          - name: email  # Add table-specific override
            drift:
              enabled: true
```

### Example: Schema-Level Sampling

Apply sampling configuration to all tables in a schema:

```yaml
profiling:
  tables:
    - select_schema: true
      schema: staging

datasets:
  datasets:
    - schema: staging
      profiling:
        sampling:
          enabled: true
          fraction: 0.1  # All staging tables sample 10%
  
  tables:
    - select_schema: true
      schema: staging  # Inherits sampling config
```

### Example: Database-Specific Schema Configs

Use database-specific schema configs for multi-database setups:

```yaml
profiling:
  schemas:
    - schema: analytics
      database: warehouse_prod
      sampling:
        enabled: true
        fraction: 0.05  # Production: 5% sampling
    - schema: analytics
      database: warehouse_dev
      sampling:
        enabled: true
        fraction: 0.2  # Development: 20% sampling
```

### Schema Config with Pattern Matching

Schema configs apply to tables discovered via patterns:

```yaml
profiling:
  schemas:
    - schema: analytics
      columns:
        - name: "*_id"
          drift:
            enabled: false
  
  tables:
    - pattern: "user_*"  # Pattern matches user_profiles, user_sessions, etc.
      schema: analytics  # All matched tables inherit schema column configs
```

### Schema Config with select_schema

Schema-level dataset configs work with `select_schema` to apply to all tables:

```yaml
profiling:
  tables:
    - select_schema: true
      schema: analytics  # All tables in analytics schema

datasets:
  datasets:
    - schema: analytics
      profiling:
        partition:
          strategy: latest
          key: date
        columns:
          - name: "*_temp"
            profiling:
              enabled: false
```

## Database-Level Configuration

Database-level configurations allow you to apply settings to all schemas/tables within a specified database, providing the broadest scope for organizational policy management.

### Overview

Database-level configs support all the same options as schema-level configs (partition, sampling, column configs, filters), and they merge with schema and table configs following the precedence: **Database → Schema → Table → Column**.

### Database Configuration Structure

```yaml
datasets:
  datasets:
    - database: warehouse
      profiling:
        partition:
          strategy: latest
          key: date
        sampling:
          enabled: true
          fraction: 0.05  # All tables in warehouse database sample 5%
        columns:
          - name: "*_id"
            drift:
              enabled: false  # All ID columns in warehouse database skip drift
          - name: "*_temp"
            profiling:
              enabled: false  # Skip temp columns in all tables
        # Filter fields also supported
        min_rows: 100
        table_types: [table]
        exclude_patterns: ["*_temp", "*_test"]

    - schema: analytics
      database: warehouse  # Inherits database-level configs
      profiling:
        columns:
          - name: "*_metadata"
            profiling:
              enabled: false  # Schema-level override

    - table: orders
      schema: analytics
      database: warehouse  # Inherits both database and schema configs
```

### How Database Configs Work

1. **Scope**: Database configs apply to ALL schemas/tables in the specified database
2. **Merging**: Database configs are merged with schema and table configs
3. **Precedence**: Database → Schema → Table → Column (each level can override previous)
4. **Column Configs**: Database column configs are merged with schema and table column configs (table takes highest precedence)

### Example: Database-Level Column Configs

Apply policies at the database level that can be overridden at schema or table level:

```yaml
datasets:
  datasets:
    - database: warehouse
      profiling:
        columns:
          - name: "*_id"
            drift:
              enabled: false  # Database-level: disable drift for all ID columns
  
    - schema: analytics
      database: warehouse
      profiling:
        columns:
          - name: "customer_id"
            drift:
              enabled: true  # Schema-level: override for customer_id in analytics schema
  
    - table: orders
      schema: analytics
      database: warehouse
      profiling:
        columns:
          - name: "customer_id"
          drift:
            enabled: false  # Table-level: override again for orders table
            thresholds:
              low: 1.0  # With custom thresholds
```

### Example: Database-Level Sampling

Apply consistent sampling strategy across all tables in a database:

```yaml
profiling:
  tables:
    - select_all_schemas: true
      database: staging_db

datasets:
  datasets:
    - database: staging_db
      profiling:
        sampling:
          enabled: true
          fraction: 0.05  # All tables in staging_db sample 5%
```

### Example: Multi-Level Precedence

Demonstrate how configurations merge across all levels:

```yaml
profiling:
  tables:
    - table: orders
      schema: analytics
      database: warehouse

datasets:
  datasets:
    - database: warehouse
      profiling:
        partition:
          strategy: all  # Database-level default
        columns:
          - name: "*_id"
            drift:
              enabled: false
  
    - schema: analytics
      database: warehouse
      profiling:
        partition:
          strategy: latest  # Schema-level override
        columns:
          - name: "customer_id"
            drift:
              enabled: true
  
    - table: orders
      schema: analytics
      database: warehouse
      profiling:
        partition:
          strategy: range  # Table-level override
          key: created_at
        columns:
          - name: "customer_id"
            drift:
              enabled: false  # Table-level override
```

**Result**:
- `orders` table uses `range` partition strategy (table overrides schema and database)
- `customer_id` column has drift disabled (table overrides schema, which overrides database)

### When to Use Database-Level Configs

Use database-level configs for:

1. **Organization-Wide Policies**: Apply consistent policies across all tables in a database
2. **Cost Management**: Apply sampling or filtering at the database level
3. **Security**: Disable profiling/drift for sensitive column patterns across the entire database
4. **Environment-Specific Settings**: Different policies for `production` vs `staging` databases

### Database Configs vs Schema Configs

- **Database Configs**: Apply to ALL schemas/tables in the database (broadest scope)
- **Schema Configs**: Apply to ALL tables in a specific schema (can be database-specific)
- **Table Configs**: Apply to a specific table (most specific)

Use database configs for organization-wide policies, and schema configs for schema-specific overrides.

## Configuration Precedence

Configurations are merged with the following precedence (highest to lowest):

1. **Column-level config** (most specific)
2. **Table-level dataset config** (from `datasets.datasets[]` with `table` specified)
3. **Schema-level dataset config** (from `datasets.datasets[]` with `schema` specified)
4. **Database-level dataset config** (from `datasets.datasets[]` with `database` specified)
5. **Global config** (defaults from `drift_detection` and `storage` sections)

Example with Database, Schema, and Table Levels:

```yaml
# Global defaults
drift_detection:
  strategy: absolute_threshold
  absolute_threshold:
    low_threshold: 5.0
    medium_threshold: 15.0
    high_threshold: 30.0

profiling:
  databases:
    - database: warehouse
      columns:
        - name: "*_id"
          drift:
            enabled: false  # Database-level: disable drift for all IDs
  
  schemas:
    - schema: analytics
      database: warehouse
      columns:
        - name: "customer_id"
          drift:
            enabled: true  # Schema-level: override for customer_id
  
  tables:
    - table: customers
      schema: analytics
      database: warehouse
      columns:
        - name: amount
          # Column-level overrides schema, database, and global
          drift:
            enabled: true
            thresholds:
              low: 2.0      # Uses 2.0 instead of 5.0
              medium: 10.0  # Uses 10.0 instead of 15.0
              high: 20.0    # Uses 20.0 instead of 30.0
```

## Backward Compatibility

Column-level configurations are **fully backward compatible**:

- If `columns` is not specified, all columns are profiled with table-level defaults
- Table-level configurations continue to work as before
- Existing configurations without column configs work unchanged
- Column-level features are opt-in

## Best Practices

### 1. Start Broad, Then Narrow

Begin with table-level configurations, then add column-level configs for specific needs:

```yaml
# Start here
profiling:
  tables:
    - table: customers

# Then refine specific columns
profiling:
  tables:
    - table: customers
      columns:
        - name: critical_field
          drift:
            thresholds:
              low: 1.0  # Very sensitive
```

### 2. Use Patterns for Repeated Configurations

Instead of listing every column, use patterns:

```yaml
columns:
  - name: "*_id"
    drift:
      enabled: false  # IDs shouldn't drift
  - name: "*_timestamp"
    metrics: [count, min, max]  # Timestamps don't need histograms
```

### 3. Disable Profiling for Large/Unimportant Columns

Save compute resources by skipping large JSON/text columns:

```yaml
columns:
  - name: raw_json_payload
    profiling:
      enabled: false
  - name: "*_metadata"
    profiling:
      enabled: false
```

### 4. Adjust Sensitivity Based on Business Importance

Use tighter thresholds for critical business metrics:

```yaml
columns:
  - name: revenue
    drift:
      thresholds:
        low: 1.0    # Very sensitive
        medium: 3.0
        high: 5.0
  - name: metadata
    drift:
      thresholds:
        low: 10.0   # More lenient
        medium: 20.0
        high: 40.0
```

### 5. Group Related Columns

Use patterns to configure related columns together:

```yaml
columns:
  - name: "*_email*"  # email, email_address, email_verified
    metrics: [count, null_count, distinct_count]
    drift:
      thresholds:
        low: 2.0
```

## Troubleshooting

### Column Not Being Profiled

**Problem**: Column specified in config isn't being profiled.

**Solutions**:
- Check column name spelling (case-sensitive in some databases)
- Verify pattern matches (test with explicit name first)
- Ensure `profiling.enabled` is not `false`
- Check that column exists in the table

### Drift Detection Not Running

**Problem**: Drift configured but not detecting changes.

**Solutions**:
- Verify column was actually profiled (check `profiled_columns` in metadata)
- Check `drift.enabled` is not `false`
- Ensure at least 2 profiling runs exist for comparison
- Verify thresholds are appropriate for the data

### Warnings About Dependencies

**Problem**: Warnings about drift/anomaly configured but profiling disabled.

**Solutions**:
- Remove drift/anomaly config if profiling is intentionally disabled
- Enable profiling if you want drift/anomaly detection
- Review configuration for typos or logic errors

## See Also

- [Drift Detection Guide](DRIFT_DETECTION.md) - Comprehensive drift detection documentation
- [Anomaly Detection Guide](ANOMALY_DETECTION.md) - Anomaly detection documentation
- [Configuration Reference](../reference/) - Complete configuration schema reference

