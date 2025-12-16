# Profiling Configuration

This guide explains how to configure profiling defaults and dataset-level overrides.

## Where to Configure

- **Global defaults:** `config.yml` under `profiling`
- **Dataset-specific overrides:** `datasets/{table}.yml` (recommended)
- **Schema/database defaults:** `{schema}_schema.yml`, `{database}_database.yml`

Example global defaults:
```yaml
profiling:
  default_sample_ratio: 1.0
  compute_histograms: true
  max_distinct_values: 1000
```

Example dataset override:
```yaml
# datasets/orders.yml
database: warehouse
schema: sales
table: orders

profiling:
  sampling:
    enabled: true
    fraction: 0.1
  partition:
    key: created_at
    strategy: latest
  columns:
    - name: order_total
      metrics: [mean, max, min]
```

## Precedence
1) Table file overrides
2) Schema file overrides
3) Database file overrides
4) Global defaults

## UI Workflow
- Use the **Profiling** page for global defaults.
- Use **Datasets → Dataset Detail** for per-dataset and column overrides.
- Preview merged configs and precedence in the Datasets page before saving.

## Validation
- CLI: `baselinr validate-config --config config.yml`
- UI: Datasets page validation and merged preview

## Related
- `DATASET_CONFIGURATION.md`
- `PARTITION_SAMPLING.md`
- `PROFILING_ENRICHMENT.md`

