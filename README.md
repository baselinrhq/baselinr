# 🧩 Baselinr

[![PyPI version](https://badge.fury.io/py/baselinr.svg)](https://badge.fury.io/py/baselinr)
[![CI](https://github.com/baselinrhq/baselinr/actions/workflows/cli-e2e.yml/badge.svg)](https://github.com/baselinrhq/baselinr/actions/workflows/cli-e2e.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/baselinrhq/baselinr/blob/main/LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**🌐 [Visit our website →](https://baselinr.io/)**

**Baselinr** is an open-source data quality and observability platform for SQL data warehouses. It automatically recommends which tables and columns to monitor, sets up data quality checks, profiles your data, detects drift and anomalies, and provides AI-powered root cause analysis—all with a self-improving feedback loop that learns from your data patterns. Use automation for zero-touch setup, or configure everything manually—you have full control and transparency.

**Quality Studio** - Baselinr includes a powerful no-code web interface for setting up and managing your entire data quality configuration. Configure connections, tables, profiling settings, validation rules, drift detection, and more—all through an intuitive visual interface without writing YAML or JSON. The UI provides real-time validation, smart recommendations, and a visual editor with YAML preview, making it easy to get started while maintaining full transparency and control.

**🎮 [Try Quality Studio Demo →](https://demo.baselinr.io)** - Experience the Quality Studio with realistic sample data showcasing all features.

## 🚀 Features

- **Automated Setup** ✨ **NEW**: Zero-touch configuration—automatically recommends tables and columns to monitor, suggests data quality checks, and can auto-apply configurations to set up complete monitoring in minutes. Or configure everything manually with full control—automation is optional, not required
- **Smart Table Selection**: Automatically recommend tables to monitor based on database usage patterns, query frequency, and metadata analysis - reduce configuration overhead with intelligent, usage-based table discovery
- **Intelligent Column Recommendations**: Analyzes column characteristics to automatically suggest appropriate data quality checks (uniqueness, format validation, range checks, etc.) with confidence scoring
- **Self-Improving Feedback Loop**: Learns from your data patterns, existing configurations, and monitoring results to continuously improve recommendations (when using automation)
- **Full Manual Control**: Complete YAML/JSON configuration with control over every aspect—use automation when helpful, configure manually when you need full control
- **Automated Profiling**: Profile tables with column-level metrics (count, null %, distinct values, mean, stddev, histograms, etc.)
- **Drift Detection**: Compare profiling runs to detect schema and statistical drift with configurable strategies
- **Type-Specific Thresholds**: Adjust drift sensitivity based on column data type (numeric, categorical, timestamp, boolean) to reduce false positives
- **Intelligent Baseline Selection**: Automatically selects optimal baseline method (last run, moving average, prior period, stable window) based on column characteristics
- **Advanced Statistical Tests**: Kolmogorov-Smirnov (KS) test, Population Stability Index (PSI), Chi-square, Entropy, and more for rigorous drift detection
- **Expectation Learning**: Automatically learns expected metric ranges from historical profiling data, including control limits, distributions, and categorical frequencies for proactive anomaly detection
- **Anomaly Detection**: Automatically detects outliers and seasonal anomalies using learned expectations with multiple detection methods (IQR, MAD, EWMA, trend/seasonality, regime shift)
- **Data Validation** ✨ **NEW**: Rule-based data quality validation with built-in validators for format, range, enum, null checks, uniqueness, and referential integrity
- **Root Cause Analysis** ✨ **NEW**: Automatically correlates anomalies with pipeline runs, code changes, and upstream data issues using temporal correlation, lineage analysis, and pattern matching
- **Event & Alert Hooks**: Pluggable event system for real-time alerts and notifications on drift, schema changes, anomalies, validation failures, and profiling lifecycle events
- **Partition-Aware Profiling**: Intelligent partition handling with strategies for latest, recent_n, or sample partitions
- **Adaptive Sampling**: Multiple sampling methods (random, stratified, top-k) for efficient profiling of large datasets
- **Multi-Database Support**: Works with PostgreSQL, Snowflake, SQLite, MySQL, BigQuery, and Redshift
- **Schema Versioning & Migrations**: Built-in schema version management with migration system for safe database schema evolution
- **Metadata Querying**: Powerful CLI and API for querying profiling runs, drift events, and table history
- **Dagster Integration**: Built-in orchestration support with Dagster assets and schedules
- **Airflow Integration**: Operators and sensors for Apache Airflow 2.x workflows
- **Configuration-Driven**: Simple YAML/JSON configuration for defining profiling targets
- **Historical Tracking**: Store profiling results over time for trend analysis
- **No-Code Quality Studio** ✨ **NEW**: Complete web-based UI for configuring and managing data quality—set up connections, tables, profiling, validation rules, and drift detection through an intuitive visual interface without writing configuration files
- **CLI Interface**: Comprehensive command-line interface for profiling, drift detection, querying, schema management, and Quality Studio UI

## 📋 Requirements

- Python 3.10+
- One of the supported databases: PostgreSQL, Snowflake, SQLite, MySQL, BigQuery, or Redshift

## 🔧 Installation

### Install from PyPI

Install Baselinr directly from PyPI:

```bash
pip install baselinr
```

### Install with Optional Dependencies

Baselinr supports optional dependencies for enhanced functionality:

**Snowflake Support:**
```bash
pip install baselinr[snowflake]
```

**Dagster Integration:**
```bash
pip install baselinr[dagster]
```

**Airflow Integration:**
```bash
pip install baselinr[airflow]
```

**All Features:**
```bash
pip install baselinr[all]
```

### Development Installation

For local development, clone the repository and install in editable mode:

```bash
git clone https://github.com/baselinrhq/baselinr.git
cd baselinr
pip install -e ".[dev]"
```

## 📚 Documentation

All documentation has been organized into the [`docs/`](docs/) directory:

- **Getting Started**: [docs/getting-started/](docs/getting-started/) - Quick start and installation guides
- **User Guides**: [docs/guides/](docs/guides/) - Drift detection, partitioning, metrics
- **Architecture**: [docs/architecture/](docs/architecture/) - System design and implementation
- **Quality Studio**: [docs/dashboard/](docs/dashboard/) - Quality Studio setup and development
- **Development**: [docs/development/](docs/development/) - Contributing and development
- **Roadmap**: [ROADMAP.md](ROADMAP.md) - Planned features and future enhancements

See [docs/README.md](docs/README.md) for the complete documentation index.

## 🏃 Quick Start

### 1. Create a Configuration File

Create a `config.yml` file:

```yaml
environment: development

source:
  type: postgres
  host: localhost
  port: 5432
  database: mydb
  username: user
  password: password
  schema: public

storage:
  connection:
    type: postgres
    host: localhost
    port: 5432
    database: mydb
    username: user
    password: password
  results_table: baselinr_results
  runs_table: baselinr_runs
  create_tables: true
  enable_expectation_learning: true  # Learn expected ranges automatically
  learning_window_days: 30           # Use last 30 days of data
  min_samples: 5                     # Require at least 5 historical runs
  enable_anomaly_detection: true     # Detect anomalies using learned expectations

profiling:
  tables:
    # Explicit table selection (highest priority)
    - table: customers
      schema: public
    
    # Pattern-based selection (wildcard)
    - pattern: "user_*"
      schema: public
      # Matches: user_profile, user_settings, user_preferences, etc.
    
    # Schema-based selection (all tables in schema)
    - select_schema: true
      schema: analytics
      exclude_patterns:
        - "*_temp"
        - "*_backup"
    
    # Regex pattern matching
    - pattern: "^(customer|order)_\\d{4}$"
      pattern_type: regex
      schema: public
      # Matches: customer_2024, order_2024, etc.
    
    # Multi-database profiling (optional database field)
    # - table: users
    #   schema: public
    #   database: analytics_db  # Profile from analytics_db instead of source.database
    # - pattern: "order_*"
    #   schema: public
    #   database: warehouse_db  # Profile matching tables from warehouse_db
    # - select_schema: true
    #   schema: analytics
    #   database: production_db  # Profile all tables in analytics schema from production_db
  
  # Discovery options for pattern-based selection
  discovery_options:
    max_tables_per_pattern: 1000
    max_schemas_per_database: 100
    cache_discovery: true
    validate_regex: true
  
  default_sample_ratio: 1.0
  compute_histograms: true
  histogram_bins: 10
```

### 2. Preview What Will Be Profiled

```bash
baselinr plan --config config.yml
```

This shows you what tables will be profiled without actually running the profiler.

### 3. Run Profiling

```bash
baselinr profile --config config.yml
```

### 4. Detect Drift

After running profiling multiple times:

```bash
baselinr drift --config config.yml --dataset customers
```

### 5. Run Data Validation

Execute validation rules to check data quality:

```bash
# Run all validation rules
baselinr validate --config config.yml

# Validate specific table
baselinr validate --config config.yml --table customers

# Save results to JSON file
baselinr validate --config config.yml --output validation_results.json
```

### 6. Query Profiling Metadata

Query your profiling history and drift events:

```bash
# List recent profiling runs
baselinr query runs --config config.yml --limit 10

# Query drift events
baselinr query drift --config config.yml --table customers --days 7

# Get detailed run information
baselinr query run --config config.yml --run-id <run-id>

# View table profiling history
baselinr query table --config config.yml --table customers --days 30
```

### 7. Check System Status

Get a quick overview of recent runs and active drift:

```bash
# Show status dashboard
baselinr status --config config.yml

# Show only drift summary
baselinr status --config config.yml --drift-only

# Watch mode (auto-refresh)
baselinr status --config config.yml --watch

# JSON output for scripting
baselinr status --config config.yml --json
```

### 8. Start Quality Studio

Launch the Quality Studio web interface to configure your data quality setup, view profiling runs, drift alerts, and metrics:

**🎮 [Try the Demo →](https://demo.baselinr.io)** - Experience Quality Studio with sample data (no installation required)

```bash
# Start Quality Studio (foreground mode)
baselinr ui --config config.yml

# Custom ports
baselinr ui --config config.yml --port-backend 8080 --port-frontend 3001

# Localhost only
baselinr ui --config config.yml --host 127.0.0.1
```

Press `Ctrl+C` to stop the Quality Studio. See [docs/schemas/UI_COMMAND.md](docs/schemas/UI_COMMAND.md) for more details.

The Quality Studio provides a no-code interface for:
- **Configuration Management**: Set up connections, storage, tables, and profiling settings through visual forms
- **Validation Rules**: Create and manage data quality validation rules with a visual rule builder
- **Drift Detection**: Configure drift detection strategies and thresholds
- **Monitoring & Analysis**: View profiling runs, drift alerts, validation results, and root cause analysis
- **Visual Editor**: Edit configuration with a split-view visual/YAML editor

### 9. Manage Schema Migrations

Check and apply schema migrations:

```bash
# Check schema version status
baselinr migrate status --config config.yml

# Apply migrations to latest version
baselinr migrate apply --config config.yml --target 1

# Validate schema integrity
baselinr migrate validate --config config.yml
```

## 🐳 Docker Development Environment

Baselinr includes a complete Docker environment for local development and testing.

### Start the Environment

```bash
cd docker
docker-compose up -d
```

This will start:
- PostgreSQL with sample data
- Dagster daemon for orchestration
- Dagster web UI at http://localhost:3000

### Stop the Environment

```bash
cd docker
docker-compose down
```

## 📊 Profiling Metrics

Baselinr computes the following metrics:

### All Column Types
- **count**: Total number of rows
- **null_count**: Number of null values
- **null_ratio**: Ratio of null values (0.0 to 1.0)
- **distinct_count**: Number of distinct values
- **unique_ratio**: Ratio of distinct values to total (0.0 to 1.0)
- **approx_distinct_count**: Approximate distinct count (database-specific)
- **data_type_inferred**: Inferred data type from values (email, url, date, etc.)
- **column_stability_score**: Column presence stability (0.0 to 1.0)
- **column_age_days**: Days since column first appeared
- **type_consistency_score**: Type consistency across runs (0.0 to 1.0)

### Numeric Columns
- **min**: Minimum value
- **max**: Maximum value
- **mean**: Average value
- **stddev**: Standard deviation
- **histogram**: Distribution histogram (optional)

### String Columns
- **min**: Lexicographic minimum
- **max**: Lexicographic maximum
- **min_length**: Minimum string length
- **max_length**: Maximum string length
- **avg_length**: Average string length

### Table-Level Metrics
- **row_count_change**: Change in row count from previous run
- **row_count_change_percent**: Percentage change in row count
- **row_count_stability_score**: Row count stability (0.0 to 1.0)
- **row_count_trend**: Trend direction (increasing/stable/decreasing)
- **schema_freshness**: Timestamp of last schema modification
- **schema_version**: Incrementing schema version number
- **column_count_change**: Net change in column count

See [docs/guides/PROFILING_ENRICHMENT.md](docs/guides/PROFILING_ENRICHMENT.md) for detailed documentation on enrichment features.

## 🧠 Expectation Learning

Baselinr can automatically learn expected metric ranges from historical profiling data, creating statistical models that help identify outliers without explicit thresholds.

### Key Features

- **Automatic Learning**: Continuously learns expected values for metrics like mean, stddev, null_ratio, count, and unique_ratio
- **Control Limits**: Calculates lower and upper control limits using Shewhart (3-sigma) method or EWMA (Exponentially Weighted Moving Average)
- **Distribution Detection**: Automatically detects if metrics follow normal or empirical distributions
- **Categorical Frequencies**: Tracks expected frequency distributions for categorical columns
- **Separate from Baselines**: Learned expectations are stored separately from drift detection baselines, enabling proactive anomaly detection

### How It Works

Expectation learning analyzes historical profiling data over a configurable window (default: 30 days) to compute:
- Expected mean, variance, and standard deviation
- Control limits for outlier detection (3-sigma or EWMA-based)
- Distribution parameters (normal vs empirical)
- Expected categorical value frequencies

These learned expectations are automatically updated after each profiling run, providing an evolving model of what "normal" looks like for your data.

### Configuration

Enable expectation learning in your `config.yml`:

```yaml
storage:
  enable_expectation_learning: true
  learning_window_days: 30      # Historical window in days
  min_samples: 5                 # Minimum runs required for learning
  ewma_lambda: 0.2              # EWMA smoothing parameter (0 < lambda <= 1)
```

### Use Cases

- **Proactive Monitoring**: Identify anomalies before they cause drift
- **Automated Alerting**: Flag unexpected metric values automatically
- **Trend Analysis**: Understand normal ranges for your data over time
- **Quality Assurance**: Ensure metrics stay within expected operational ranges

See [docs/guides/EXPECTATION_LEARNING.md](docs/guides/EXPECTATION_LEARNING.md) for comprehensive documentation on expectation learning.

## 🔄 Dagster Integration

Baselinr can create Dagster assets dynamically from your configuration:

```python
from baselinr.integrations.dagster import build_baselinr_definitions

defs = build_baselinr_definitions(
    config_path="config.yml",
    asset_prefix="baselinr",
    job_name="baselinr_profile_all",
    enable_sensor=True,  # optional
)
```

## 🔧 dbt Integration

Baselinr provides comprehensive integration with dbt for scalable profiling and drift detection.

### Using dbt Refs/Selectors in Configs

Reference dbt models directly in your baselinr configuration:

```yaml
profiling:
  tables:
    - dbt_ref: customers
      dbt_project_path: ./dbt_project
    - dbt_selector: tag:critical
      dbt_project_path: ./dbt_project
```

### Direct dbt Model Integration

Use dbt model references and selectors in baselinr configs:

```yaml
# baselinr_config.yml
profiling:
  tables:
    - dbt_ref: customers
      dbt_project_path: ./dbt_project
    - dbt_selector: tag:critical
      dbt_project_path: ./dbt_project
```

**Installation**:
1. Install baselinr: `pip install baselinr`
2. Use dbt refs/selectors in your baselinr config:
   ```yaml
   profiling:
     tables:
       - dbt_ref: customers
         dbt_project_path: ./dbt_project
       - dbt_selector: tag:critical
         dbt_project_path: ./dbt_project
   ```
3. Run `dbt compile` or `dbt run` to generate manifest.json
4. Run profiling: `baselinr profile --config baselinr_config.yml`

> **Note**: dbt hooks can only execute SQL, not Python scripts. Run profiling after `dbt run` using an orchestrator or manually.

See [dbt Integration Guide](docs/guides/DBT_INTEGRATION.md) for complete documentation.

## 🪂 Airflow Integration

Baselinr provides comprehensive integration with Apache Airflow 2.x for orchestration and scheduling.

### Quick Start

```python
from airflow import DAG
from baselinr.integrations.airflow import BaselinrProfileOperator

dag = DAG("baselinr_profiling", ...)

profile_task = BaselinrProfileOperator(
    task_id="profile_tables",
    config_path="/path/to/config.yml",
    dag=dag,
)
```

### Operators

- **BaselinrProfileOperator**: Run profiling and return results via XCom
- **BaselinrDriftOperator**: Detect drift with optional DAG failure on drift
- **BaselinrQueryOperator**: Query Baselinr metadata (runs, drift, table history)

### Features

- Automatic XCom integration for passing results between tasks
- RCA collector for automatic DAG run metadata collection
- Support for Airflow REST API (v1/v2) and metadata database
- Fail on drift for CI/CD pipelines

See [Airflow Integration Guide](docs/guides/AIRFLOW_INTEGRATION.md) and [Quick Start](docs/guides/AIRFLOW_QUICKSTART.md) for complete documentation.

## 🐍 Python SDK

Baselinr provides a high-level Python SDK for programmatic access to all functionality.

### Quick Start

```python
from baselinr import BaselinrClient

# Initialize client
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

# Query recent runs
runs = client.query_runs(days=7, limit=10)

# Get status summary
status = client.get_status()
print(f"Active drift events: {len(status['drift_summary'])}")
```

### Documentation

- **Complete SDK Guide**: [docs/guides/PYTHON_SDK.md](docs/guides/PYTHON_SDK.md) - Comprehensive API reference, examples, and best practices

### SDK Examples

- **Basic Usage**: [examples/sdk_quickstart.py](examples/sdk_quickstart.py) - Simple profiling and drift detection
- **Advanced Usage**: [examples/sdk_advanced.py](examples/sdk_advanced.py) - Progress callbacks, custom analysis, querying

### Key Features

- **Simple API**: All functionality through a single `BaselinrClient` class
- **Automatic Setup**: Handles configuration loading, connection management, and event bus setup
- **Type Hints**: Full type annotations for IDE support
- **Lazy Loading**: Connections initialized only when needed

For complete SDK documentation including all methods, parameters, and advanced patterns, see the [Python SDK Guide](docs/guides/PYTHON_SDK.md).

## 🎯 Use Cases

- **Data Quality Monitoring**: Track data quality metrics over time
- **Data Validation**: Enforce data quality rules with format, range, enum, and referential integrity checks
- **Schema Change Detection**: Automatically detect schema changes
- **Statistical Drift Detection**: Identify statistical anomalies in your data
- **Data Documentation**: Generate up-to-date metadata about your datasets
- **CI/CD Integration**: Fail builds when critical drift or validation failures are detected

## 📁 Project Structure

```
baselinr/
├── baselinr/           # Main package
│   ├── config/           # Configuration management
│   ├── connectors/       # Database connectors
│   ├── profiling/        # Profiling engine
│   ├── storage/          # Results storage
│   ├── drift/            # Drift detection
│   ├── learning/         # Expectation learning
│   ├── anomaly/          # Anomaly detection
│   ├── integrations/
│   │   └── dagster/      # Dagster assets & sensors
│   └── cli.py            # CLI interface
├── examples/             # Example configurations
│   ├── config.yml        # PostgreSQL example
│   ├── config_sqlite.yml # SQLite example
│   ├── config_mysql.yml  # MySQL example
│   ├── config_bigquery.yml # BigQuery example
│   ├── config_redshift.yml # Redshift example
│   ├── config_with_metrics.yml # Metrics example
│   ├── config_slack_alerts.yml # Slack alerts example
│   ├── dagster_repository.py
│   └── quickstart.py
├── docker/               # Docker environment
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── init_postgres.sql
│   ├── dagster.yaml
│   └── workspace.yaml
├── setup.py
├── requirements.txt
└── README.md
```

## 🧪 Running Examples

### Quick Start Example

```bash
python examples/quickstart.py
```

### CLI Examples

```bash
# View profiling plan (dry-run)
baselinr plan --config examples/config.yml

# View plan in JSON format
baselinr plan --config examples/config.yml --output json

# View plan with verbose details
baselinr plan --config examples/config.yml --verbose

# Profile all tables in config
baselinr profile --config examples/config.yml

# Profile with output to JSON
baselinr profile --config examples/config.yml --output results.json

# Dry run (don't write to storage)
baselinr profile --config examples/config.yml --dry-run

# Detect drift
baselinr drift --config examples/config.yml --dataset customers

# Detect drift with specific runs
baselinr drift --config examples/config.yml \
  --dataset customers \
  --baseline <run-id-1> \
  --current <run-id-2>

# Fail on critical drift (useful for CI/CD)
baselinr drift --config examples/config.yml \
  --dataset customers \
  --fail-on-drift

# Use statistical tests for advanced drift detection
# (configure in config.yml: strategy: statistical)

# Query profiling runs
baselinr query runs --config examples/config.yml --limit 10

# Query drift events for a table
baselinr query drift --config examples/config.yml \
  --table customers \
  --severity high \
  --days 7

# Get detailed run information
baselinr query run --config examples/config.yml \
  --run-id <run-id> \
  --format json

# View table profiling history
baselinr query table --config examples/config.yml \
  --table customers \
  --days 30 \
  --format csv \
  --output history.csv

# Check system status
baselinr status --config examples/config.yml

# Watch status (auto-refresh)
baselinr status --config examples/config.yml --watch

# Status with JSON output
baselinr status --config examples/config.yml --json

# Start Quality Studio
baselinr ui --config examples/config.yml

# Check schema migration status
baselinr migrate status --config examples/config.yml

# Apply schema migrations
baselinr migrate apply --config examples/config.yml --target 1

# Validate schema integrity
baselinr migrate validate --config examples/config.yml
```

## 🔍 Drift Detection

Baselinr provides multiple drift detection strategies and intelligent baseline selection:

### Available Strategies

1. **Absolute Threshold** (default): Simple percentage-based thresholds
   - Low: 5% change
   - Medium: 15% change
   - High: 30% change

2. **Standard Deviation**: Statistical significance based on standard deviations

3. **Statistical Tests** (advanced): Multiple statistical tests for rigorous detection
   - **Numeric columns**: KS test, PSI, Z-score
   - **Categorical columns**: Chi-square, Entropy, Top-K stability
   - Automatically selects appropriate tests based on column type

### Intelligent Baseline Selection

Baselinr automatically selects the optimal baseline for drift detection based on column characteristics:

- **Auto Selection**: Automatically chooses the best baseline method per column
  - High variance columns → Moving average (smooths noise)
  - Seasonal columns → Prior period (accounts for weekly/monthly patterns)
  - Stable columns → Last run (simplest baseline)
- **Moving Average**: Average of last N runs (configurable, default: 7)
- **Prior Period**: Same period last week/month (handles seasonality)
- **Stable Window**: Historical window with low drift (most reliable)
- **Last Run**: Simple comparison to previous run (default)

Thresholds and baseline selection are fully configurable via the `drift_detection` configuration. See [docs/guides/DRIFT_DETECTION.md](docs/guides/DRIFT_DETECTION.md) for general drift detection and [docs/guides/STATISTICAL_DRIFT_DETECTION.md](docs/guides/STATISTICAL_DRIFT_DETECTION.md) for statistical tests.

## 🔔 Event & Alert Hooks

Baselinr includes a pluggable event system that emits events for drift detection, schema changes, and profiling lifecycle events. You can register hooks to process these events for logging, persistence, or alerting.

### Built-in Hooks

- **LoggingAlertHook**: Log events to stdout
- **SQLEventHook**: Persist events to any SQL database
- **SnowflakeEventHook**: Persist events to Snowflake with VARIANT support

### Example Configuration

```yaml
hooks:
  enabled: true
  hooks:
    # Log all events
    - type: logging
      log_level: INFO
    
    # Persist to database
    - type: sql
      table_name: baselinr_events
      connection:
        type: postgres
        host: localhost
        database: monitoring
        username: user
        password: pass
```

### Event Types

- **DataDriftDetected**: Emitted when drift is detected
- **SchemaChangeDetected**: Emitted when schema changes
- **ProfilingStarted**: Emitted when profiling begins
- **ProfilingCompleted**: Emitted when profiling completes
- **ProfilingFailed**: Emitted when profiling fails

### Custom Hooks

Create custom hooks by implementing the `AlertHook` protocol:

```python
from baselinr.events import BaseEvent

class MyCustomHook:
    def handle_event(self, event: BaseEvent) -> None:
        # Process the event
        print(f"Event: {event.event_type}")
```

Configure custom hooks:

```yaml
hooks:
  enabled: true
  hooks:
    - type: custom
      module: my_hooks
      class_name: MyCustomHook
      params:
        webhook_url: https://api.example.com/alerts
```

See [docs/architecture/EVENTS_AND_HOOKS.md](docs/architecture/EVENTS_AND_HOOKS.md) for comprehensive documentation and examples.

## 🔄 Schema Versioning & Migrations

Baselinr includes a built-in schema versioning system to manage database schema evolution safely.

### Migration Commands

```bash
# Check current schema version status
baselinr migrate status --config config.yml

# Apply migrations to a specific version
baselinr migrate apply --config config.yml --target 1

# Preview migrations (dry run)
baselinr migrate apply --config config.yml --target 1 --dry-run

# Validate schema integrity
baselinr migrate validate --config config.yml
```

### How It Works

- Schema versions are tracked in the `baselinr_schema_version` table
- Migrations are applied incrementally and can be rolled back
- The system automatically detects when your database schema is out of date
- Migrations are idempotent and safe to run multiple times

## 🔍 Metadata Querying

Baselinr provides powerful querying capabilities to explore your profiling history and drift events.

### Query Commands

```bash
# Query profiling runs with filters
baselinr query runs --config config.yml \
  --table customers \
  --status completed \
  --days 30 \
  --limit 20 \
  --format table

# Query drift events
baselinr query drift --config config.yml \
  --table customers \
  --severity high \
  --days 7 \
  --format json

# Get detailed information about a specific run
baselinr query run --config config.yml \
  --run-id abc123-def456 \
  --format json

# View table profiling history over time
baselinr query table --config config.yml \
  --table customers \
  --schema public \
  --days 90 \
  --format csv \
  --output history.csv
```

### Output Formats

All query commands support multiple output formats:
- **table**: Human-readable table format (default)
- **json**: JSON format for programmatic use
- **csv**: CSV format for spreadsheet analysis

## 🛠️ Configuration Options

### Source Configuration

```yaml
source:
  type: postgres | snowflake | sqlite | mysql | bigquery | redshift
  host: hostname
  port: 5432
  database: database_name
  username: user
  password: password
  schema: schema_name  # Optional
  
  # Snowflake-specific
  account: snowflake_account
  warehouse: warehouse_name
  role: role_name
  
  # SQLite-specific
  filepath: /path/to/database.db
  
  # BigQuery-specific (credentials via extra_params)
  extra_params:
    credentials_path: /path/to/service-account-key.json
    # Or use GOOGLE_APPLICATION_CREDENTIALS environment variable
  
  # MySQL-specific
  # Uses standard host/port/database/username/password
  
  # Redshift-specific
  # Uses standard host/port/database/username/password
  # Default port: 5439
```

### Profiling Configuration

```yaml
profiling:
  # Table discovery and pattern-based selection
  table_discovery: true  # Enable automatic table discovery
  discovery_options:
    max_tables_per_pattern: 1000  # Limit matches per pattern
    max_schemas_per_database: 100  # Limit schemas to scan
    validate_regex: true  # Validate regex patterns at config load time
    tag_provider: auto  # Tag metadata provider: auto, snowflake, bigquery, postgres, mysql, redshift, sqlite, dbt
  
  tables:
    # Explicit table selection (highest priority)
    - table: table_name
      schema: schema_name  # Optional
    
    # Pattern-based selection (wildcard)
    - pattern: "user_*"
      schema: public
      # Matches all tables starting with "user_"
    
    # Regex pattern matching
    - pattern: "^(customer|order)_\\d{4}$"
      pattern_type: regex
      schema: public
      # Matches: customer_2024, order_2024, etc.
    
    # Schema-based selection (all tables in schema)
    - select_schema: true
      schema: analytics
      exclude_patterns:
        - "*_temp"
        - "*_backup"
    
    # Database-level selection (all schemas)
    - select_all_schemas: true
      exclude_schemas:
        - "information_schema"
        - "pg_catalog"
    
    # Multi-database profiling (optional database field)
    # When database is specified, the pattern operates on that database
    # When omitted, uses config.source.database (backward compatible)
    # - table: customers
    #   schema: public
    #   database: analytics_db
    # - select_all_schemas: true
    #   database: staging_db  # Profile all schemas in staging_db
    
    # Tag-based selection
    - tags:
        - "data_quality:critical"
        - "domain:customer"
      schema: public
    
    # Precedence override (explicit table overrides pattern)
    - pattern: "events_*"
      schema: analytics
      override_priority: 10
    
    - table: events_critical
      schema: analytics
      override_priority: 100  # Higher priority overrides pattern
  
  default_sample_ratio: 1.0
  max_distinct_values: 1000
  compute_histograms: true  # Enable for statistical tests
  histogram_bins: 10
  
  metrics:
    - count
    - null_count
    - null_ratio
    - distinct_count
    - unique_ratio
    - approx_distinct_count
    - min
    - max
    - mean
    - stddev
    - histogram
    - data_type_inferred
```

### Drift Detection Configuration

```yaml
drift_detection:
  # Strategy: absolute_threshold | standard_deviation | statistical
  strategy: absolute_threshold
  
  # Absolute threshold (default)
  absolute_threshold:
    low_threshold: 5.0
    medium_threshold: 15.0
    high_threshold: 30.0
  
  # Baseline auto-selection configuration
  baselines:
    strategy: auto  # auto | last_run | moving_average | prior_period | stable_window
    windows:
      moving_average: 7    # Number of runs for moving average
      prior_period: 7      # Days for prior period (1=day, 7=week, 30=month)
      min_runs: 3          # Minimum runs required for auto-selection
  
  # Statistical tests (advanced)
  # statistical:
  #   tests:
  #     - ks_test
  #     - psi
  #     - z_score
  #     - chi_square
  #     - entropy
  #     - top_k
  #   sensitivity: medium
  #   test_params:
  #     ks_test:
  #       alpha: 0.05
  #     psi:
  #       buckets: 10
  #       threshold: 0.2
```

### Expectation Learning Configuration

```yaml
storage:
  # Enable automatic learning of expected metric ranges
  enable_expectation_learning: true
  
  # Historical window in days for learning expectations
  learning_window_days: 30
  
  # Minimum number of historical runs required for learning
  min_samples: 5
  
  # EWMA smoothing parameter for control limits (0 < lambda <= 1)
  # Lower values = more smoothing (0.1-0.3 recommended)
  ewma_lambda: 0.2
```

### Anomaly Detection Configuration

```yaml
storage:
  # Enable automatic anomaly detection using learned expectations
  enable_anomaly_detection: true
  
  # List of enabled detection methods (default: all methods)
  anomaly_enabled_methods:
    - control_limits
    - iqr
    - mad
    - ewma
    - seasonality
    - regime_shift
  
  # IQR multiplier threshold for outlier detection
  anomaly_iqr_threshold: 1.5
  
  # MAD threshold (modified z-score) for outlier detection
  anomaly_mad_threshold: 3.0
  
  # EWMA deviation threshold (number of stddevs)
  anomaly_ewma_deviation_threshold: 2.0
  
  # Enable trend and seasonality detection
  anomaly_seasonality_enabled: true
  
  # Enable regime shift detection
  anomaly_regime_shift_enabled: true
  
  # Number of recent runs for regime shift comparison
  anomaly_regime_shift_window: 3
  
  # P-value threshold for regime shift detection
  anomaly_regime_shift_sensitivity: 0.05
```

## 🔐 Environment Variables

Baselinr supports environment variable overrides:

```bash
# Override source connection
export BASELINR_SOURCE__HOST=prod-db.example.com
export BASELINR_SOURCE__PASSWORD=secret

# Override environment
export BASELINR_ENVIRONMENT=production

# Run profiling
baselinr profile --config config.yml
```

## 🧪 Development

### Run Tests

```bash
pytest
```

### Code Formatting

```bash
black baselinr/
isort baselinr/
```

### Type Checking

```bash
mypy baselinr/
```

## 📝 License

Apache License 2.0 - see LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Contact

For questions and support, please open an issue on GitHub.

---

**Baselinr** - Modern data profiling made simple 🧩

