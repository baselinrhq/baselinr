# dbt Integration Guide

Baselinr provides comprehensive integration with dbt (data build tool) to enable scalable profiling and drift detection within your dbt workflows.

## Overview

The dbt integration consists of two main components:

1. **dbt refs/selectors in baselinr configs**: Use dbt model references, selectors, and tags in baselinr table patterns
2. **Direct dbt model integration**: Add baselinr tests and profiling within dbt models via macros, tests, and post-hooks

## Installation

### Python Package

The dbt integration is included in the main baselinr package:

```bash
pip install baselinr
```

### dbt Package

Add the baselinr dbt package to your `packages.yml`:

```yaml
packages:
  - git: "https://github.com/baselinrhq/dbt-baselinr.git"
    revision: v0.1.0
```

Then install:

```bash
dbt deps
```

> **Note**: The dbt package is now in a [separate repository](https://github.com/baselinrhq/dbt-baselinr). If you were previously using `subdirectory: dbt_package` from the main baselinr repository, please migrate to the new repository. See the [dbt-baselinr repository](https://github.com/baselinrhq/dbt-baselinr) for the latest version and migration guide.

## Component 1: dbt Refs/Selectors in Baselinr Configs

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

## Component 2: Direct dbt Model Integration

### Post-Hook Profiling

Profile tables automatically after model execution. The `baselinr_profile` macro uses the same `profiling` configuration structure as baselinr config files:

```yaml
# schema.yml
models:
  - name: customers
    config:
      # Use profiling from base config file
      post-hook: "{{ baselinr_profile(target.schema, target.name) }}"
```

With custom profiling settings:

```yaml
models:
  - name: customers
    config:
      # Override metrics and partition per model
      post-hook: "{{ baselinr_profile(target.schema, target.name, profiling={'metrics': ['count', 'mean', 'stddev'], 'partition': {'key': 'created_date', 'strategy': 'latest'}}) }}"
  
  - name: events
    config:
      # Use sampling for large tables
      post-hook: "{{ baselinr_profile(target.schema, target.name, profiling={'sampling': {'enabled': true, 'fraction': 0.1}, 'metrics': ['count', 'histogram']}) }}"
```

Macro parameters:
- `schema_name`: Schema name (typically `target.schema`)
- `table_name`: Table name (typically `target.name`)
- `config_path`: Optional path to baselinr config file (for connection/storage settings)
- `profiling`: Dictionary matching the `profiling` section from baselinr config files (optional - uses base config if not provided)

**Configuration options** (same as baselinr config files):
- `metrics`: List of metrics to compute (e.g., `['count', 'mean', 'stddev', 'histogram']`)
- `compute_histograms`: Whether to compute histograms (boolean)
- `histogram_bins`: Number of histogram bins (integer)
- `max_distinct_values`: Maximum distinct values to track (integer)
- `partition`: Partition configuration (`key`, `strategy`, `recent_n`, etc.)
- `sampling`: Sampling configuration (`enabled`, `method`, `fraction`, `max_rows`)

If `profiling` is not provided, the macro uses the `profiling` settings from your baselinr config file.

**Note**: The `baselinr_profile` macro requires the baselinr Python package to be installed and a config file available. For databases that don't support executing shell commands in post-hooks, use dbt's `on-run-end` hook instead:

```yaml
# dbt_project.yml
on-run-end:
  - "python dbt_packages/baselinr/scripts/baselinr_profile.py --schema {{ target.schema }} --table {{ this }}"
```

### Drift Detection Tests

Add drift detection tests to your models. The `baselinr_drift` test uses the same `drift_detection` configuration structure as baselinr config files:

```yaml
# schema.yml
models:
  - name: customers
    columns:
      - name: customer_id
        tests:
          # Use drift_detection config (same structure as baselinr config files)
          - baselinr_drift:
              drift_detection:
                strategy: absolute_threshold
                absolute_threshold:
                  low_threshold: 5.0
                  medium_threshold: 15.0
                  high_threshold: 30.0
                baselines:
                  strategy: auto
      - name: email
        tests:
          # Override just the thresholds for this column
          - baselinr_drift:
              drift_detection:
                strategy: absolute_threshold
                absolute_threshold:
                  medium_threshold: 10.0
```

Test parameters:
- `drift_detection`: Dictionary matching the `drift_detection` section from baselinr config files (optional - uses base config if not provided)
- `config_path`: Optional path to baselinr config file (for connection/storage settings)

**Configuration options** (same as baselinr config files):
- `strategy`: `absolute_threshold`, `standard_deviation`, `statistical`, or `ml_based`
- `absolute_threshold`: `low_threshold`, `medium_threshold`, `high_threshold` (percentages)
- `standard_deviation`: `low_threshold`, `medium_threshold`, `high_threshold` (std devs)
- `baselines`: Baseline selection strategy (`auto`, `last_run`, `moving_average`, etc.)

If `drift_detection` is not provided, the test uses the `drift_detection` settings from your baselinr config file.

### Column-Level Configuration

Document baselinr configuration per column:

```yaml
models:
  - name: customers
    columns:
      - name: customer_id
        description: "{{ baselinr_config(metric='count', threshold=10.0) }}"
```

### Execution Order

When using both profiling post-hooks and drift tests on the same model, dbt executes them in this order:

1. **Model materialization** - The dbt model runs
2. **Post-hooks** - Profiling post-hook executes (synchronously)
3. **Tests** - Drift tests execute (can access profiling results)

The profiling post-hook runs **synchronously** to ensure results are written to storage before tests execute. The drift test automatically uses the latest profiling run for comparison.

**Important**: The profiling script blocks until profiling is complete and results are written to storage. This ensures that when the drift test runs, it can access the profiling results from the post-hook.

**Example**:
```yaml
models:
  - name: customers
    config:
      # Runs first (after model)
      post-hook: "{{ baselinr_profile(target.schema, target.name) }}"
    columns:
      - name: customer_id
        tests:
          # Runs second (after post-hook)
          - baselinr_drift:
              drift_detection:
                strategy: absolute_threshold
                absolute_threshold:
                  medium_threshold: 5.0
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

### Example 3: Full dbt Model with Profiling and Tests

```yaml
# schema.yml
models:
  - name: customers
    config:
      # Profile with custom metrics and partition
      post-hook: "{{ baselinr_profile(target.schema, target.name, profiling={'metrics': ['count', 'mean', 'stddev'], 'partition': {'key': 'created_date', 'strategy': 'latest'}}) }}"
    columns:
      - name: customer_id
        tests:
          - not_null
          - unique
          # Use drift_detection config structure (same as baselinr config files)
          - baselinr_drift:
              drift_detection:
                strategy: absolute_threshold
                absolute_threshold:
                  low_threshold: 5.0
                  medium_threshold: 15.0
                  high_threshold: 30.0
                baselines:
                  strategy: auto
      - name: email
        tests:
          - not_null
          # Override just the thresholds for this column
          - baselinr_drift:
              drift_detection:
                strategy: absolute_threshold
                absolute_threshold:
                  medium_threshold: 1.0
      - name: registration_date
        tests:
          # Use standard deviation strategy
          - baselinr_drift:
              drift_detection:
                strategy: standard_deviation
                standard_deviation:
                  low_threshold: 1.0
                  medium_threshold: 2.0
                  high_threshold: 3.0
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
4. **Test in Development**: Use drift tests in development to catch issues early
5. **Profile After Critical Models**: Use post-hooks for models that need immediate profiling

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

### Post-Hook Not Executing

**Issue**: Profiling post-hook doesn't run

**Solution**:
- Ensure baselinr Python package is installed
- Check that the config file path is correct
- For databases that don't support shell commands, use `on-run-end` hook instead
- Verify dbt has permission to execute the profiling script

## Advanced Usage

### Custom Script Paths

Set custom script paths via dbt variables:

```yaml
# dbt_project.yml
vars:
  baselinr_script_path: "custom/path/to/scripts/baselinr_profile.py"
```

### Async Profiling

For large tables, use async execution (if supported by your database):

```yaml
models:
  - name: large_table
    config:
      post-hook: "{{ baselinr_profile(target.schema, target.name, async_execution=true) }}"
```

### Multiple Config Files

Use different baselinr configs for different models:

```yaml
models:
  - name: customers
    config:
      post-hook: "{{ baselinr_profile(target.schema, target.name, config_path='configs/customers_baselinr.yml') }}"
  - name: orders
    config:
      post-hook: "{{ baselinr_profile(target.schema, target.name, config_path='configs/orders_baselinr.yml') }}"
```

## See Also

- [Baselinr Configuration Guide](CONFIGURATION.md)
- [Drift Detection Guide](DRIFT_DETECTION.md)
- [Profiling Guide](PROFILING.md)
- [dbt Documentation](https://docs.getdbt.com/)

