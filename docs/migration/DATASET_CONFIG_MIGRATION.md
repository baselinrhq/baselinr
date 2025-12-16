# Dataset Config Migration (Inline → File-Based)

This guide provides a concise checklist to move from inline dataset configuration to the file-based `datasets/` directory.

## Prerequisites
- Backup your current `config.yml`.
- Ensure Baselinr CLI is installed and on your PATH.

## Recommended: Automated Migration

```bash
baselinr migrate-config --config config.yml --output-dir datasets
```

Options:
- `--config, -c` Path to main config (required)
- `--output-dir` Target datasets directory (default: `datasets`)
- `--no-backup` Skip creating a backup

What it does:
1) Backs up `config.yml` (unless `--no-backup`)
2) Extracts inline datasets into `datasets/` files
3) Converts schema-level and database-level profiling entries into `{schema}_schema.yml` / `{database}_database.yml`
4) Updates `config.yml` to reference the datasets directory
5) Removes deprecated inline sections that were migrated

## Manual Migration (Summary)
1) Create the datasets directory: `mkdir datasets`
2) For each inline dataset, create `datasets/{table}.yml` with `database`, `schema`, `table`, and feature blocks.
3) Convert `profiling.schemas[]` → `{schema}_schema.yml`; `profiling.databases[]` → `{database}_database.yml`.
4) Update `config.yml`:
   ```yaml
   datasets:
     datasets_dir: ./datasets
     auto_discover: true
     recursive: true
   ```
5) Remove migrated inline sections.

## Validation
- CLI: `baselinr validate-config --config config.yml`
- Dashboard: use the Datasets page to preview merged config and precedence.

## Troubleshooting

### Common Issues

#### Error: "ProfilingConfig no longer supports 'schemas' or 'databases' fields"
**Cause:** Your config still has `profiling.schemas[]` or `profiling.databases[]` sections.

**Solution:** Run the migration tool:
```bash
baselinr migrate-config --config config.yml
```

These sections are automatically converted to dataset files (`{schema}_schema.yml` or `{database}_database.yml`).

#### Error: "Validation rules must be defined in the datasets section"
**Cause:** You have `validation.rules[]` in the global validation section.

**Solution:** 
1. Run `baselinr migrate-config --config config.yml` to automatically migrate rules
2. Or manually move rules to the appropriate dataset files in the `datasets/` directory

#### Config key missing after migration
**Cause:** Configuration precedence - table-level files override schema/database defaults.

**Solution:** 
- Check the precedence order: table > schema > database > global
- Use the dashboard's "Preview" feature to see the merged configuration
- Verify the file naming matches: `{table}.yml`, `{schema}_schema.yml`, `{database}_database.yml`

#### Schema/database defaults not applied
**Cause:** File naming doesn't match the expected convention.

**Solution:** 
- Schema files must be named: `{schema_name}_schema.yml` (e.g., `public_schema.yml`)
- Database files must be named: `{database_name}_database.yml` (e.g., `warehouse_database.yml`)
- Table files should be: `{table_name}.yml` (e.g., `customers.yml`)

#### YAML syntax errors after migration
**Cause:** Invalid YAML syntax in migrated files.

**Solution:**
```bash
# Validate the config
baselinr validate-config --config config.yml

# Check specific file
yamllint datasets/customers.yml  # if you have yamllint installed
```

#### Tables not being profiled after migration
**Cause:** Table selection patterns may not be configured correctly.

**Solution:**
- Ensure `profiling.tables[]` contains table selection patterns (this is still valid)
- Or enable `profiling.table_discovery: true` for automatic discovery
- Check that dataset files have correct `database`, `schema`, and `table` fields

#### "No tables configured for profiling" error
**Cause:** No table patterns defined and table discovery is disabled.

**Solution:**
- Add tables to `profiling.tables[]` section, OR
- Enable `profiling.table_discovery: true`, OR
- Configure tables in dataset files (they will be auto-discovered if `datasets.auto_discover: true`)

### Getting Help

If you encounter issues not covered here:
1. Check the full migration guide: `docs/guides/DATASET_MIGRATION.md`
2. Review dataset configuration guide: `docs/guides/DATASET_CONFIGURATION.md`
3. Validate your config: `baselinr validate-config --config config.yml`
4. Use the dashboard's preview feature to inspect merged configurations

## Related Docs
- `docs/guides/DATASET_CONFIGURATION.md` - How to organize dataset configs
- `docs/guides/DATASET_MIGRATION.md` - Expanded migration scenarios and examples
- `docs/guides/CONFIGURATION.md` - Complete configuration reference

