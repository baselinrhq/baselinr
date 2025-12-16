# Dataset Configuration Guide

This guide explains how to organize dataset configuration in Baselinr using the file-based `datasets/` directory and how those configs interact with global settings.

## Directory Structure

- `config.yml` — global defaults only (profiling, drift, validation, anomaly)
- `datasets/` — dataset-specific files (per table, schema, or database)

```yaml
# config.yml
datasets:
  datasets_dir: ./datasets
  auto_discover: true
  recursive: true
```

**File naming conventions**
- `{table}.yml` — table-level config
- `{schema}_schema.yml` — schema-level config
- `{database}_database.yml` — database-level config

## Configuration Precedence

Highest wins:
1) Table file  
2) Schema file  
3) Database file  
4) Global defaults in `config.yml`

Column configs inside a table file override column defaults in broader scopes.

## Dataset File Examples

```yaml
# datasets/customers.yml (table-level)
database: warehouse
schema: public
table: customers

profiling:
  sampling:
    enabled: true
    fraction: 0.1
  columns:
    - name: email
      drift:
        enabled: true

validation:
  rules:
    - type: format
      column: email
      pattern: '^[^@]+@[^@]+\.[^@]+$'
```

```yaml
# datasets/analytics_schema.yml (schema-level)
database: warehouse
schema: analytics

profiling:
  default_sample_ratio: 0.05
```

```yaml
# datasets/warehouse_database.yml (database-level)
database: warehouse

drift:
  strategy: absolute_threshold
  absolute_threshold:
    low_threshold: 5.0
```

## Inline vs File-Based

- **Recommended:** File-based (under `datasets/`) for clarity, version control, and scaling to many datasets.
- **Inline support:** Inline datasets remain supported, but new work should prefer files. Inline configs do not get precedence over table files; files still win.

## Common Tasks

- **Add a new dataset:** create `datasets/{table}.yml` with `database`, `schema`, and `table` plus feature blocks (`profiling`, `drift`, `validation`, `anomaly`, `columns`).
- **Schema-wide defaults:** use `{schema}_schema.yml` to apply to all tables in that schema.
- **Database-wide defaults:** use `{database}_database.yml` for coarse defaults.
- **Preview & validation:** use the dashboard Datasets page to preview merged config, view precedence, and validate before saving.

## Testing Your Configs

- Run `baselinr validate-config --config config.yml` to validate schema and YAML.
- Use the dashboard Datasets page to preview merged configs and see source precedence.

## Migration Notes

- The CLI `migrate-config` command can convert inline datasets to files and create backups.
- See `docs/guides/DATASET_MIGRATION.md` or `docs/migration/DATASET_CONFIG_MIGRATION.md` for step-by-step instructions and edge cases.

