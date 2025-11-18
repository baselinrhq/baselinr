# Baselinr Development Guide

This guide is for developers who want to contribute to Baselinr or understand its internals.

## Architecture Overview

Baselinr is built with a modular architecture:

```
┌─────────────────────────────────────────────────────┐
│                   CLI / Dagster                      │
│                  (Entry Points)                      │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│               Configuration Layer                    │
│         (YAML/JSON + Pydantic Validation)           │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│               Profiling Engine                       │
│     (Orchestrates profiling of tables/columns)      │
└──────┬──────────────────────────────────────┬───────┘
       │                                      │
┌──────▼──────┐                      ┌───────▼────────┐
│ Connectors  │                      │    Metrics     │
│  (Database  │                      │  (Column-level │
│   Access)   │                      │   Statistics)  │
└──────┬──────┘                      └───────┬────────┘
       │                                      │
       └──────────────┬───────────────────────┘
                      │
         ┌────────────▼────────────┐
         │    Storage Layer        │
         │  (Results Persistence)  │
         └────────────┬────────────┘
                      │
         ┌────────────▼────────────┐
         │   Drift Detection       │
         │  (Compare Runs)         │
         └─────────────────────────┘
```

## Module Structure

### `config/`
- **`schema.py`**: Pydantic models for configuration validation
- **`loader.py`**: Loads YAML/JSON configs with env variable support

### `connectors/`
- **`base.py`**: Abstract base class for database connectors
- **`postgres.py`**: PostgreSQL connector implementation
- **`snowflake.py`**: Snowflake connector implementation
- **`sqlite.py`**: SQLite connector implementation

Each connector:
1. Creates SQLAlchemy engine
2. Provides table introspection
3. Executes queries for profiling

### `profiling/`
- **`core.py`**: Main profiling engine that orchestrates the process
- **`metrics.py`**: Calculates column-level metrics (count, mean, stddev, etc.)

The profiling flow:
1. Load configuration
2. Connect to source database
3. For each table:
   - Reflect schema
   - For each column:
     - Calculate applicable metrics
     - Collect results
4. Package results for storage

### `storage/`
- **`writer.py`**: Writes profiling results to storage backend
- **`schema.sql`**: SQL schema for results tables

Storage schema:
- `baselinr_runs`: Metadata about profiling runs
- `baselinr_results`: Individual column metrics (EAV pattern)

### `drift/`
- **`detector.py`**: Compares profiling runs to detect drift

Drift detection:
1. Load two profiling runs (baseline + current)
2. Compare schema (added/removed columns)
3. Compare metrics (calculate % change)
4. Classify severity (low/medium/high)

### `integrations/dagster/`
- **`assets.py`**: Factory for creating Dagster assets from config
- **`events.py`**: Structured event emission for Dagster
- **`sensors.py`**: Plan-aware sensor helpers
- **`__init__.py`**: `build_baselinr_definitions` entrypoint for Dagster repos

## Development Setup

### 1. Clone and Install

```bash
cd profile_mesh
pip install -e ".[dev,all]"
```

### 2. Start Development Environment

```bash
make dev-setup
```

This will:
- Install dependencies
- Start Docker containers (PostgreSQL + Dagster)

### 3. Run Tests

```bash
make test
```

### 4. Code Quality

```bash
# Format code
make format

# Run linters
make lint
```

## Testing Strategy

### Unit Tests
Test individual functions and classes in isolation:
- Configuration loading and validation
- Metric calculations
- Type detection utilities

### Integration Tests
Test components together with a real database:
- Full profiling workflow
- Storage operations
- Drift detection

### End-to-End Tests
Test complete scenarios:
- CLI commands
- Dagster asset execution

## Adding a New Database Connector

1. Create a new file in `connectors/` (e.g., `mysql.py`)
2. Inherit from `BaseConnector`
3. Implement required methods:
   - `_create_engine()`: Create SQLAlchemy engine
   - `get_connection_string()`: Build connection string
4. Add to `connectors/__init__.py`
5. Update `DatabaseType` enum in `config/schema.py`
6. Add connection handling in `profiling/core.py`

Example:

```python
from sqlalchemy import create_engine
from .base import BaseConnector

class MySQLConnector(BaseConnector):
    def _create_engine(self):
        return create_engine(self.get_connection_string())
    
    def get_connection_string(self):
        return f"mysql://{self.config.username}:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.database}"
```

## Adding a New Metric

1. Add metric logic to `MetricCalculator` in `profiling/metrics.py`
2. Add metric name to default metrics list in `config/schema.py`
3. Update documentation

Example:

```python
def _calculate_percentiles(self, table, col, sample_ratio):
    """Calculate percentile metrics."""
    with self.engine.connect() as conn:
        # Calculate p25, p50, p75
        query = select(
            func.percentile_cont(0.25).within_group(col.asc()).label('p25'),
            func.percentile_cont(0.50).within_group(col.asc()).label('p50'),
            func.percentile_cont(0.75).within_group(col.asc()).label('p75')
        ).select_from(table)
        
        result = conn.execute(query).fetchone()
        return {
            'p25': result.p25,
            'p50': result.p50,
            'p75': result.p75
        }
```

## Database Schema Evolution

When updating the storage schema:

1. Update `storage/schema.sql`
2. Update table creation in `storage/writer.py`
3. Consider migration strategy for existing deployments
4. Document breaking changes

## Performance Considerations

### Sampling
For large tables, use sampling:
```yaml
profiling:
  tables:
    - table: large_table
      sample_ratio: 0.1  # Profile 10% of rows
```

### Histogram Computation
Histograms can be expensive for large tables:
```yaml
profiling:
  compute_histograms: false  # Disable for performance
```

### Parallel Profiling
Future enhancement: Profile multiple tables in parallel using thread/process pools.

## Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect Profiling Results

```python
from baselinr.config.loader import ConfigLoader
from baselinr.profiling.core import ProfileEngine

config = ConfigLoader.load_from_file("config.yml")
engine = ProfileEngine(config)
results = engine.profile()

# Inspect results
for result in results:
    print(f"Table: {result.dataset_name}")
    for col in result.columns:
        print(f"  Column: {col['column_name']}")
        print(f"  Metrics: {col['metrics']}")
```

### Query Storage Directly

```sql
-- View all runs
SELECT * FROM baselinr_runs ORDER BY profiled_at DESC LIMIT 10;

-- View metrics for a column
SELECT metric_name, metric_value
FROM baselinr_results
WHERE dataset_name = 'customers'
  AND column_name = 'age'
  AND run_id = '<run-id>'
ORDER BY metric_name;
```

## Contributing Guidelines

1. **Code Style**: Use Black for formatting, follow PEP 8
2. **Type Hints**: Add type hints to all functions
3. **Documentation**: Include docstrings for all public APIs
4. **Tests**: Add tests for new features
5. **Commits**: Use clear, descriptive commit messages

## Release Process

1. Update version in `setup.py` and `pyproject.toml`
2. Update CHANGELOG.md
3. Run full test suite
4. Create git tag: `git tag v0.x.0`
5. Build package: `python setup.py sdist bdist_wheel`
6. Upload to PyPI: `twine upload dist/*`

## Future Enhancements

### Phase 2 (Planned)
- [ ] Alert system for drift detection
- [ ] Web dashboard for visualizing results
- [ ] Additional database connectors (MySQL, BigQuery, Redshift)
- [ ] Data quality rules engine
- [ ] Parallel profiling for multiple tables
- [ ] Profile comparison UI

### Phase 3 (Ideas)
- [ ] Machine learning-based anomaly detection
- [ ] Column correlation analysis
- [ ] PII detection
- [ ] Data lineage tracking
- [ ] Integration with data catalogs (DataHub, Amundsen)

## Getting Help

- Read the code! It's well-documented
- Check examples in `examples/`
- Look at tests in `tests/`
- Review issues on GitHub

## License

MIT License - see LICENSE file

