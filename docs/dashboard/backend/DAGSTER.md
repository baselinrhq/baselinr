# Baselinr × Dagster

Baselinr ships a first-class Dagster integration under `baselinr.integrations.dagster`. It turns your profiling config into Dagster assets, optional sensors, and a ready-to-run job so teams can orchestrate profiling alongside their existing data pipelines.

## Installation

```bash
pip install "baselinr[dagster]"
```

The extra ensures `dagster`, `dagster-webserver`, and their dependencies are present. If you already manage Dagster dependencies yourself you can install plain `baselinr` and rely on your environment’s Dagster packages.

## Quick Start

```python
# repo.py
from pathlib import Path
from baselinr.integrations.dagster import build_baselinr_definitions

CONFIG_PATH = Path(__file__).parent / "baselinr.yml"

defs = build_baselinr_definitions(
    config_path=str(CONFIG_PATH),
    asset_prefix="baselinr",
    job_name="baselinr_profile_all",
    enable_sensor=True,
)
```

`build_baselinr_definitions` wires up:

- A cached `BaselinrResource` so every asset shares the same parsed config.
- One asset per table pattern plus a summary asset.
- A pre-built asset job (`baselinr_profile_all` by default).
- An optional `baselinr_plan_sensor` that triggers runs when the plan changes.

Load `defs` from your Dagster repository file (e.g., `dagster_defs.py`) and start `dagster dev` as usual. Assets appear in the UI with environment tags, drift metadata, and per-table run materializations.

## Sensor Behavior

- `baselinr_plan_sensor` recalculates the profiling plan on each tick.
- The cursor stores a JSON signature of table metrics, sampling rules, and drift strategy.
- When new tables appear or metadata changes, the sensor emits a `RunRequest` that targets only the affected assets via `asset_selection`.
- Run metadata includes the changed tables and total metrics requested so you can filter in the Dagster UI.
- Pass `enable_sensor=False` to `build_baselinr_definitions` if you prefer manual or cron-triggered jobs. You can also instantiate the sensor directly via `baselinr_plan_sensor` to customize intervals or force runs.

## Customization

`create_profiling_assets` accepts optional overrides:

- `asset_name_prefix`: defaults to `baselinr`.
- `group_name`: defaults to `baselinr_profiling`.
- `default_tags`: merged onto every asset (e.g., `{"team": "data-quality"}`).
- `default_metadata`: appended to every asset’s Dagster metadata block.

`build_baselinr_definitions` forwards those overrides and supports toggling the sensor or supplying a different job name.

## Environment & Storage Notes

- The integration reads the same YAML config you use for the CLI. Ensure credentials/DSNs referenced in the config are reachable from your Dagster runtime.
- Result persistence uses the storage connection defined in the config. For local experimentation, `sqlite` works out of the box; for production use Postgres, Snowflake, etc., according to your storage settings.
- If you rely on environment variables (`BASELINR_*`) they’ll be resolved once per process thanks to the cached resource—restart Dagster when secrets change.

## Validation

Run `pytest tests/test_dagster_integration.py` to execute the Dagster-focused unit tests. If you have Dagster installed locally you can also run:

```bash
dagster dev -m repo  # or your module name
```

and confirm that assets, the profiling job, and the plan sensor all load successfully.
