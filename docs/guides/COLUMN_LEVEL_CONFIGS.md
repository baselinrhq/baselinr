# Column-Level Configuration Guide

Baselinr supports fine-grained column-level configurations for profiling, drift detection, and anomaly detection. This allows you to control exactly which columns are profiled, which metrics are computed, and how drift/anomaly detection behaves on a per-column basis.

## Overview

Column-level configurations are defined in ODCS contracts. All column configs (profiling, drift, validation, anomaly) are nested within each column definition in the contract:

```yaml
# contracts/customers.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: customers
    physicalName: public.customers
    columns:
      - column: email
        quality:
          - type: format
            rule: format
            specification:
              pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
            severity: error
          - type: not_null
            rule: not_null
            severity: error
customProperties:
  - property: baselinr.anomaly.customers.email
    value:
      enabled: true
      methods: [control_limits, iqr]
  - property: baselinr.drift.customers.email
    value:
      enabled: true
      thresholds:
        low: 2.0
        medium: 5.0
        high: 10.0
```

## Key Features

- **Column Selection**: Choose which columns to profile using explicit names or patterns
- **Per-Column Metrics**: Specify which metrics to compute for each column
- **Per-Column Drift Control**: Customize drift thresholds, strategies, and enable/disable per column
- **Per-Column Anomaly Control**: Configure anomaly detection methods and thresholds per column
- **Pattern Matching**: Use wildcards (`*_id`) or regex patterns for column names
- **Dependency Management**: Automatic handling of dependencies (drift/anomaly require profiling)

## Configuration Structure

### Column Configuration in ODCS Contracts

All column-level configuration is defined in ODCS contracts within the `dataset[].columns[]` section:

```yaml
# contracts/customers.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: customers
    physicalName: public.customers
    columns:
      - column: email
        # Validation rules via quality field
        quality:
          - type: format
            rule: format
            specification:
              pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
            severity: error
        # Profiling, drift, and anomaly via customProperties
customProperties:
  - property: baselinr.anomaly.customers.email
    value:
      enabled: true
      methods: [control_limits, iqr]
      thresholds:
        iqr_threshold: 1.5
        mad_threshold: 2.0
  - property: baselinr.drift.customers.email
    value:
      enabled: true
      strategy: absolute_threshold
      thresholds:
        low: 2.0
        medium: 5.0
        high: 10.0
```

**Important**: Column-level configurations are defined in ODCS contracts using:
- `quality` field for validation rules
- `customProperties` with `baselinr.*` prefixes for profiling, drift, and anomaly settings

See [ODCS Data Contracts Guide](./ODCS_DATA_CONTRACTS.md) for complete documentation.

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

By default, all columns are profiled. When you specify columns in an ODCS contract, only matching columns are profiled.

```yaml
# contracts/customers.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: customers
    physicalName: public.customers
    columns:
      - column: email
      - column: age
      - column: name
      # Only email, age, and name will be profiled
```

To profile everything except specific columns, use customProperties:

```yaml
# contracts/customers.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: customers
    physicalName: public.customers
    columns:
      - column: internal_notes
customProperties:
  - property: baselinr.profiling.customers.internal_notes
    value:
      enabled: false
```

### Custom Metrics Per Column

Override table-level metrics for specific columns using customProperties:

```yaml
# contracts/customers.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: customers
    physicalName: public.customers
    columns:
      - column: email
      - column: age
      - column: metadata_json
customProperties:
  - property: baselinr.profiling.customers.email
    value:
      metrics: [count, null_count, distinct_count]
  - property: baselinr.profiling.customers.age
    value:
      metrics: [count, mean, stddev, min, max, null_ratio]
  - property: baselinr.profiling.customers.metadata_json
    value:
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

Override global drift thresholds for specific columns using ODCS contracts:

```yaml
# contracts/customers.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: customers
    physicalName: public.customers
    columns:
      - column: lifetime_value
customProperties:
  - property: baselinr.drift.customers.lifetime_value
    value:
      enabled: true
      thresholds:
        low: 5.0      # 5% change = low severity
        medium: 10.0  # 10% change = medium severity
        high: 20.0    # 20% change = high severity
```

### Disable Drift Detection Per Column

Skip drift detection for specific columns using ODCS contracts:

```yaml
# contracts/customers.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: customers
    physicalName: public.customers
    columns:
      - column: internal_notes
      - column: customer_id
customProperties:
  - property: baselinr.drift.customers.internal_notes
    value:
      enabled: false  # No drift detection for this column
  - property: baselinr.drift.customers.customer_id
    value:
      enabled: false  # No drift for ID columns
```

### Per-Column Drift Strategy

Override drift strategy for specific columns using ODCS contracts:

```yaml
# contracts/customers.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: customers
    physicalName: public.customers
    columns:
      - column: amount
      - column: status
customProperties:
  - property: baselinr.drift.customers.amount
    value:
      strategy: statistical  # Use statistical tests for this column
      thresholds: {...}
  - property: baselinr.drift.customers.status
    value:
      strategy: absolute_threshold  # Use simple thresholds
      thresholds:
        low: 2.0
        medium: 5.0
        high: 10.0
```

### Per-Column Baseline Selection

Override baseline selection strategy per column using ODCS contracts:

```yaml
# contracts/customers.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: customers
    physicalName: public.customers
    columns:
      - column: daily_revenue
customProperties:
  - property: baselinr.drift.customers.daily_revenue
    value:
      baselines:
        strategy: prior_period  # Use prior period for seasonality
        windows:
          prior_period: 7       # Same day last week
```

## Anomaly Detection Configuration

### Per-Column Anomaly Methods

Enable specific anomaly detection methods per column using ODCS contracts:

```yaml
# contracts/orders.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: orders
    physicalName: public.orders
    columns:
      - column: amount
      - column: order_date
customProperties:
  - property: baselinr.anomaly.orders.amount
    value:
      enabled: true
      methods: [control_limits, iqr, mad]  # Only these methods
  - property: baselinr.anomaly.orders.order_date
    value:
      enabled: true
      methods: [seasonality, regime_shift]  # Focus on temporal patterns
```

### Per-Column Anomaly Thresholds

Customize anomaly detection sensitivity per column using ODCS contracts:

```yaml
# contracts/orders.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: orders
    physicalName: public.orders
    columns:
      - column: amount
      - column: quantity
customProperties:
  - property: baselinr.anomaly.orders.amount
    value:
      enabled: true
      thresholds:
        iqr_threshold: 2.0           # More sensitive (default: 1.5)
        mad_threshold: 3.5           # More sensitive (default: 3.0)
        ewma_deviation_threshold: 2.5 # More sensitive (default: 2.0)
  - property: baselinr.anomaly.orders.quantity
    value:
      enabled: true
      thresholds:
        iqr_threshold: 3.0           # Less sensitive
```

### Disable Anomaly Detection Per Column

```yaml
# contracts/customers.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: customers
    physicalName: public.customers
    columns:
      - column: metadata_json
customProperties:
  - property: baselinr.anomaly.customers.metadata_json
    value:
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
# contracts/customers.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: customers
    physicalName: public.customers
    columns:
      - column: metadata
customProperties:
  - property: baselinr.profiling.customers.metadata
    value:
      enabled: false  # ❌ Profiling disabled
  - property: baselinr.drift.customers.metadata
    value:
      enabled: true   # ⚠️ Warning: Drift requires profiling
  - property: baselinr.anomaly.customers.metadata
    value:
      enabled: true   # ⚠️ Warning: Anomaly requires profiling
```

**Result**: Warnings are logged, and drift/anomaly are automatically skipped for this column.

## Complete Examples

### Example 1: Basic Column Selection

```yaml
# contracts/customers.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: customers
    physicalName: public.customers
    columns:
      - column: email
      - column: age
      - column: customer_id
customProperties:
  - property: baselinr.profiling.customers.email
    value:
      metrics: [count, null_count, distinct_count]
  - property: baselinr.profiling.customers.age
    value:
      metrics: [count, mean, stddev, min, max]
  - property: baselinr.profiling.customers.customer_id
    value:
      metrics: [count, null_count]
```

### Example 2: Selective Profiling with Drift Control

```yaml
# contracts/customers.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: customers
    physicalName: public.customers
    columns:
      - column: email
      - column: lifetime_value
      - column: internal_notes
      - column: customer_id
customProperties:
  - property: baselinr.profiling.customers.email
    value:
      metrics: [count, null_count, distinct_count]
  - property: baselinr.drift.customers.email
    value:
      enabled: true
      thresholds:
        low: 2.0
        medium: 5.0
        high: 10.0
  - property: baselinr.profiling.customers.lifetime_value
    value:
      metrics: [count, mean, stddev, min, max]
  - property: baselinr.drift.customers.lifetime_value
    value:
      enabled: true
      thresholds:
        low: 5.0
        medium: 15.0
        high: 30.0
  - property: baselinr.profiling.customers.internal_notes
    value:
      enabled: false  # Not profiled
  - property: baselinr.drift.customers.customer_id
    value:
      enabled: false  # No drift detection for IDs
```

### Example 3: Full Configuration with Anomaly Detection

```yaml
# contracts/orders.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: orders
    physicalName: public.orders
    columns:
      - column: amount
      - column: order_date
      - column: notes
customProperties:
  - property: baselinr.profiling.orders.amount
    value:
      metrics: [count, mean, stddev, min, max]
  - property: baselinr.drift.orders.amount
    value:
      enabled: true
      strategy: absolute_threshold
      thresholds:
        low: 5.0
        medium: 15.0
        high: 30.0
  - property: baselinr.anomaly.orders.amount
    value:
      enabled: true
      methods: [control_limits, iqr, mad]
      thresholds:
        iqr_threshold: 2.0
        mad_threshold: 3.5
  - property: baselinr.profiling.orders.order_date
    value:
      metrics: [count, min, max]
  - property: baselinr.anomaly.orders.order_date
    value:
      enabled: true
      methods: [seasonality, regime_shift]
  - property: baselinr.profiling.orders.notes
    value:
      enabled: false  # Skip entirely
```

### Example 4: Pattern-Based Column Configuration

**Note**: ODCS contracts don't support pattern-based column matching directly. You need to explicitly list columns or use multiple contracts. For pattern-based matching, consider using the global `profiling.tables` configuration with patterns.

```yaml
# config.yml
profiling:
  tables:
    - table: events
      schema: public
      # Pattern matching is handled at table level, not column level
```

For column-specific configurations, define them explicitly in ODCS contracts.

## Schema-Level Configuration

**Note**: Schema-level configurations are now handled via ODCS contracts. You can organize contracts by schema (e.g., `contracts/analytics/*.odcs.yaml`) or include multiple datasets in a single contract to apply common settings.

### Overview

With ODCS contracts, you can define common settings for multiple tables by:
1. Creating separate contract files per schema (e.g., `contracts/analytics/orders.odcs.yaml`)
2. Including multiple datasets in one contract file
3. Using customProperties to apply schema-wide policies

### Schema Configuration with ODCS Contracts

```yaml
# contracts/analytics_schema.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: orders
    physicalName: warehouse.analytics.orders
    columns:
      - column: order_id
      - column: total_amount
customProperties:
  - property: baselinr.partition.orders
    value:
      strategy: latest
      key: date
  - property: baselinr.sampling.orders
    value:
      enabled: true
      fraction: 0.1
  - property: baselinr.drift.orders.order_id
    value:
      enabled: false  # All ID columns skip drift
  - property: baselinr.drift.orders.total_amount
    value:
      enabled: true
      thresholds:
        low: 1.0
```

### How Schema Configs Work

1. **Schema Matching**: Schema configs match based on schema name (and optionally database name)
2. **Config Merging**: Schema configs are merged with table patterns before profiling
3. **Precedence**: Table-level configs override schema-level configs
4. **Column Configs**: Schema column configs are merged with table column configs (table takes precedence)

### Example: Schema-Level Column Configs

Apply column configurations to all tables in a schema using ODCS contracts:

```yaml
# contracts/analytics_schema.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: orders
    physicalName: analytics.orders
    columns:
      - column: order_id
      - column: metadata
  - name: customers
    physicalName: analytics.customers
    columns:
      - column: customer_id
      - column: email
      - column: metadata
customProperties:
  # Schema-wide: disable drift for all ID columns
  - property: baselinr.drift.orders.order_id
    value:
      enabled: false
  - property: baselinr.drift.customers.customer_id
    value:
      enabled: false
  # Schema-wide: skip metadata columns
  - property: baselinr.profiling.orders.metadata
    value:
      enabled: false
  - property: baselinr.profiling.customers.metadata
    value:
      enabled: false
  # Table-specific override: enable drift for email
  - property: baselinr.drift.customers.email
    value:
      enabled: true
```

### Example: Schema-Level Sampling

Apply sampling configuration to all tables in a schema:

```yaml
# contracts/staging_schema.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: staging_table1
    physicalName: staging.table1
  - name: staging_table2
    physicalName: staging.table2
customProperties:
  # Apply 10% sampling to all staging tables
  - property: baselinr.sampling.staging_table1
    value:
      enabled: true
      fraction: 0.1
  - property: baselinr.sampling.staging_table2
    value:
      enabled: true
      fraction: 0.1
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

With ODCS contracts, you can organize contracts by schema directory structure:

```yaml
# contracts/analytics/orders.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: orders
    physicalName: analytics.orders
    columns:
      - column: order_date
        partitionStatus: true
      - column: temp_data
customProperties:
  - property: baselinr.partition.orders
    value:
      strategy: latest
      key: order_date
  - property: baselinr.profiling.orders.temp_data
    value:
      enabled: false
```

## Database-Level Configuration

**Note**: Database-level configurations are now handled via ODCS contracts. Organize contracts by database (e.g., `contracts/warehouse/*.odcs.yaml`) or use contract-level customProperties to apply database-wide policies.

### Overview

With ODCS contracts, you can achieve database-level configuration by:
1. Organizing contracts in database-specific directories
2. Using contract-level customProperties for database-wide policies
3. Including multiple datasets from different schemas in one contract

### Database Configuration with ODCS Contracts

```yaml
# contracts/warehouse_database.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: orders
    physicalName: warehouse.analytics.orders
    columns:
      - column: order_id
      - column: temp_data
  - name: customers
    physicalName: warehouse.analytics.customers
    columns:
      - column: customer_id
      - column: temp_data
customProperties:
  # Database-wide: 5% sampling for all tables
  - property: baselinr.sampling.orders
    value:
      enabled: true
      fraction: 0.05
  - property: baselinr.sampling.customers
    value:
      enabled: true
      fraction: 0.05
  # Database-wide: disable drift for all ID columns
  - property: baselinr.drift.orders.order_id
    value:
      enabled: false
  - property: baselinr.drift.customers.customer_id
    value:
      enabled: false
  # Database-wide: skip temp columns
  - property: baselinr.profiling.orders.temp_data
    value:
      enabled: false
  - property: baselinr.profiling.customers.temp_data
    value:
      enabled: false
```

### How Database Configs Work

1. **Scope**: Database configs apply to ALL schemas/tables in the specified database
2. **Merging**: Database configs are merged with schema and table configs
3. **Precedence**: Database → Schema → Table → Column (each level can override previous)
4. **Column Configs**: Database column configs are merged with schema and table column configs (table takes highest precedence)

### Example: Database-Level Column Configs

Apply policies at the database level using ODCS contracts:

```yaml
# contracts/warehouse_database.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: orders
    physicalName: warehouse.analytics.orders
    columns:
      - column: customer_id
  - name: customers
    physicalName: warehouse.analytics.customers
    columns:
      - column: customer_id
customProperties:
  # Database-level: disable drift for all ID columns (can be overridden per table)
  - property: baselinr.drift.orders.customer_id
    value:
      enabled: false
  # Table-level override: enable drift for customers table
  - property: baselinr.drift.customers.customer_id
    value:
      enabled: true
      thresholds:
        low: 1.0
```

### Example: Database-Level Sampling

Apply consistent sampling strategy across all tables in a database:

```yaml
# contracts/staging_db.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: table1
    physicalName: staging_db.schema1.table1
  - name: table2
    physicalName: staging_db.schema2.table2
customProperties:
  # All tables in staging_db sample 5%
  - property: baselinr.sampling.table1
    value:
      enabled: true
      fraction: 0.05
  - property: baselinr.sampling.table2
    value:
      enabled: true
      fraction: 0.05
```

### Example: Multi-Level Precedence

With ODCS contracts, precedence is handled via contract-level and dataset-level customProperties:

```yaml
# contracts/warehouse_analytics_orders.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: orders
    physicalName: warehouse.analytics.orders
    columns:
      - column: created_at
        partitionStatus: true
      - column: customer_id
customProperties:
  # Table-level: range partition strategy (overrides any database/schema defaults)
  - property: baselinr.partition.orders
    value:
      strategy: range
      key: created_at
  # Table-level: disable drift for customer_id (overrides any database/schema defaults)
  - property: baselinr.drift.orders.customer_id
    value:
      enabled: false
```

**Result**:
- `orders` table uses `range` partition strategy (defined in contract)
- `customer_id` column has drift disabled (defined in contract)

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

1. **Column-level config** (most specific - from ODCS contract columns)
2. **Contract-level config** (from ODCS contract customProperties)
3. **Global config** (defaults from `drift_detection` and `storage` sections)

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

