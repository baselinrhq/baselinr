# Dataset Configuration Migration Guide

This guide explains how to migrate from inline dataset configuration to the new file-based directory structure.

## Overview

Baselinr now supports organizing dataset configurations in a modular file-based structure, similar to dbt projects. This provides better organization, version control, and scalability compared to inline configuration.

## When to Migrate

You should migrate to the file-based structure if:
- You have multiple dataset configurations
- You want better organization and maintainability
- You need to collaborate on dataset configs with a team
- You want to scale to many datasets

## Migration Methods

### Automated Migration (Recommended)

Use the `migrate-config` CLI command to automatically convert inline configs to files:

```bash
baselinr migrate-config --config config.yml --output-dir datasets
```

**Options:**
- `--config, -c`: Path to your configuration file (required)
- `--output-dir`: Directory name for dataset files (default: `datasets`)
- `--no-backup`: Skip creating a backup of the original config

**Example:**
```bash
# Migrate with default settings (creates backup)
baselinr migrate-config --config config.yml

# Migrate to custom directory
baselinr migrate-config --config config.yml --output-dir my_datasets

# Migrate without backup
baselinr migrate-config --config config.yml --no-backup
```

**What the migration tool does:**
1. Creates a backup of your original config file (unless `--no-backup` is used)
2. Extracts all inline dataset configs to individual YAML files
3. Migrates `profiling.schemas[]` entries to `{schema}_schema.yml` files
4. Migrates `profiling.databases[]` entries to `{database}_database.yml` files
5. Updates your main config file to reference the datasets directory
6. Removes `profiling.schemas` and `profiling.databases` from the config
7. Preserves all configuration settings

### Manual Migration

If you prefer to migrate manually:

1. **Create datasets directory:**
   ```bash
   mkdir datasets
   ```

2. **Extract dataset configs:**
   For each dataset in your `datasets.datasets` section, create a file:
   - `datasets/{table_name}.yml` for table-specific configs
   - `datasets/{schema_name}_schema.yml` for schema-level configs
   - `datasets/{database_name}_database.yml` for database-level configs

3. **Migrate profiling.schemas and profiling.databases:**
   If you have `profiling.schemas[]` or `profiling.databases[]` entries, migrate them to dataset files:
   - Convert each entry in `profiling.schemas[]` to `datasets/{schema}_schema.yml`
   - Convert each entry in `profiling.databases[]` to `datasets/{database}_database.yml`
   - Remove `profiling.schemas` and `profiling.databases` from your config

3. **Update main config:**
   Replace the inline `datasets` section with:
   ```yaml
   datasets:
     datasets_dir: ./datasets
     auto_discover: true
     recursive: true
   ```

## Migration Examples

### Before (Inline Configuration)

```yaml
# config.yml
environment: development
source:
  type: postgres
  host: localhost
  database: mydb
  username: user
  password: pass

storage:
  connection:
    type: postgres
    host: localhost
    database: mydb
    username: user
    password: pass
  results_table: results
  runs_table: runs

datasets:
  datasets:
    - table: customers
      schema: public
      profiling:
        partition:
          key: created_at
          strategy: latest
        sampling:
          enabled: true
          fraction: 0.1
      drift:
        strategy: statistical
    - table: orders
      schema: public
      profiling:
        partition:
          key: order_date
          strategy: latest
```

### After (File-Based Configuration)

**config.yml:**
```yaml
environment: development
source:
  type: postgres
  host: localhost
  database: mydb
  username: user
  password: pass

storage:
  connection:
    type: postgres
    host: localhost
    database: mydb
    username: user
    password: pass
  results_table: results
  runs_table: runs

datasets:
  datasets_dir: ./datasets
  auto_discover: true
  recursive: true
```

**datasets/customers.yml:**
```yaml
table: customers
schema: public
profiling:
  partition:
    key: created_at
    strategy: latest
  sampling:
    enabled: true
    fraction: 0.1
drift:
  strategy: statistical
```

**datasets/orders.yml:**
```yaml
table: orders
schema: public
profiling:
  partition:
    key: order_date
    strategy: latest
```

### Migrating profiling.schemas and profiling.databases

If you have schema-level or database-level configurations in `profiling.schemas[]` or `profiling.databases[]`, the migration tool will automatically convert them:

**Before:**
```yaml
profiling:
  schemas:
    - schema: analytics
      partition:
        strategy: latest
        key: date
      columns:
        - name: "*_id"
          drift:
            enabled: false
  databases:
    - database: warehouse
      sampling:
        enabled: true
        fraction: 0.05
```

**After:**
```yaml
profiling:
  tables:
    - select_schema: true
      schema: analytics
    - select_all_schemas: true
      database: warehouse

datasets:
  datasets_dir: ./datasets
  auto_discover: true
  recursive: true
```

**datasets/analytics_schema.yml:**
```yaml
schema: analytics
profiling:
  partition:
    strategy: latest
    key: date
  columns:
    - name: "*_id"
      drift:
        enabled: false
```

**datasets/warehouse_database.yml:**
```yaml
database: warehouse
profiling:
  sampling:
    enabled: true
    fraction: 0.05
```

## File Naming Conventions

The migration tool automatically generates filenames based on the dataset identifier:

- **Table-level configs:** `{table_name}.yml`
  - Example: `customers.yml`, `orders.yml`

- **Schema-level configs:** `{schema_name}_schema.yml`
  - Example: `public_schema.yml`, `analytics_schema.yml`

- **Database-level configs:** `{database_name}_database.yml`
  - Example: `warehouse_database.yml`

## Directory Structure

You can organize dataset files in a hierarchical structure:

```
config.yml
datasets/
  ├── customers.yml
  ├── orders.yml
  ├── analytics/
  │   ├── _schema.yml        # Schema-level config for analytics
  │   ├── events.yml
  │   └── metrics.yml
  └── warehouse/
      ├── _database.yml      # Database-level config
      └── staging/
          └── _schema.yml
```

## Verification

After migration, verify your configuration:

1. **Check that files were created:**
   ```bash
   ls -la datasets/
   ```

2. **Validate the configuration:**
   ```bash
   baselinr plan --config config.yml
   ```

3. **Test loading:**
   ```python
   from baselinr.config.loader import ConfigLoader
   
   config = ConfigLoader.load_from_file("config.yml")
   print(f"Loaded {len(config.datasets.datasets)} datasets")
   ```

## Troubleshooting

### Migration fails with "No inline dataset configs found"

This means your config doesn't have inline dataset configs. You may already be using the file-based structure, or you need to add dataset configs first.

### Files not being discovered

Check:
- The `datasets_dir` path is correct (relative to config file or absolute)
- Files match the `file_pattern` (default: `*.yml`)
- `recursive` is set to `true` if using subdirectories
- Files aren't excluded by `exclude_patterns`

### Configuration errors after migration

1. Check that all dataset files are valid YAML
2. Verify dataset identifiers (table, schema, database) are correct
3. Ensure the main config file references the datasets directory correctly

### Backup file location

Backup files are created in the same directory as your config file with the format:
```
{config_file}.backup.{timestamp}.{ext}
```

Example: `config.yml.backup.20240101_120000.yml`

## Best Practices

1. **Use descriptive filenames:** Match table/schema names for clarity
2. **Organize by schema/database:** Use subdirectories for logical grouping
3. **Version control:** Commit dataset files to version control
4. **Documentation:** Add comments in dataset files for complex configurations
5. **Backup before migration:** Always create backups (default behavior)

## Next Steps

After migration:
- Review generated files and organize as needed
- Update your team's workflow to edit dataset files directly
- Consider using schema-level or database-level configs for common settings
- Set up CI/CD to validate dataset configurations

## Final Notes

### After Migration

Once you've migrated to the file-based structure:

1. **Remove old config sections**: The migration tool automatically removes migrated sections, but verify:
   - `profiling.schemas[]` should be removed (migrated to `{schema}_schema.yml` files)
   - `profiling.databases[]` should be removed (migrated to `{database}_database.yml` files)
   - `validation.rules[]` should be removed (migrated to dataset files)
   - Inline `datasets.datasets[]` should be removed (migrated to individual files)

2. **Verify configuration**: Always validate after migration:
   ```bash
   baselinr validate-config --config config.yml
   ```

3. **Test profiling**: Run a test profile to ensure everything works:
   ```bash
   baselinr profile --dry-run
   ```

4. **Update workflows**: 
   - Update CI/CD pipelines to validate dataset files
   - Update team documentation to reference new file locations
   - Consider using the dashboard UI for managing dataset configs

### Important Reminders

- **`profiling.tables[]` is still valid**: This section is for table selection patterns, not dataset-specific configs. It remains in the main config file.
- **Global defaults stay in `config.yml`**: Only dataset-specific overrides go in the `datasets/` directory.
- **File naming matters**: Use exact naming conventions (`{table}.yml`, `{schema}_schema.yml`, `{database}_database.yml`).
- **Precedence is important**: Table-level configs override schema-level, which override database-level, which override global defaults.

## Related Documentation

- [Configuration Reference](../../website/docs/reference/CONFIG_REFERENCE.md) - Complete config reference
- [Dataset Configuration Guide](DATASET_CONFIGURATION.md) - Detailed dataset config guide
- [Best Practices Guide](BEST_PRACTICES.md) - Configuration best practices
