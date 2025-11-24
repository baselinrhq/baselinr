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

## Using dbt Package

### 1. Install dbt Package

In your dbt project's `packages.yml`:

```yaml
packages:
  - git: "https://github.com/baselinrhq/baselinr.git"
    subdirectory: dbt_package
```

Then:
```bash
dbt deps
```

### 2. Test Post-Hook Profiling

```yaml
# models/schema.yml
models:
  - name: customers
    config:
      post-hook: "{{ baselinr_profile(target.schema, target.name) }}"
```

Run the model:
```bash
dbt run --select customers
```

### 3. Test Drift Detection

```yaml
# models/schema.yml
models:
  - name: customers
    columns:
      - name: customer_id
        tests:
          - baselinr_drift:
              metric: count
              threshold: 5.0
```

Run tests:
```bash
dbt test --select customers
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

### dbt Package Not Found

If dbt can't find the baselinr package:
- Run `dbt deps` to install packages
- Check `dbt_packages/` directory exists
- Verify git URL in `packages.yml`

## Full Example

See `docs/development/DBT_TESTING.md` for a complete walkthrough with examples.

