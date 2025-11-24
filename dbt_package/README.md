# dbt-baselinr

> **⚠️ DEPRECATED: This directory is deprecated.**
> 
> The dbt package has been moved to a separate repository: **[https://github.com/baselinrhq/dbt-baselinr](https://github.com/baselinrhq/dbt-baselinr)**
> 
> **Please migrate to the new repository.** See the [Migration Guide](#migration-from-monorepo) below for instructions.
> 
> This directory will remain for reference but will not receive updates.

---

dbt package for integrating Baselinr data profiling and drift detection with dbt models.

## Installation

### Option 1: Install from GitHub (Recommended)

Add this package to your `packages.yml`:

```yaml
packages:
  - git: "https://github.com/baselinrhq/dbt-baselinr.git"
    revision: v0.1.0  # or latest tag
```

Then run:

```bash
dbt deps
```

### Option 2: Install from dbt Hub (Coming Soon)

Once published to dbt Hub:

```yaml
packages:
  - package: baselinr/baselinr
    version: 0.1.0
```

## Requirements

- **dbt-core** >= 1.0.0
- **baselinr** (Python package) >= 0.3.0

Install the baselinr Python package:

```bash
pip install baselinr
```

## Usage

### Post-Hook Profiling

Profile tables automatically after model execution. Uses the same `profiling` configuration structure as baselinr config files:

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
      post-hook: "{{ baselinr_profile(target.schema, target.name, profiling={'metrics': ['count', 'mean'], 'partition': {'key': 'date', 'strategy': 'latest'}}) }}"
  
  - name: events
    config:
      # Use sampling for large tables
      post-hook: "{{ baselinr_profile(target.schema, target.name, profiling={'sampling': {'enabled': true, 'fraction': 0.1}, 'metrics': ['count', 'histogram']}) }}"
```

If `profiling` is not provided, the macro uses the `profiling` settings from your baselinr config file.

### Drift Detection Tests

Add drift detection tests to your models. Uses the same `drift_detection` configuration structure as baselinr config files:

```yaml
# schema.yml
models:
  - name: customers
    columns:
      - name: customer_id
        tests:
          - baselinr_drift:
              drift_detection:
                strategy: absolute_threshold
                absolute_threshold:
                  low_threshold: 5.0
                  medium_threshold: 15.0
                  high_threshold: 30.0
                baselines:
                  strategy: auto
```

If `drift_detection` is not provided, the test uses the `drift_detection` settings from your baselinr config file.

### Column-Level Configuration

Configure baselinr settings per column:

```yaml
models:
  - name: customers
    columns:
      - name: customer_id
        description: "{{ baselinr_config(metric='count', threshold=10.0) }}"
```

## Configuration

The package uses baselinr's standard configuration. You can:

1. Use a default config file (searches for `baselinr_config.yml` in project root)
2. Specify a custom config path in macros
3. Use environment variables for configuration

See [Baselinr documentation](https://baselinr.io/docs) for configuration details.

## Example Models

The package includes example models (`example_customers`, `example_orders`) that can be used for testing:

```bash
# Run example models
dbt run --select example_customers example_orders

# Test with baselinr profiling
dbt run --select example_customers
# Profiling will run automatically via post-hook

# Test drift detection
dbt test --select example_customers
```

**Note**: Example models are empty by default (`WHERE 1=0`). Populate them with test data for actual profiling and drift detection.

## Compatibility

| dbt-baselinr | baselinr (Python) |
|--------------|-------------------|
| 0.1.x        | >=0.3.0           |

## Migration from Monorepo

> **⚠️ IMPORTANT: If you're currently using this package from the monorepo, please migrate now.**

If you were previously using the dbt package from the main baselinr repository:

**Old installation (DEPRECATED):**
```yaml
packages:
  - git: "https://github.com/baselinrhq/baselinr.git"
    subdirectory: dbt_package  # ⚠️ This method is deprecated
```

**New installation (REQUIRED):**
```yaml
packages:
  - git: "https://github.com/baselinrhq/dbt-baselinr.git"
    revision: v0.1.0
```

Then run `dbt deps` to update.

**Why migrate?**
- ✅ Independent versioning and releases
- ✅ Faster installation (smaller repository)
- ✅ Better maintainability
- ✅ Future dbt Hub support
- ⚠️ This directory will not receive updates

## Resources

- [Baselinr Documentation](https://baselinr.io/docs)
- [dbt Integration Guide](https://baselinr.io/docs/guides/dbt-integration)
- [GitHub Repository](https://github.com/baselinrhq/dbt-baselinr)
- [Report Issues](https://github.com/baselinrhq/dbt-baselinr/issues)
