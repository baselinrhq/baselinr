# Configuration Overview

This document summarizes how Baselinr configuration is organized and where to place different settings.

## Top-Level Structure

- `config.yml` — global defaults and service settings (profiling defaults, drift defaults, validation defaults, hooks, storage, UI settings).
- `contracts/` — ODCS data contract files (`.odcs.yaml`) that define dataset schemas, quality rules, and SLAs. Controlled by:
  ```yaml
  contracts:
    directory: ./contracts
    recursive: true
    validate_on_load: true
  ```
- `hooks/`, `storage`, `connections` — defined in `config.yml` as before.

## What Belongs Where

- **Global defaults:** Keep in `config.yml` (profiling defaults, drift defaults, validation defaults, anomaly defaults).
- **Dataset-specific overrides:** Use ODCS contracts in `contracts/` directory (see `ODCS_DATA_CONTRACTS.md`).
- **Column-level settings:** Define in ODCS contract `dataset[].columns[]` sections.
- **dbt imports:** When enabled, can be converted to ODCS contracts.

## Precedence (Most Specific Wins)
1) ODCS contract dataset-level configs (from `contracts/*.odcs.yaml`)
2) Global defaults in `config.yml`

Contract-level customProperties can override global defaults for specific tables.

## Recommended Workflow

1) Define global defaults in `config.yml`.
2) Create ODCS contracts for your datasets in `contracts/` directory.
3) Define quality rules, SLAs, and dataset-specific configs in contracts.
4) Use the dashboard Contracts page to view and manage contracts.

## Validation & Preview

- CLI: `baselinr validate-config --config config.yml`
- CLI: `baselinr contracts validate --config config.yml` to validate ODCS contracts
- Dashboard: Contracts page provides contract management and validation.

## Getting Started

- See `docs/guides/ODCS_DATA_CONTRACTS.md` for complete documentation on using ODCS contracts.

