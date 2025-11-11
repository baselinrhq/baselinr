# 🧩 ProfileMesh

**ProfileMesh** is a modern, open-source data profiling and drift detection framework for SQL-based data warehouses. It automatically profiles datasets, stores metadata and statistics, and detects drift over time.

## 🚀 Features

- **Automated Profiling**: Profile tables with column-level metrics (count, null %, distinct values, mean, stddev, histograms, etc.)
- **Drift Detection**: Compare profiling runs to detect schema and statistical drift with configurable strategies
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
# dagster_repository.py
from dagster import Definitions
from profilemesh.dagster_integration import create_profiling_assets, create_profiling_job

# Create assets from config
assets = create_profiling_assets(
    config_path="config.yml",
    asset_name_prefix="profilemesh"
)

# Create a job
job = create_profiling_job(assets=assets)

# Define Dagster definitions
defs = Definitions(
    assets=assets,
    jobs=[job]
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
│   ├── dagster_integration/  # Dagster assets
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
```

## 🔍 Drift Detection Thresholds

ProfileMesh uses the following thresholds for drift severity:

- **Low**: 5% change
- **Medium**: 15% change
- **High**: 30% change

Thresholds are fully configurable via the `drift_detection` configuration. See [DRIFT_DETECTION.md](DRIFT_DETECTION.md) for details on configurable strategies.

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

See [EVENTS_AND_HOOKS.md](EVENTS_AND_HOOKS.md) for comprehensive documentation and examples.

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
  compute_histograms: true
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

