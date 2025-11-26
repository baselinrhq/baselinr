# dbt Package (Internal Testing Only)

**⚠️ This directory is for internal testing only. Not for user distribution.**

This directory contains a minimal dbt project used for testing baselinr's dbt integration features, specifically:
- Testing `dbt_ref` pattern resolution
- Testing `dbt_selector` pattern resolution
- Testing manifest.json parsing
- Integration tests

## Usage

This is used by the development team to test dbt integration locally:

```bash
# Activate venv (with Python 3.12)
.\.venv\Scripts\Activate.ps1  # or use activate.ps1 from repo root

# Generate manifest.json
cd dbt_package
dbt compile --profiles-dir .

# Test dbt refs/selectors in baselinr
cd ..
baselinr plan --config examples/config_dbt.yml
```

**Note**: You need Python 3.12 (not 3.14) for dbt compatibility. The venv should be created with:
```bash
py -3.12 -m venv .venv
```

## Structure

- `dbt_project.yml` - Basic dbt project configuration
- `models/` - Example dbt models for testing
- `schema.yml` - Model schema definitions with tags for selector testing

## Not Included

This directory does NOT include:
- Macros (not needed for testing refs/selectors)
- Scripts (not needed for testing)
- User-facing functionality

For user documentation, see [dbt Integration Guide](../docs/guides/DBT_INTEGRATION.md).
