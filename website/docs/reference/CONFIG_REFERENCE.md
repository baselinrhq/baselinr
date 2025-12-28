# Baselinr Configuration Reference

Complete reference for all Baselinr configuration options with detailed explanations and examples.

## Table of Contents

- [Configuration Overview](#configuration-overview)
- [Basic Configuration](#basic-configuration)
- [Source Configuration](#source-configuration)
- [Storage Configuration](#storage-configuration)
- [Profiling Configuration](#profiling-configuration)
- [Drift Detection Configuration](#drift-detection-configuration)
- [Hooks Configuration](#hooks-configuration)
- [Monitoring Configuration](#monitoring-configuration)
- [Retry Configuration](#retry-configuration)
- [Execution Configuration](#execution-configuration)
- [Incremental Configuration](#incremental-configuration)
- [Schema Change Configuration](#schema-change-configuration)
- [Full Configuration Example](#full-configuration-example)

## Configuration Overview

Baselinr configuration is defined in YAML or JSON format. All configuration files start with:

```yaml
environment: development  # or test, production
source: {...}             # Source database connection
storage: {...}            # Storage configuration
```

Most other sections are optional and have sensible defaults.

## Basic Configuration

### `environment`

Environment name for this configuration.

**Type:** `string`

**Values:** `development`, `test`, `production`

**Default:** `development`

**Example:**
```yaml
environment: production
```

## Source Configuration

### `source`

Source database connection configuration.

**Type:** `ConnectionConfig`

**Required:** Yes

**Example:**
```yaml
source:
  type: postgres
  host: localhost
  port: 5432
  database: my_database
  username: my_user
  password: my_password
  schema: public
```

#### Connection Types

##### PostgreSQL

```yaml
source:
  type: postgres
  host: localhost
  port: 5432
  database: my_database
  username: my_user
  password: my_password
  schema: public  # Optional
```

##### Snowflake

```yaml
source:
  type: snowflake
  account: myaccount
  warehouse: compute_wh
  database: my_database
  schema: my_schema
  username: my_user
  password: my_password
  role: my_role  # Optional
```

##### SQLite

```yaml
source:
  type: sqlite
  filepath: ./database.db
```

##### MySQL

```yaml
source:
  type: mysql
  host: localhost
  port: 3306
  database: my_database
  username: my_user
  password: my_password
```

##### BigQuery

```yaml
source:
  type: bigquery
  database: my_project.my_dataset
  extra_params:
    credentials_path: /path/to/key.json
```

##### Redshift

```yaml
source:
  type: redshift
  host: my-cluster.xxxxx.us-east-1.redshift.amazonaws.com
  port: 5439
  database: my_database
  username: my_user
  password: my_password
```

**Fields:**
- `type` (str, required): Database type (postgres, snowflake, sqlite, mysql, bigquery, redshift)
- `host` (Optional[str]): Database host (not required for sqlite)
- `port` (Optional[int]): Database port
- `database` (str, required): Database name
- `username` (Optional[str]): Username
- `password` (Optional[str]): Password
- `schema` (Optional[str]): Schema name (alias: `schema_`)
- `account` (Optional[str]): Snowflake account
- `warehouse` (Optional[str]): Snowflake warehouse
- `role` (Optional[str]): Snowflake role
- `filepath` (Optional[str]): SQLite file path
- `extra_params` (Dict[str, Any]): Additional connection parameters

## Storage Configuration

### `storage`

Storage configuration for profiling results.

**Type:** `StorageConfig`

**Required:** Yes

**Example:**
```yaml
storage:
  connection:
    type: postgres
    host: localhost
    port: 5432
    database: baselinr_metadata
    username: baselinr
    password: password
  results_table: baselinr_results
  runs_table: baselinr_runs
  create_tables: true
```

**Fields:**
- `connection` (ConnectionConfig, required): Storage database connection
- `results_table` (str): Results table name (default: `baselinr_results`)
- `runs_table` (str): Runs table name (default: `baselinr_runs`)
- `create_tables` (bool): Automatically create tables (default: `true`)
- `enable_expectation_learning` (bool): Enable expectation learning (default: `false`)
- `learning_window_days` (int): Historical window for learning (default: `30`)
- `min_samples` (int): Minimum runs for learning (default: `5`)
- `ewma_lambda` (float): EWMA smoothing parameter (default: `0.2`)
- `enable_anomaly_detection` (bool): Enable anomaly detection (default: `false`)
- `anomaly_enabled_methods` (List[str]): Enabled anomaly methods (default: all methods)
- `anomaly_iqr_threshold` (float): IQR threshold (default: `1.5`)
- `anomaly_mad_threshold` (float): MAD threshold (default: `3.0`)
- `anomaly_ewma_deviation_threshold` (float): EWMA deviation threshold (default: `2.0`)
- `anomaly_seasonality_enabled` (bool): Enable seasonality detection (default: `true`)
- `anomaly_regime_shift_enabled` (bool): Enable regime shift detection (default: `true`)
- `anomaly_regime_shift_window` (int): Regime shift window size (default: `3`)
- `anomaly_regime_shift_sensitivity` (float): Regime shift p-value threshold (default: `0.05`)

## Profiling Configuration

### `profiling`

Profiling behavior configuration.

**Type:** `ProfilingConfig`

**Required:** No (has defaults)

**Example:**
```yaml
profiling:
  tables:
    - table: customers
      schema: public
  max_distinct_values: 1000
  compute_histograms: true
  histogram_bins: 10
  metrics:
    - count
    - null_count
    - null_ratio
    - distinct_count
    - mean
    - stddev
    - histogram
```

**Note:** Dataset-level profiling configuration (partition, sampling, columns) should be defined in ODCS contracts, not in `profiling.tables`. See [ODCS Data Contracts](../guides/ODCS_DATA_CONTRACTS.md) for details.

**Fields:**
- `tables` (List[TablePattern]): List of tables to profile (default: `[]`). TablePattern only contains table selection fields (table, schema, pattern, etc.). Profiling configuration should be in ODCS contracts.
- `table_discovery` (bool): Enable automatic table discovery (default: `true` when patterns used)
- `discovery_options` (DiscoveryOptionsConfig): Options for table discovery (see below)
- `max_distinct_values` (int): Maximum distinct values to compute (default: `1000`)
- `compute_histograms` (bool): Compute histograms (default: `true`)
- `histogram_bins` (int): Number of histogram bins (default: `10`)
- `metrics` (List[str]): Metrics to compute (default: all standard metrics)
- `default_sample_ratio` (float): Default sampling ratio (default: `1.0`)
- `enable_enrichment` (bool): Enable profiling enrichment (default: `true`)
- `enable_approx_distinct` (bool): Enable approximate distinct count (default: `true`)
- `enable_schema_tracking` (bool): Enable schema change tracking (default: `true`)
- `enable_type_inference` (bool): Enable data type inference (default: `true`)
- `enable_column_stability` (bool): Enable column stability tracking (default: `true`)
- `stability_window` (int): Stability calculation window (default: `7`)
- `type_inference_sample_size` (int): Type inference sample size (default: `1000`)

#### DiscoveryOptionsConfig

Configuration options for table discovery and pattern-based selection.

**Fields:**
- `include_schemas` (Optional[List[str]]): Only discover in these schemas
- `exclude_schemas` (Optional[List[str]]): Exclude these schemas from discovery
- `include_table_types` (Optional[List[str]]): Default table types to include
- `exclude_table_types` (Optional[List[str]]): Default table types to exclude
- `cache_discovery` (bool): Cache discovered tables for performance (default: `true`)
- `cache_ttl_seconds` (int): TTL for discovery cache in seconds (default: `300`)
- `max_tables_per_pattern` (int): Max tables to match per pattern (default: `1000`)
- `max_schemas_per_database` (int): Max schemas to scan per database (default: `100`)
- `discovery_limit_action` (str): What to do when limit hit: `"warn"`, `"error"`, or `"skip"` (default: `"warn"`)
- `validate_regex` (bool): Validate regex patterns at config load time (default: `true`)
- `tag_provider` (Optional[str]): Tag metadata provider: `"auto"`, `"snowflake"`, `"bigquery"`, `"postgres"`, `"mysql"`, `"redshift"`, `"sqlite"`, `"dbt"`, or `None` (default: `None`)
- `dbt_manifest_path` (Optional[str]): Path to dbt manifest.json for dbt tag provider

#### TablePattern

Configuration for a single table or table selection pattern.

**Fields:**
- `database` (Optional[str]): Database name (optional, defaults to `source.database`). When specified, the pattern operates on that database instead of the default source database. This enables multi-database profiling in a single configuration.
- `table` (Optional[str]): Explicit table name (required if pattern not used)
- `schema` (Optional[str]): Schema name (alias: `schema_`)
  
  **Pattern-based selection:**
- `pattern` (Optional[str]): Wildcard (`*`, `?`) or regex pattern for table name matching
- `pattern_type` (Optional[str]): Pattern type - `"wildcard"` or `"regex"` (default: `"wildcard"`)
- `schema_pattern` (Optional[str]): Wildcard/regex pattern for schema names
  
  **Schema/database-level selection:**
- `select_schema` (Optional[bool]): If `true`, profile all tables in specified schema(s). Can be combined with `database` field to profile all tables in a schema from a specific database.
- `select_all_schemas` (Optional[bool]): If `true`, profile all schemas in database. Can be combined with `database` field to profile all schemas from a specific database.
  
  **Tag-based selection:**
- `tags` (Optional[List[str]]): Tags that tables must have (AND logic)
- `tags_any` (Optional[List[str]]): Tags where any match (OR logic)
  
  **Filters:**
- `exclude_patterns` (Optional[List[str]]): Patterns to exclude from matches
- `table_types` (Optional[List[str]]): Filter by table type: `"table"`, `"view"`, `"materialized_view"`, etc.
- `min_rows` (Optional[int]): Only profile tables with at least N rows
- `max_rows` (Optional[int]): Only profile tables with at most N rows
- `required_columns` (Optional[List[str]]): Tables must have these columns
- `modified_since_days` (Optional[int]): Only profile tables modified in last N days
  
  **Precedence:**
- `override_priority` (Optional[int]): Higher priority overrides lower priority matches
  (default: explicit=100, patterns=10, schema=5, database=1)

**Note:** 
- Either `table`, `pattern`, `select_schema`, or `select_all_schemas` must be specified.
- **TablePattern only contains table selection fields.** Profiling configuration (partition, sampling, columns) should be defined in ODCS contracts. See [ODCS Data Contracts](../guides/ODCS_DATA_CONTRACTS.md) for details.

#### PartitionConfig

Partition-aware profiling configuration.

**Fields:**
- `key` (Optional[str]): Partition column name
- `strategy` (str): Partition strategy (default: `all`)
  - `all`: Profile all partitions
  - `latest`: Profile latest partition
  - `recent_n`: Profile N recent partitions
  - `sample`: Sample partitions
  - `specific_values`: Profile specific partition values
- `recent_n` (Optional[int]): Number of recent partitions (required for `recent_n` strategy)
- `values` (Optional[List[Any]]): Specific partition values (required for `specific_values` strategy)
- `metadata_fallback` (bool): Try to infer partition key (default: `true`)

#### SamplingConfig

Sampling configuration for profiling.

**Fields:**
- `enabled` (bool): Enable sampling (default: `false`)
- `method` (str): Sampling method (default: `random`)
  - `random`: Random sampling
  - `stratified`: Stratified sampling
  - `topk`: Top-K sampling
- `fraction` (float): Fraction of rows to sample (default: `0.01`)
- `max_rows` (Optional[int]): Maximum rows to sample

**Available Metrics:**
- `count`: Row count
- `null_count`: Number of null values
- `null_ratio`: Ratio of null values
- `distinct_count`: Number of distinct values
- `unique_ratio`: Ratio of unique values
- `approx_distinct_count`: Approximate distinct count
- `min`: Minimum value
- `max`: Maximum value
- `mean`: Mean value
- `stddev`: Standard deviation
- `histogram`: Value distribution histogram
- `data_type_inferred`: Inferred data type

## Drift Detection Configuration

### `drift_detection`

Drift detection configuration.

**Type:** `DriftDetectionConfig`

**Required:** No (has defaults)

**Example:**
```yaml
drift_detection:
  strategy: absolute_threshold
  absolute_threshold:
    low_threshold: 5.0
    medium_threshold: 15.0
    high_threshold: 30.0
  baselines:
    strategy: auto
    windows:
      moving_average: 7
      prior_period: 7
      min_runs: 3
  enable_type_specific_thresholds: true
  type_specific_thresholds:
    numeric:
      mean:
        low: 10.0
        medium: 25.0
        high: 50.0
      default:
        low: 5.0
        medium: 15.0
        high: 30.0
```

**Fields:**
- `strategy` (str): Drift detection strategy (default: `absolute_threshold`)
  - `absolute_threshold`: Percentage change thresholds
  - `standard_deviation`: Standard deviation based
  - `statistical`: Statistical tests (KS, PSI, etc.)
  - `ml_based`: Machine learning based (placeholder)
- `absolute_threshold` (Dict[str, float]): Absolute threshold parameters
  - `low_threshold`: Low severity threshold (default: `5.0`)
  - `medium_threshold`: Medium severity threshold (default: `15.0`)
  - `high_threshold`: High severity threshold (default: `30.0`)
- `standard_deviation` (Dict[str, float]): Standard deviation parameters
  - `low_threshold`: Low severity threshold in std devs (default: `1.0`)
  - `medium_threshold`: Medium severity threshold (default: `2.0`)
  - `high_threshold`: High severity threshold (default: `3.0`)
- `statistical` (Dict[str, Any]): Statistical test parameters
  - `tests`: List of tests to run (default: `["ks_test", "psi", "chi_square"]`)
  - `sensitivity`: Sensitivity level (default: `medium`)
  - `test_params`: Test-specific parameters
- `baselines` (Dict[str, Any]): Baseline selection configuration
  - `strategy`: Baseline strategy (default: `last_run`)
    - `auto`: Auto-select best baseline
    - `last_run`: Use last run
    - `moving_average`: Use moving average
    - `prior_period`: Use prior period
    - `stable_window`: Use stable window
  - `windows`: Window configuration
    - `moving_average`: Number of runs for moving average (default: `7`)
    - `prior_period`: Days for prior period (default: `7`)
    - `min_runs`: Minimum runs required (default: `3`)
- `enable_type_specific_thresholds` (bool): Enable type-specific thresholds (default: `true`)
- `type_specific_thresholds` (Dict[str, Dict[str, Dict[str, float]]]): Type-specific threshold overrides

## Hooks Configuration

### `hooks`

Event hooks configuration.

**Type:** `HooksConfig`

**Required:** No (has defaults)

**Example:**
```yaml
hooks:
  enabled: true
  hooks:
    - type: logging
      enabled: true
      log_level: INFO
    - type: slack
      enabled: true
      webhook_url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
      channel: "#data-alerts"
      min_severity: medium
      alert_on_drift: true
      alert_on_schema_change: true
```

**Fields:**
- `enabled` (bool): Master switch for all hooks (default: `true`)
- `hooks` (List[HookConfig]): List of hook configurations

#### HookConfig

Configuration for a single hook.

**Fields:**
- `type` (str, required): Hook type
  - `logging`: Log events
  - `sql`: Store events in SQL database
  - `snowflake`: Store events in Snowflake
  - `slack`: Send Slack notifications
  - `custom`: Custom hook
- `enabled` (bool): Enable this hook (default: `true`)
- `log_level` (Optional[str]): Log level for logging hook (default: `INFO`)
- `connection` (Optional[ConnectionConfig]): Database connection for SQL/Snowflake hooks
- `table_name` (Optional[str]): Table name for SQL/Snowflake hooks (default: `baselinr_events`)
- `webhook_url` (Optional[str]): Webhook URL for Slack hook
- `channel` (Optional[str]): Slack channel
- `username` (Optional[str]): Slack username (default: `Baselinr`)
- `min_severity` (Optional[str]): Minimum severity to alert (default: `low`)
- `alert_on_drift` (Optional[bool]): Alert on drift events (default: `true`)
- `alert_on_schema_change` (Optional[bool]): Alert on schema changes (default: `true`)
- `alert_on_profiling_failure` (Optional[bool]): Alert on profiling failures (default: `true`)
- `timeout` (Optional[int]): Request timeout in seconds (default: `10`)
- `module` (Optional[str]): Module path for custom hook
- `class_name` (Optional[str]): Class name for custom hook
- `params` (Dict[str, Any]): Additional parameters for custom hook

## Monitoring Configuration

### `monitoring`

Prometheus metrics configuration.

**Type:** `MonitoringConfig`

**Required:** No (has defaults)

**Example:**
```yaml
monitoring:
  enable_metrics: true
  port: 9753
  keep_alive: true
```

**Fields:**
- `enable_metrics` (bool): Enable Prometheus metrics (default: `false`)
- `port` (int): Metrics server port (default: `9753`)
- `keep_alive` (bool): Keep server running after profiling (default: `true`)

## Retry Configuration

### `retry`

Retry and recovery configuration.

**Type:** `RetryConfig`

**Required:** No (has defaults)

**Example:**
```yaml
retry:
  enabled: true
  retries: 3
  backoff_strategy: exponential
  min_backoff: 0.5
  max_backoff: 8.0
```

**Fields:**
- `enabled` (bool): Enable retry logic (default: `true`)
- `retries` (int): Maximum retry attempts (default: `3`, range: 0-10)
- `backoff_strategy` (str): Backoff strategy (default: `exponential`)
  - `exponential`: Exponential backoff
  - `fixed`: Fixed backoff
- `min_backoff` (float): Minimum backoff in seconds (default: `0.5`)
- `max_backoff` (float): Maximum backoff in seconds (default: `8.0`)

## Execution Configuration

### `execution`

Parallel execution configuration.

**Type:** `ExecutionConfig`

**Required:** No (has defaults)

**Example:**
```yaml
execution:
  max_workers: 4
  batch_size: 10
  queue_size: 100
  warehouse_limits:
    snowflake: 20
    postgres: 8
    sqlite: 1
```

**Fields:**
- `max_workers` (int): Maximum parallel workers (default: `1`, sequential)
- `batch_size` (int): Tables per batch (default: `10`)
- `queue_size` (int): Maximum queue size (default: `100`)
- `warehouse_limits` (Dict[str, int]): Warehouse-specific worker limits

**Note:** Default is sequential execution (`max_workers=1`) for backward compatibility. Set `max_workers > 1` to enable parallelism.

## Incremental Configuration

### `incremental`

Incremental profiling configuration.

**Type:** `IncrementalConfig`

**Required:** No (has defaults)

**Example:**
```yaml
incremental:
  enabled: true
  change_detection:
    enabled: true
    metadata_table: baselinr_table_state
    snapshot_ttl_minutes: 1440
  partial_profiling:
    enabled: true
    allow_partition_pruning: true
    max_partitions_per_run: 64
  adaptive_scheduling:
    enabled: true
    default_interval_minutes: 1440
  cost_controls:
    enabled: true
    max_bytes_scanned: 1000000000
    fallback_strategy: sample
```

**Fields:**
- `enabled` (bool): Enable incremental profiling (default: `false`)
- `change_detection`: Change detection configuration
  - `enabled` (bool): Enable change detection (default: `true`)
  - `metadata_table` (str): Metadata cache table (default: `baselinr_table_state`)
  - `snapshot_ttl_minutes` (int): Cache TTL in minutes (default: `1440`)
- `partial_profiling`: Partial profiling configuration
  - `enabled` (bool): Enable partial profiling (default: `true`)
  - `allow_partition_pruning` (bool): Allow partition pruning (default: `true`)
  - `max_partitions_per_run` (int): Max partitions per run (default: `64`)
- `adaptive_scheduling`: Adaptive scheduling configuration
  - `enabled` (bool): Enable adaptive scheduling (default: `true`)
  - `default_interval_minutes` (int): Default interval in minutes (default: `1440`)
- `cost_controls`: Cost control configuration
  - `enabled` (bool): Enable cost controls (default: `true`)
  - `max_bytes_scanned` (Optional[int]): Max bytes per run
  - `max_rows_scanned` (Optional[int]): Max rows per run
  - `fallback_strategy` (str): Fallback strategy (default: `sample`)

## Schema Change Configuration

### `schema_change`

Schema change detection configuration.

**Type:** `SchemaChangeConfig`

**Required:** No (has defaults)

**Example:**
```yaml
schema_change:
  enabled: true
  similarity_threshold: 0.7
  suppression:
    - table: staging_table
      change_type: column_added
```

**Fields:**
- `enabled` (bool): Enable schema change detection (default: `true`)
- `similarity_threshold` (float): Similarity threshold for rename detection (default: `0.7`)
- `suppression` (List[SchemaChangeSuppressionRule]): Suppression rules

## Data Contracts Configuration

### `contracts`

ODCS (Open Data Contract Standard) data contracts configuration. Contracts define dataset schemas, quality rules, SLAs, and stakeholders in a standardized format.

**Type:** `ContractsConfig`

**Required:** No

**Example:**
```yaml
contracts:
  directory: ./contracts
  file_patterns: ["*.odcs.yaml", "*.odcs.yml"]
  recursive: true
  validate_on_load: true
  exclude_patterns:
    - "**/templates/**"
  strict_validation: false
```

**Directory Structure:**
```
config.yml (main config)
contracts/
  ├── customers.odcs.yaml
  ├── orders.odcs.yaml
  ├── analytics/
  │   ├── reports.odcs.yaml
  │   └── metrics.odcs.yaml
  └── templates/
      └── template.odcs.yaml
```

**File Naming:**
- `{name}.odcs.yaml` or `{name}.odcs.yml` - ODCS contract files following v3.1.0 specification

**Configuration Options:**
- `directory` (str): Path to contracts directory (relative to config file or absolute, default: `./contracts`)
- `file_patterns` (List[str]): File patterns to match (default: `["*.odcs.yaml", "*.odcs.yml"]`)
- `recursive` (bool): Recursively search subdirectories (default: `true`)
- `validate_on_load` (bool): Validate contracts against ODCS schema when loading (default: `true`)
- `exclude_patterns` (Optional[List[str]]): Patterns to exclude from discovery
- `strict_validation` (bool): Treat validation warnings as errors (default: `false`)

**Benefits:**
- Standardized format (ODCS v3.1.0)
- Industry-standard data contracts
- Better interoperability with other tools
- Comprehensive dataset definitions (schema, quality, SLAs, stakeholders)
- Single source of truth for each dataset

See [ODCS Data Contracts Guide](../guides/ODCS_DATA_CONTRACTS.md) for complete documentation.

## Full Configuration Example

See `examples/config.yml` for a complete configuration example with all options.

---

## Related Documentation

- [API Reference](API_REFERENCE.md) - Complete API documentation
- [Installation Guide](../getting-started/INSTALL.md) - Installation instructions
- [Quick Start Guide](../getting-started/QUICKSTART.md) - Quick start tutorial
- [Drift Detection Guide](../guides/DRIFT_DETECTION.md) - Drift detection details
- [Python SDK Guide](../guides/PYTHON_SDK.md) - SDK usage guide
- [Best Practices Guide](../guides/BEST_PRACTICES.md) - Configuration best practices
- [Troubleshooting Guide](../guides/TROUBLESHOOTING.md) - Configuration troubleshooting

