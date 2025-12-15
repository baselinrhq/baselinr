# Dataset Configuration Files

This directory contains dataset-level configuration files organized in a modular structure.

## File Structure

- `customers.yml` - Table-specific configuration for the `customers` table
- `analytics_schema.yml` - Schema-level configuration for the `analytics` schema
- `warehouse_database.yml` - Database-level configuration for the `warehouse` database

## File Naming Conventions

- `{table_name}.yml` - Table-specific configs
- `{schema_name}_schema.yml` - Schema-level configs
- `{database_name}_database.yml` - Database-level configs

## Configuration Precedence

Configurations are merged with the following precedence (highest to lowest):
1. Table-level config (most specific)
2. Schema-level config
3. Database-level config
4. Global config defaults

## Usage

The main `config.yml` file references this directory:

```yaml
datasets:
  datasets_dir: ./datasets
  auto_discover: true
  recursive: true
```

All YAML files in this directory (and subdirectories if `recursive: true`) will be automatically discovered and loaded.
