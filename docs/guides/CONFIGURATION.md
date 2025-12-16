# Configuration Overview

This document summarizes how Baselinr configuration is organized and where to place different settings.

## Top-Level Structure

- `config.yml` — global defaults and service settings (profiling defaults, drift defaults, validation defaults, hooks, storage, UI settings).
- `datasets/` — dataset-specific configuration files (table, schema, database). Controlled by:
  ```yaml
  datasets:
    datasets_dir: ./datasets
    auto_discover: true
    recursive: true
  ```
- `hooks/`, `storage`, `connections` — defined in `config.yml` as before.

## What Belongs Where

- **Global defaults:** Keep in `config.yml` (profiling defaults, drift defaults, validation defaults, anomaly defaults).
- **Dataset-specific overrides:** Use files under `datasets/` (see `DATASET_CONFIGURATION.md`).
- **Column-level settings:** Place under the table file’s `columns` section.
- **dbt imports:** When enabled, imported models land in `datasets/` files.

## Precedence (Most Specific Wins)
1) Table file (`datasets/{table}.yml`)
2) Schema file (`datasets/{schema}_schema.yml`)
3) Database file (`datasets/{database}_database.yml`)
4) Global defaults in `config.yml`

Column-level rules follow the same hierarchy inside a table file.

## Recommended Workflow

1) Define global defaults in `config.yml`.
2) Create database or schema files for broad defaults.
3) Add table files for specific datasets and column overrides.
4) Use the dashboard Datasets page to preview merged configs and validate.

## Validation & Preview

- CLI: `baselinr validate-config --config config.yml`
- Dashboard: Datasets page provides merged preview, precedence view, and validation.

## Migration

- Use `baselinr migrate-config --config config.yml --output-dir datasets` to convert inline configs.
- See `docs/migration/DATASET_CONFIG_MIGRATION.md` for step-by-step guidance.

