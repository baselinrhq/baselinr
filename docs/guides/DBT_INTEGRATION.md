# dbt Integration Guide

Baselinr provides comprehensive integration with dbt (data build tool) to enable scalable profiling and drift detection within your dbt workflows.

## Overview

Baselinr integrates with dbt by allowing you to use dbt model references and selectors directly in your baselinr configuration files. This enables you to profile dbt models without maintaining separate table lists.

## Installation

The dbt integration is included in the main baselinr package:

```bash
pip install baselinr
```

No additional dbt package installation is required. The integration works by reading dbt's `manifest.json` file to resolve model references and selectors.

## Using dbt Refs and Selectors in Baselinr Configs

### Using dbt Refs

Reference dbt models directly in your baselinr configuration:

```yaml
profiling:
  tables:
    - dbt_ref: customers
      dbt_project_path: ./dbt_project
    - dbt_ref: orders
      dbt_project_path: ./dbt_project
```

The `dbt_ref` field accepts:
- Simple model name: `"customers"`
- Package-qualified name: `"package.model_name"`

### Using dbt Selectors

Use dbt selector syntax to select multiple models:

```yaml
profiling:
  tables:
    - dbt_selector: tag:critical
      dbt_project_path: ./dbt_project
    - dbt_selector: config.materialized:table
      dbt_project_path: ./dbt_project
    - dbt_selector: tag:critical+tag:customer  # Union
    - dbt_selector: tag:critical,config.materialized:table  # Intersection
```

Supported selector syntax:
- `tag:tag_name` - Models with specific tag
- `config.materialized:table` - Models with specific materialization
- `name:model_name` - Specific model name
- `path:models/staging` - Models in specific path
- `package:package_name` - Models in package
- `+` - Union (OR logic)
- `,` - Intersection (AND logic)

### Configuration Options

```yaml
profiling:
  tables:
    - dbt_ref: customers
      dbt_project_path: ./dbt_project  # Path to dbt project root
      dbt_manifest_path: ./target/manifest.json  # Optional: explicit manifest path
      schema: analytics  # Optional: override schema
      partition:  # Optional: partition config
        key: date
        strategy: latest
      sampling:  # Optional: sampling config
        enabled: true
        fraction: 0.1
```

### Manifest Path Resolution

Baselinr will automatically detect the manifest.json file:

1. If `dbt_manifest_path` is provided, use it
2. If `dbt_project_path` is provided, look for `target/manifest.json`
3. Otherwise, raise an error

**Note**: You must run `dbt compile` or `dbt run` first to generate the manifest.json file.

## Running Profiling After dbt

Since dbt hooks can only execute SQL (not Python scripts), you cannot run baselinr profiling directly from dbt hooks. Instead, use one of these approaches:

### Option 1: Orchestrator (Recommended for Production)

Use your orchestrator (Airflow, Dagster, Prefect, etc.) to run profiling after `dbt run`:

```python
# Example: Airflow DAG
dbt_run = BashOperator(
    task_id='dbt_run',
    bash_command='dbt run'
)

baselinr_profile = BashOperator(
    task_id='baselinr_profile',
    bash_command='baselinr profile --config baselinr_config.yml'
)

dbt_run >> baselinr_profile
```

### Option 2: Script After dbt Run

Run a script after `dbt run` that reads `run_results.json` to find materialized models:

```bash
dbt run
python scripts/baselinr_run_profiling_for_models.py
```

This script automatically:
- Reads `target/run_results.json` to find successfully materialized models
- Reads `target/manifest.json` to get per-model configurations
- Runs profiling for each model

### Option 3: CI/CD Pipeline

Add profiling as a step in your CI/CD pipeline:

```yaml
# Example: GitHub Actions
- name: Run dbt models
  run: dbt run

- name: Profile models
  run: baselinr profile --config baselinr_config.yml
```

## Examples

### Example 1: Profile All Critical Models

```yaml
# baselinr_config.yml
profiling:
  tables:
    - dbt_selector: tag:critical
      dbt_project_path: ./dbt_project
```

### Example 2: Profile Specific Models with Partitioning

```yaml
profiling:
  tables:
    - dbt_ref: daily_events
      dbt_project_path: ./dbt_project
      partition:
        key: event_date
        strategy: latest
    - dbt_ref: hourly_metrics
      dbt_project_path: ./dbt_project
      partition:
        key: metric_hour
        strategy: recent_n
        recent_n: 24
```

### Example 3: Profile dbt Models with Partitioning

```yaml
# baselinr_config.yml
profiling:
  tables:
    - dbt_ref: customers
      dbt_project_path: ./dbt_project
      partition:
        key: created_date
        strategy: latest
      metrics:
        - count
        - mean
        - stddev
```

### Example 4: Using dbt Selectors for Scalable Profiling

```yaml
profiling:
  tables:
    # Profile all models tagged as critical
    - dbt_selector: tag:critical
      dbt_project_path: ./dbt_project
    
    # Profile all table-materialized models in staging
    - dbt_selector: config.materialized:table,path:models/staging
      dbt_project_path: ./dbt_project
    
    # Profile models with either tag
    - dbt_selector: tag:customer+tag:order
      dbt_project_path: ./dbt_project
```

## Best Practices

1. **Generate Manifest First**: Always run `dbt compile` or `dbt run` before using dbt patterns in baselinr configs
2. **Use Tags Strategically**: Tag your dbt models to enable scalable profiling (e.g., `tag:critical`, `tag:profile`)
3. **Combine with Pattern Matching**: Use dbt selectors for model selection, then apply baselinr filters (partitioning, sampling)
4. **Use Orchestrators**: Run profiling after `dbt run` using your orchestrator (Airflow, Dagster, etc.)
5. **Profile Critical Models**: Focus profiling on models tagged as critical or high-value

## Troubleshooting

### Manifest Not Found

**Error**: `dbt manifest not found: ...`

**Solution**: Run `dbt compile` or `dbt run` to generate the manifest.json file in the `target/` directory.

### dbt Ref Not Resolved

**Error**: `Could not resolve dbt ref: model_name`

**Solution**: 
- Ensure the model exists in your dbt project
- Check that the manifest.json is up to date
- Verify the model name matches exactly (case-sensitive)

### Selector Matches No Models

**Warning**: `dbt selector '...' matched no models`

**Solution**:
- Verify the selector syntax is correct
- Check that models have the specified tags/configs
- Use `dbt list --select <selector>` to test your selector

### Profiling Not Running After dbt

**Issue**: Profiling doesn't run after `dbt run`

**Solution**:
- Ensure baselinr Python package is installed
- Run profiling manually after `dbt run`: `baselinr profile --config baselinr_config.yml`
- Use an orchestrator to automate the workflow
- Check that `target/run_results.json` exists (generated by `dbt run`)

## Advanced Usage

### Per-Model Configuration

You can still configure profiling settings per model by using dbt selectors with different baselinr configs:

```yaml
# baselinr_config_critical.yml
profiling:
  tables:
    - dbt_selector: tag:critical
      dbt_project_path: ./dbt_project
      metrics:
        - count
        - mean
        - stddev
        - histogram

# baselinr_config_staging.yml
profiling:
  tables:
    - dbt_selector: path:models/staging
      dbt_project_path: ./dbt_project
      sampling:
        enabled: true
        fraction: 0.1
```

Then run with different configs:
```bash
baselinr profile --config baselinr_config_critical.yml
baselinr profile --config baselinr_config_staging.yml
```

## See Also

- [Baselinr Configuration Guide](CONFIGURATION.md)
- [Drift Detection Guide](DRIFT_DETECTION.md)
- [Profiling Guide](PROFILING.md)
- [dbt Documentation](https://docs.getdbt.com/)

