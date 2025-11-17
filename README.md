# 🧩 ProfileMesh

**ProfileMesh** is a modern, open-source data profiling and drift detection framework for SQL-based data warehouses. It automatically profiles datasets, stores metadata and statistics, and detects drift over time.

## 🚀 Features

- **Automated Profiling**: Profile tables with column-level metrics (count, null %, distinct values, mean, stddev, histograms, etc.)
- **Drift Detection**: Compare profiling runs to detect schema and statistical drift with configurable strategies
- **Advanced Statistical Tests**: Kolmogorov-Smirnov (KS) test, Population Stability Index (PSI), Chi-square, Entropy, and more for rigorous drift detection
- **Event & Alert Hooks**: Pluggable event system for real-time alerts and notifications on drift, schema changes, and profiling lifecycle events
- **Partition-Aware Profiling**: Intelligent partition handling with strategies for latest, recent_n, or sample partitions
- **Adaptive Sampling**: Multiple sampling methods (random, stratified, top-k) for efficient profiling of large datasets
- **Multi-Database Support**: Works with PostgreSQL, Snowflake, and SQLite
- **Dagster Integration**: Built-in orchestration support with Dagster assets and schedules
- **Configuration-Driven**: Simple YAML/JSON configuration for defining profiling targets
- **Historical Tracking**: Store profiling results over time for trend analysis
- **CLI Interface**: Easy-to-use command-line interface for manual profiling

## 📋 Requirements

- Python 3.10+
- PostgreSQL, Snowflake, or SQLite database

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
- **null_percent**: Percentage of null values
- **distinct_count**: Number of distinct values
- **distinct_percent**: Percentage of distinct values

### Numeric Columns
- **min**: Minimum value
- **max**: Maximum value
- **mean**: Average value
- **stddev**: Standard deviation
- **histogram**: Distribution histogram (optional)

### String Columns
- **min_length**: Minimum string length
- **max_length**: Maximum string length
- **avg_length**: Average string length

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

ProfileMesh provides multiple drift detection strategies:

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

Thresholds are fully configurable via the `drift_detection` configuration. See [docs/guides/DRIFT_DETECTION.md](docs/guides/DRIFT_DETECTION.md) for general drift detection and [docs/guides/STATISTICAL_DRIFT_DETECTION.md](docs/guides/STATISTICAL_DRIFT_DETECTION.md) for statistical tests.

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

## 🛠️ Configuration Options

### Source Configuration

```yaml
source:
  type: postgres | snowflake | sqlite
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
    - null_percent
    - distinct_count
    - distinct_percent
    - min
    - max
    - mean
    - stddev
    - histogram
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

