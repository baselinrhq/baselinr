# Testing dbt Integration Locally

This guide explains how to test the dbt integration features locally during development.

## Prerequisites

1. **Install dbt-core**:
   ```bash
   pip install dbt-core dbt-postgres  # or dbt-snowflake, dbt-bigquery, etc.
   ```

2. **Start PostgreSQL** (if using postgres):
   ```bash
   cd docker
   docker compose up -d postgres
   ```

## Quick Test Setup

### 1. Create a Minimal dbt Project

```bash
mkdir test_dbt_project
cd test_dbt_project

# Create dbt_project.yml
cat > dbt_project.yml << 'EOF'
name: 'test_project'
version: '1.0.0'
config-version: 2
profile: 'test_profile'
EOF

# Create profiles directory
mkdir -p profiles
cat > profiles/profiles.yml << 'EOF'
test_profile:
  outputs:
    dev:
      type: postgres
      host: localhost
      port: 5433
      user: baselinr
      password: baselinr
      dbname: baselinr
      schema: public
  target: dev
EOF

# Create models directory
mkdir models

# Create a simple model
cat > models/customers.sql << 'EOF'
SELECT 
  1 as customer_id,
  'test@example.com' as email,
  '2024-01-01'::date as registration_date
EOF

# Create schema.yml with tags
cat > models/schema.yml << 'EOF'
version: 2
models:
  - name: customers
    description: "Test customer model"
    tags:
      - critical
      - customer
    config:
      materialized: table
EOF
```

### 2. Generate dbt Manifest

```bash
cd test_dbt_project
export DBT_PROFILES_DIR=./profiles
dbt compile
```

This creates `target/manifest.json` which baselinr uses to resolve dbt refs and selectors.

## Testing dbt Manifest Parsing

### Python Script

```python
from baselinr.integrations.dbt import DBTManifestParser

# Load manifest
parser = DBTManifestParser(
    manifest_path="./test_dbt_project/target/manifest.json"
)
manifest = parser.load_manifest()

# Resolve a dbt ref
schema, table = parser.resolve_ref("customers")
print(f"Resolved 'customers' to: {schema}.{table}")
# Output: Resolved 'customers' to: public.customers

# Get models by tag
models = parser.get_models_by_tag("critical")
print(f"Found {len(models)} models with 'critical' tag")
# Output: Found 1 models with 'critical' tag
```

### Run Tests

```bash
pytest tests/test_dbt_integration.py::TestDBTManifestParser -v
```

## Testing dbt Selector Resolution

```python
from baselinr.integrations.dbt import DBTManifestParser, DBTSelectorResolver

parser = DBTManifestParser(
    manifest_path="./test_dbt_project/target/manifest.json"
)
parser.load_manifest()

resolver = DBTSelectorResolver(parser)

# Test tag selector
models = resolver.resolve_selector("tag:critical")
print(f"Found {len(models)} models with tag:critical")

# Test config selector
models = resolver.resolve_selector("config.materialized:table")
print(f"Found {len(models)} table-materialized models")

# Test union selector
models = resolver.resolve_selector("tag:critical+tag:customer")
print(f"Found {len(models)} models with either tag")

# Test intersection selector
models = resolver.resolve_selector("tag:critical,config.materialized:table")
print(f"Found {len(models)} models matching both criteria")
```

## Testing dbt Patterns in Baselinr Config

### 1. Create Config with dbt Patterns

```yaml
# config_dbt_test.yml
environment: development

source:
  type: postgres
  host: localhost
  port: 5433
  database: baselinr
  username: baselinr
  password: baselinr
  schema: public

storage:
  connection:
    type: postgres
    host: localhost
    port: 5433
    database: baselinr
    username: baselinr
    password: baselinr
    schema: public
  results_table: baselinr_results
  runs_table: baselinr_runs
  create_tables: true

profiling:
  tables:
    # Test dbt_ref
    - dbt_ref: customers
      dbt_manifest_path: ./test_dbt_project/target/manifest.json
    
    # Test dbt_selector
    - dbt_selector: tag:critical
      dbt_manifest_path: ./test_dbt_project/target/manifest.json
```

### 2. Test Pattern Expansion

```python
from baselinr import BaselinrClient

client = BaselinrClient(config_path="config_dbt_test.yml")

# Build plan (expands dbt patterns)
plan = client.plan()
print(f"Will profile {plan.total_tables} tables")

for table in plan.tables:
    print(f"  - {table.full_name}")
```

### 3. Test Profiling

```python
# Profile tables resolved from dbt patterns
results = client.profile()
for result in results:
    print(f"Profiled {result.dataset_name}: {len(result.columns)} columns")
```

## Testing dbt Integration

### 1. Test dbt Refs/Selectors

The dbt integration allows you to use dbt model references and selectors in baselinr configs. To test:

1. Set up a dbt project with some models
2. Run `dbt compile` or `dbt run` to generate `manifest.json`
3. Create a baselinr config with dbt refs:

```yaml
profiling:
  tables:
    - dbt_ref: customers
      dbt_project_path: ./dbt_project
```

4. Run profiling: `baselinr profile --config baselinr_config.yml`

> **Note**: dbt hooks can only execute SQL, not Python scripts. Use orchestrators to run profiling after `dbt run`.

### 2. Verify Profiling Results

After running profiling, check the results:

```python
from baselinr import BaselinrClient
client = BaselinrClient()
runs = client.query_runs(table="customers", limit=1)
print(f"Latest run: {runs[0]}")
```

## Integration with Docker

The docker setup includes PostgreSQL which can be used for dbt testing:

```bash
# Start PostgreSQL
cd docker
docker compose up -d postgres

# Use in dbt profiles.yml
# host: localhost
# port: 5433
# user: baselinr
# password: baselinr
# dbname: baselinr
```

## Troubleshooting

### Manifest Not Found

**Error**: `dbt manifest not found`

**Solution**: Run `dbt compile` or `dbt run` first to generate `target/manifest.json`

### dbt Ref Not Resolved

**Error**: `Could not resolve dbt ref: model_name`

**Solution**:
- Ensure model exists in dbt project
- Check manifest.json is up to date
- Verify model name matches exactly (case-sensitive)

### Selector Matches No Models

**Warning**: `dbt selector '...' matched no models`

**Solution**:
- Verify selector syntax
- Check models have specified tags/configs
- Test selector with `dbt list --select <selector>`

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'baselinr.integrations.dbt'`

**Solution**:
- Ensure baselinr is installed: `pip install -e .`
- Check Python path includes baselinr package
- Verify `baselinr/integrations/dbt/__init__.py` exists

## Running Full Integration Test

```bash
# Run all dbt integration tests
pytest tests/test_dbt_integration.py -v

# Run specific test class
pytest tests/test_dbt_integration.py::TestDBTManifestParser -v

# Run with coverage
pytest tests/test_dbt_integration.py --cov=baselinr.integrations.dbt
```

