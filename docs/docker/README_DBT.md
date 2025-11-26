# Testing dbt Integration with Docker

This guide explains how to test the dbt integration using the Docker development environment.

## Quick Start

### 1. Start PostgreSQL

```bash
cd docker
docker compose up -d postgres
```

PostgreSQL will be available at:
- **Host**: `localhost`
- **Port**: `5433`
- **Database**: `baselinr`
- **User**: `baselinr`
- **Password**: `baselinr`

### 2. Install dbt

```bash
pip install dbt-core dbt-postgres
```

### 3. Create Test dbt Project

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

# Create models
mkdir models
cat > models/customers.sql << 'EOF'
SELECT 
  1 as customer_id,
  'test@example.com' as email,
  '2024-01-01'::date as registration_date
EOF

cat > models/schema.yml << 'EOF'
version: 2
models:
  - name: customers
    tags: [critical]
    config:
      materialized: table
EOF
```

### 4. Generate Manifest

```bash
cd test_dbt_project
export DBT_PROFILES_DIR=./profiles
dbt compile
```

This creates `target/manifest.json` needed by baselinr.

### 5. Test with Baselinr

Create a baselinr config:

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
    - dbt_ref: customers
      dbt_manifest_path: ./test_dbt_project/target/manifest.json
```

Test it:

```bash
# Plan what will be profiled
baselinr plan --config config_dbt_test.yml

# Profile the table
baselinr profile --config config_dbt_test.yml
```

## Using dbt with Baselinr

### 1. Use dbt Refs/Selectors in Baselinr Config

Reference dbt models directly in your baselinr configuration:

```yaml
profiling:
  tables:
    - dbt_ref: customers
      dbt_project_path: ./dbt_project
    - dbt_selector: tag:critical
      dbt_project_path: ./dbt_project
```

> **Note**: dbt hooks can only execute SQL, not Python scripts. Run profiling after `dbt run` using an orchestrator or manually. See the [dbt Integration Guide](../guides/DBT_INTEGRATION.md) for details.

### 2. Verify Profiling

After running profiling, verify the results were stored:

```python
from baselinr import BaselinrClient
client = BaselinrClient()
runs = client.query_runs(table="customers", limit=1)
print(f"Latest run: {runs[0]}")
```

## Troubleshooting

### Connection Issues

If dbt can't connect to PostgreSQL:
- Verify PostgreSQL is running: `docker compose ps`
- Check port: Should be `5433` (not `5432`)
- Test connection: `psql -h localhost -p 5433 -U baselinr -d baselinr`

### Manifest Not Found

If baselinr can't find the manifest:
- Run `dbt compile` first
- Check path: `./test_dbt_project/target/manifest.json`
- Use absolute path if relative path doesn't work

### dbt Integration Issues

If baselinr can't find dbt manifest:
- Run `dbt compile` or `dbt run` to generate `manifest.json`
- Check that `dbt_project_path` in config points to your dbt project root
- Verify git URL in `packages.yml`

## Full Example

See `docs/development/DBT_TESTING.md` for a complete walkthrough with examples.

