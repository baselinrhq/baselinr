# 🧩 ProfileMesh

**ProfileMesh** is a modern, open-source data profiling and drift detection framework for SQL-based data warehouses. It automatically profiles datasets, stores metadata and statistics, and detects drift over time.

## 🚀 Features

- **Automated Profiling**: Profile tables with column-level metrics (count, null %, distinct values, mean, stddev, histograms, etc.)
- **Drift Detection**: Compare profiling runs to detect schema and statistical drift with configurable strategies
- **Type-Specific Thresholds**: Adjust drift sensitivity based on column data type (numeric, categorical, timestamp, boolean) to reduce false positives
- **Intelligent Baseline Selection**: Automatically selects optimal baseline method (last run, moving average, prior period, stable window) based on column characteristics
- **Advanced Statistical Tests**: Kolmogorov-Smirnov (KS) test, Population Stability Index (PSI), Chi-square, Entropy, and more for rigorous drift detection
- **Event & Alert Hooks**: Pluggable event system for real-time alerts and notifications on drift, schema changes, and profiling lifecycle events
- **Partition-Aware Profiling**: Intelligent partition handling with strategies for latest, recent_n, or sample partitions
- **Adaptive Sampling**: Multiple sampling methods (random, stratified, top-k) for efficient profiling of large datasets
- **Multi-Database Support**: Works with PostgreSQL, Snowflake, SQLite, MySQL, BigQuery, and Redshift
- **Schema Versioning & Migrations**: Built-in schema version management with migration system for safe database schema evolution
- **Metadata Querying**: Powerful CLI and API for querying profiling runs, drift events, and table history
- **Dagster Integration**: Built-in orchestration support with Dagster assets and schedules
- **Configuration-Driven**: Simple YAML/JSON configuration for defining profiling targets
- **Historical Tracking**: Store profiling results over time for trend analysis
- **CLI Interface**: Comprehensive command-line interface for profiling, drift detection, querying, and schema management

## 📋 Requirements

- Python 3.10+
- One of the supported databases: PostgreSQL, Snowflake, SQLite, MySQL, BigQuery, or Redshift

## 🔧 Installation

### Basic Installation

```bash
pip install -e .
```

### With Snowflake Support

```bash
pip install -e ".[snowflake]"
```

### With Dagster Integration

```bash
pip install -e ".[dagster]"
```

### Full Installation (All Features)

```bash
pip install -e ".[all]"
```

## 📚 Documentation

All documentation has been organized into the [`docs/`](docs/) directory:

- **Getting Started**: [docs/getting-started/](docs/getting-started/) - Quick start and installation guides
- **User Guides**: [docs/guides/](docs/guides/) - Drift detection, partitioning, metrics
- **Architecture**: [docs/architecture/](docs/architecture/) - System design and implementation
- **Dashboard**: [docs/dashboard/](docs/dashboard/) - Dashboard setup and development
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
  results_table: profilemesh_results
  runs_table: profilemesh_runs
  create_tables: true

profiling:
  tables:
    - table: customers
      sample_ratio: 1.0
    - table: orders
      sample_ratio: 1.0
  
  default_sample_ratio: 1.0
  compute_histograms: true
  histogram_bins: 10
```

### 2. Preview What Will Be Profiled

```bash
profilemesh plan --config config.yml
```

This shows you what tables will be profiled without actually running the profiler.

### 3. Run Profiling

```bash
profilemesh profile --config config.yml
```

### 4. Detect Drift

After running profiling multiple times:

```bash
profilemesh drift --config config.yml --dataset customers
```

### 5. Query Profiling Metadata

Query your profiling history and drift events:

```bash
# List recent profiling runs
profilemesh query runs --config config.yml --limit 10

# Query drift events
profilemesh query drift --config config.yml --table customers --days 7

# Get detailed run information
profilemesh query run --config config.yml --run-id <run-id>

# View table profiling history
profilemesh query table --config config.yml --table customers --days 30
```

### 6. Manage Schema Migrations

Check and apply schema migrations:

```bash
# Check schema version status
profilemesh migrate status --config config.yml

# Apply migrations to latest version
profilemesh migrate apply --config config.yml --target 1

# Validate schema integrity
profilemesh migrate validate --config config.yml
```

## 🐳 Docker Development Environment

ProfileMesh includes a complete Docker environment for local development and testing.

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

ProfileMesh computes the following metrics:

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

## 🔄 Dagster Integration

ProfileMesh can create Dagster assets dynamically from your configuration:

```python
from profilemesh.integrations.dagster import build_profilemesh_definitions

defs = build_profilemesh_definitions(
    config_path="config.yml",
    asset_prefix="profilemesh",
    job_name="profilemesh_profile_all",
    enable_sensor=True,  # optional
)
```

## 🎯 Use Cases

- **Data Quality Monitoring**: Track data quality metrics over time
- **Schema Change Detection**: Automatically detect schema changes
- **Statistical Drift Detection**: Identify statistical anomalies in your data
- **Data Documentation**: Generate up-to-date metadata about your datasets
- **CI/CD Integration**: Fail builds when critical drift is detected

## 📁 Project Structure

```
profilemesh/
├── profilemesh/           # Main package
│   ├── config/           # Configuration management
│   ├── connectors/       # Database connectors
│   ├── profiling/        # Profiling engine
│   ├── storage/          # Results storage
│   ├── drift/            # Drift detection
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
profilemesh plan --config examples/config.yml

# View plan in JSON format
profilemesh plan --config examples/config.yml --output json

# View plan with verbose details
profilemesh plan --config examples/config.yml --verbose

# Profile all tables in config
profilemesh profile --config examples/config.yml

# Profile with output to JSON
profilemesh profile --config examples/config.yml --output results.json

# Dry run (don't write to storage)
profilemesh profile --config examples/config.yml --dry-run

# Detect drift
profilemesh drift --config examples/config.yml --dataset customers

# Detect drift with specific runs
profilemesh drift --config examples/config.yml \
  --dataset customers \
  --baseline <run-id-1> \
  --current <run-id-2>

# Fail on critical drift (useful for CI/CD)
profilemesh drift --config examples/config.yml \
  --dataset customers \
  --fail-on-drift

# Use statistical tests for advanced drift detection
# (configure in config.yml: strategy: statistical)

# Query profiling runs
profilemesh query runs --config examples/config.yml --limit 10

# Query drift events for a table
profilemesh query drift --config examples/config.yml \
  --table customers \
  --severity high \
  --days 7

# Get detailed run information
profilemesh query run --config examples/config.yml \
  --run-id <run-id> \
  --format json

# View table profiling history
profilemesh query table --config examples/config.yml \
  --table customers \
  --days 30 \
  --format csv \
  --output history.csv

# Check schema migration status
profilemesh migrate status --config examples/config.yml

# Apply schema migrations
profilemesh migrate apply --config examples/config.yml --target 1

# Validate schema integrity
profilemesh migrate validate --config examples/config.yml
```

## 🔍 Drift Detection

ProfileMesh provides multiple drift detection strategies and intelligent baseline selection:

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

ProfileMesh automatically selects the optimal baseline for drift detection based on column characteristics:

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

ProfileMesh includes a pluggable event system that emits events for drift detection, schema changes, and profiling lifecycle events. You can register hooks to process these events for logging, persistence, or alerting.

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
      table_name: profilemesh_events
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
from profilemesh.events import BaseEvent

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

ProfileMesh includes a built-in schema versioning system to manage database schema evolution safely.

### Migration Commands

```bash
# Check current schema version status
profilemesh migrate status --config config.yml

# Apply migrations to a specific version
profilemesh migrate apply --config config.yml --target 1

# Preview migrations (dry run)
profilemesh migrate apply --config config.yml --target 1 --dry-run

# Validate schema integrity
profilemesh migrate validate --config config.yml
```

### How It Works

- Schema versions are tracked in the `profilemesh_schema_version` table
- Migrations are applied incrementally and can be rolled back
- The system automatically detects when your database schema is out of date
- Migrations are idempotent and safe to run multiple times

## 🔍 Metadata Querying

ProfileMesh provides powerful querying capabilities to explore your profiling history and drift events.

### Query Commands

```bash
# Query profiling runs with filters
profilemesh query runs --config config.yml \
  --table customers \
  --status completed \
  --days 30 \
  --limit 20 \
  --format table

# Query drift events
profilemesh query drift --config config.yml \
  --table customers \
  --severity high \
  --days 7 \
  --format json

# Get detailed information about a specific run
profilemesh query run --config config.yml \
  --run-id abc123-def456 \
  --format json

# View table profiling history over time
profilemesh query table --config config.yml \
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
  tables:
    - table: table_name
      schema: schema_name  # Optional
      sample_ratio: 1.0    # 0.0 to 1.0
  
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

## 🔐 Environment Variables

ProfileMesh supports environment variable overrides:

```bash
# Override source connection
export PROFILEMESH_SOURCE__HOST=prod-db.example.com
export PROFILEMESH_SOURCE__PASSWORD=secret

# Override environment
export PROFILEMESH_ENVIRONMENT=production

# Run profiling
profilemesh profile --config config.yml
```

## 🧪 Development

### Run Tests

```bash
pytest
```

### Code Formatting

```bash
black profilemesh/
isort profilemesh/
```

### Type Checking

```bash
mypy profilemesh/
```

## 📝 License

MIT License - see LICENSE file for details

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Contact

For questions and support, please open an issue on GitHub.

---

**ProfileMesh** - Modern data profiling made simple 🧩

