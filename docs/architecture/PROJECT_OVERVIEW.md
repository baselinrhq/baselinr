# Baselinr Project Overview

## 📁 Complete Project Structure

```
profile_mesh/
│
├── baselinr/                 # Main Python package
│   ├── __init__.py
│   ├── cli.py                  # Command-line interface
│   │
│   ├── config/                 # Configuration management
│   │   ├── __init__.py
│   │   ├── schema.py          # Pydantic models
│   │   └── loader.py          # YAML/JSON config loader
│   │
│   ├── connectors/            # Database connectors
│   │   ├── __init__.py
│   │   ├── base.py           # Abstract base connector
│   │   ├── postgres.py       # PostgreSQL implementation
│   │   ├── snowflake.py      # Snowflake implementation
│   │   └── sqlite.py         # SQLite implementation
│   │
│   ├── profiling/            # Profiling engine
│   │   ├── __init__.py
│   │   ├── core.py          # Main profiling orchestrator
│   │   └── metrics.py       # Column-level metric calculator
│   │
│   ├── storage/             # Results storage
│   │   ├── __init__.py
│   │   ├── writer.py       # Results writer
│   │   └── schema.sql      # Storage schema DDL
│   │
│   ├── drift/              # Drift detection
│   │   ├── __init__.py
│   │   └── detector.py     # Drift detector and reporter
│   │
│   └── integrations/
│       └── dagster/         # Dagster orchestration
│           ├── __init__.py
│           ├── assets.py    # Asset factory
│           ├── sensors.py   # Plan-aware sensor
│           └── events.py    # Event emission
│
├── examples/                # Example configurations
│   ├── config.yml          # PostgreSQL config
│   ├── config_sqlite.yml   # SQLite config
│   ├── dagster_repository.py  # Dagster definitions
│   └── quickstart.py       # Quickstart script
│
├── docker/                 # Docker development environment
│   ├── docker-compose.yml  # Compose configuration
│   ├── Dockerfile         # Application container
│   ├── init_postgres.sql  # Database initialization
│   ├── dagster.yaml      # Dagster instance config
│   └── workspace.yaml    # Dagster workspace config
│
├── tests/                 # Test suite
│   ├── __init__.py
│   ├── test_config.py    # Configuration tests
│   └── test_profiling.py # Profiling tests
│
├── setup.py              # Package setup (setuptools)
├── pyproject.toml        # Modern Python packaging config
├── requirements.txt      # Python dependencies
├── Makefile             # Development automation
├── .gitignore          # Git ignore patterns
├── .dockerignore       # Docker ignore patterns
├── LICENSE             # Apache License 2.0
├── README.md           # Main documentation
├── docs/getting-started/QUICKSTART.md       # Quick start guide
├── DEVELOPMENT.md      # Developer guide
├── PROJECT_OVERVIEW.md # This file
└── MANIFEST.in        # Package manifest

```

## 🎯 Key Features Implemented

### ✅ Phase 1 MVP Complete

All Phase 1 requirements from the specification have been implemented:

#### 1. Profiling Engine ✓
- ✅ Profiles tables via SQLAlchemy
- ✅ Collects schema metadata
- ✅ Computes column metrics:
  - count, null %, distinct %
  - min, max, mean, stddev
  - histograms
  - string length statistics
- ✅ Supports sampling
- ✅ Outputs structured results (JSON + SQL)

#### 2. Configuration System ✓
- ✅ YAML/JSON configuration loader
- ✅ Pydantic validation
- ✅ Warehouse connection configuration
- ✅ Table patterns (explicit or wildcard-ready)
- ✅ Sampling configuration
- ✅ Output destination configuration
- ✅ Environment overrides via env vars

#### 3. Storage Layer ✓
- ✅ Results table with history
- ✅ Schema includes:
  - dataset_name, column_name
  - metric_name, metric_value
  - profiled_at, run_id
- ✅ Runs table for metadata
- ✅ Automatic table creation

#### 4. Execution Layer ✓
- ✅ CLI command: `baselinr profile --config config.yml`
- ✅ Dagster integration:
  - Dynamic asset factory
  - Configurable jobs
  - Event emission
  - Schedule definitions

#### 5. Developer Environment ✓
- ✅ Docker Compose setup with:
  - PostgreSQL (sample data + results)
  - Dagster daemon
  - Dagster web UI
- ✅ Sample data generator (SQL seed script)
- ✅ No-cost local setup
- ✅ Sample tables: customers, products, orders

#### 6. Drift Detection ✓
- ✅ Compare two profile runs
- ✅ Detect schema changes
- ✅ Calculate metric differences
- ✅ Severity classification (low/medium/high)
- ✅ JSON output
- ✅ Summary statistics

## 📊 Supported Databases

| Database   | Status | Notes                          |
|------------|--------|--------------------------------|
| PostgreSQL | ✅ Full | Primary development target     |
| SQLite     | ✅ Full | Lightweight local testing      |
| Snowflake  | ✅ Full | Enterprise data warehouse      |
| MySQL      | 🔲 Easy | Can be added with connector    |
| BigQuery   | 🔲 Easy | Can be added with connector    |
| Redshift   | 🔲 Easy | Can be added with connector    |

## 🔧 Available Commands

### CLI Commands
```bash
# Profile tables
baselinr profile --config config.yml [--output results.json] [--dry-run]

# Detect drift
baselinr drift --config config.yml --dataset <name> \
  [--baseline <run-id>] [--current <run-id>] \
  [--output report.json] [--fail-on-drift]
```

### Makefile Commands
```bash
make help           # Show all commands
make install        # Install Baselinr
make docker-up      # Start Docker environment
make docker-down    # Stop Docker environment
make quickstart     # Run quickstart example
make test           # Run tests
make format         # Format code
make lint           # Run linters
```

### Python API
```python
from baselinr.config.loader import ConfigLoader
from baselinr.profiling.core import ProfileEngine
from baselinr.storage.writer import ResultWriter
from baselinr.drift.detector import DriftDetector

# Load config
config = ConfigLoader.load_from_file("config.yml")

# Profile tables
engine = ProfileEngine(config)
results = engine.profile()

# Write results
writer = ResultWriter(config.storage)
writer.write_results(results)

# Detect drift
detector = DriftDetector(config.storage)
report = detector.detect_drift(dataset_name="customers")
```

## 🚀 Getting Started

Choose your path:

### 1. Quick Test (5 minutes)
```bash
cd profile_mesh
make docker-up
pip install -e ".[dagster]"
make quickstart
```

### 2. Full Setup (10 minutes)
```bash
cd profile_mesh
make install-all
make docker-up
# Wait 30 seconds
baselinr profile --config examples/config.yml
```

### 3. Your Database
- Copy `examples/config.yml`
- Update connection details
- Add your tables
- Run: `baselinr profile --config your_config.yml`

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| README.md | Main documentation and feature overview |
| docs/getting-started/QUICKSTART.md | Step-by-step getting started guide |
| DEVELOPMENT.md | Architecture and contribution guide |
| PROJECT_OVERVIEW.md | This file - project structure |

## 🧪 Testing

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_config.py -v

# Run with coverage
pytest --cov=baselinr tests/
```

## 🐳 Docker Environment

The Docker environment includes:

- **PostgreSQL** (port 5432)
  - Database: `baselinr`
  - User: `baselinr`
  - Password: `baselinr`
  - Sample tables pre-loaded

- **Dagster UI** (port 3000)
  - http://localhost:3000
  - Pre-configured with Baselinr assets
  - Daily schedule for profiling

## 📦 Package Distribution

Baselinr can be installed as:

```bash
# Basic installation
pip install baselinr

# With Snowflake support
pip install baselinr[snowflake]

# With Dagster orchestration
pip install baselinr[dagster]

# Full installation
pip install baselinr[all]

# Development mode
pip install -e ".[dev,all]"
```

## 🎯 Phase 1 Completion Criteria - STATUS

All criteria from the specification are met:

✅ **CLI works**: `baselinr profile --config config.yml` produces results  
✅ **Dagster integration**: Assets discoverable and runnable  
✅ **Storage**: Results written to structured tables  
✅ **Drift detection**: Can compare two profile runs  

## 🔮 Future Enhancements (Post-MVP)

### Phase 2
- Web dashboard for visualization
- Alert system (email, Slack, PagerDuty)
- Additional database connectors
- Enhanced drift detection (ML-based)
- Data quality rules engine

### Phase 3
- Column correlation analysis
- PII detection
- Data lineage tracking
- Integration with data catalogs
- Real-time profiling

## 📄 License

Apache License 2.0 - see LICENSE file for details.

## 🤝 Contributing

Contributions welcome! See DEVELOPMENT.md for guidelines.

---

**Baselinr v0.1.0** - MVP Complete ✅

