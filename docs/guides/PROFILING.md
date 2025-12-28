# Profiling Configuration

This guide explains how to configure profiling defaults and contract-level overrides.

## Where to Configure

- **Global defaults:** `config.yml` under `profiling`
- **Contract-level overrides:** ODCS contracts in `contracts/` directory (see [ODCS Data Contracts](ODCS_DATA_CONTRACTS.md))

Example global defaults:
```yaml
profiling:
  default_sample_ratio: 1.0
  compute_histograms: true
  max_distinct_values: 1000
```

Example contract-level override:
```yaml
# contracts/orders.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: orders
    physicalName: sales.orders
    columns:
      - column: created_at
        partitionStatus: true
customProperties:
  - property: baselinr.sampling
    value:
      enabled: true
      fraction: 0.1
  - property: baselinr.partition.orders
    value:
      strategy: latest
```

## Precedence
1) Contract-level overrides (from ODCS contracts)
2) Global defaults (from `config.yml`)

## UI Workflow
- Use the **Profiling** page for global defaults.
- Use **Contracts** page for contract-level and column overrides.
- Preview merged configs in the Contracts page before saving.

## Validation
- CLI: `baselinr contracts validate --config config.yml`
- UI: Contracts page validation and preview

## Related
- `ODCS_DATA_CONTRACTS.md`
- `PARTITION_SAMPLING.md`
- `PROFILING_ENRICHMENT.md`

