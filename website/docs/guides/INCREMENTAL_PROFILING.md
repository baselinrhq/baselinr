# Incremental Profiling Guide

Incremental profiling keeps Baselinr fast and cost‑efficient by skipping tables that have not changed and focusing work on the partitions that actually moved. This guide explains how it works, how to configure it, and how to monitor and troubleshoot runs.

---

## Why Incremental Profiling?

- **Cost control:** Avoid re‑scanning multi‑TB tables when the data is unchanged.
- **Faster SLAs:** Hourly/daily schedules become practical because only a subset of the portfolio is re‑profiled.
- **Smarter orchestration:** Sensors, CLI runs, and the dashboard can explain *why* a table ran (full, partial, sample) or was skipped.

---

## Architecture Overview

The implementation spans several new components:

| Component | Description | Key Files |
| --- | --- | --- |
| **Change detectors** | Connector‑specific metadata readers that return snapshot IDs, partition manifests, or CDC tokens. | `baselinr/incremental/change_detection.py`, `baselinr/connectors/*` |
| **State store** | Persists `snapshot_id`, last decision, row/byte estimates per table in `baselinr_table_state`. | `baselinr/incremental/state.py`, `baselinr/storage/schema*.sql` |
| **Incremental planner** | Compares current metadata vs. stored state, applies staleness and cost rules, and returns skip/partial/full/sample decisions. | `baselinr/incremental/planner.py`, `baselinr/planner.py` |
| **CLI/Dagster integration** | CLI now asks the planner for the tables to run; Dagster sensors can call the same API. | `baselinr/cli.py`, `baselinr/dagster_integration/*` |
| **Observability** | New `ProfilingSkipped` events, dashboard wiring, and warm‑cache surface area for skipped tables. | `baselinr/events/events.py`, `docs/dashboard/backend/README.md` |

---

## Configuration

Incremental profiling is disabled by default. Enable and tune it via the root `incremental` section:

```yaml
incremental:
  enabled: true

  change_detection:
    metadata_table: baselinr_table_state   # created automatically if storage.create_tables is true
    snapshot_ttl_minutes: 1440

  partial_profiling:
    enabled: true
    allow_partition_pruning: true
    max_partitions_per_run: 64
    mergeable_metrics:
      - count
      - null_count
      - min
      - max

  adaptive_scheduling:
    enabled: true
    default_interval_minutes: 1440
    min_interval_minutes: 60
    max_interval_minutes: 10080
    priority_overrides:
      "analytics.daily_orders": 180   # force updates every 3h

  cost_controls:
    enabled: true
    max_rows_scanned: 100000000
    fallback_strategy: sample         # sample | defer | full
    sample_fraction: 0.05
```

> **Tip:** Each connector may have its own detector options via `change_detection.connector_overrides` if you need to pass view names or custom metadata queries.

---

## Planner Workflow

1. **Sensor/CLI tick:** The CLI (and Dagster sensors) call `PlanBuilder.get_tables_to_run()` which delegates to the incremental planner.
2. **Staleness check:** If a table was profiled recently (`adaptive_scheduling`), it is skipped immediately.
3. **Change detection:** Warehouse metadata (snapshot IDs, pg_stat counters, BigQuery partition mtimes, etc.) is compared with the stored `snapshot_id`.
4. **Decision tree:**
   - **No change:** Emit `ProfilingSkipped` event (`reason=snapshot_match`) and reuse cached metrics.
   - **Changed partitions only:** Run in partial mode; partition filters are injected via the `specific_values` strategy.
   - **Cost exceeds budget:** Sample or defer per `cost_controls.fallback_strategy`.
   - **Otherwise:** Run a full profile.
5. **State write‑back:** After profiles complete, the CLI updates `baselinr_table_state` with the new `snapshot_id`, decision, row counts, bytes, and run ID so the next tick has the latest metadata.

---

## Change Detection Sources

| Warehouse | Metadata Used | Notes |
| --- | --- | --- |
| **Postgres/Redshift** | `pg_stat_all_tables` row counters, vacuum/analyze timestamps. | Detects inserts/updates/deletes without scanning data. |
| **Snowflake** | `INFORMATION_SCHEMA.TABLES` (row counts, `last_altered`). | Snapshot ID is derived from `last_altered`. |
| **BigQuery** | `INFORMATION_SCHEMA.TABLES/PARTITIONS` (last modified time + per‑partition rows). | Supports incremental runs per partition. |
| **Others** | Falls back to checksum of metadata; you can extend `DETECTOR_REGISTRY` with connector‑specific classes. |

When metadata is missing or unreliable, the planner automatically falls back to a full profile to guarantee correctness.

---

## Partial Profiling Mechanics

- Planner sets `partition.strategy = specific_values` with the changed partition IDs returned by the detector.
- Query builder now understands `specific_values` and constrains the partition column to that list.
- The profiler reuses cached metrics for untouched partitions, merging only the updated metrics before writing storage rows.
- `mergeable_metrics` controls which column metrics can be merged safely (counts, min/max, etc.).

---

## Cost Controls

Configure soft limits to cap expensive scans:

| Field | Behavior |
| --- | --- |
| `max_rows_scanned` / `max_bytes_scanned` | If estimates exceed the threshold, the planner uses the fallback strategy. |
| `fallback_strategy = sample` | Planner runs the table with sampling (using `cost_controls.sample_fraction`). |
| `fallback_strategy = defer` | Planner emits a deferred skip event. |
| `fallback_strategy = full` | Planner still runs the table but records the overage reason. |

Events (`profile_deferred_cost_cap`, `profile_sampled_cost_cap`) are emitted so dashboards can surface these decisions.

---

## Dagster Integration

1. Configure your Dagster sensor/op to run on a fixed cadence (e.g., hourly).
2. Inside the sensor call `PlanBuilder.get_tables_to_run()`; only materialize the tables whose decision is `full`, `partial`, or `sample`.
3. Forward `incremental_plan.to_summary()` to logging/metrics so you can observe skip/partial ratios over time.

This keeps the Dagster schedule simple while letting Baselinr decide how much work to do each tick.

---

## Observability & Dashboard

- `baselinr_table_state` is visible to the dashboard backend so the UI can explain why a table was skipped or partially profiled.
- New `ProfilingSkipped` events include `action`, `reason`, and `snapshot_id` for hook consumers.
- When a table is skipped, downstream consumers (Grafana, APIs) receive the cached metrics plus the timestamp of the last successful run.

See `docs/dashboard/backend/README.md` for the updated schema and sample queries.

---

## Troubleshooting Checklist

| Symptom | What to check |
| --- | --- |
| Tables never run | Ensure `incremental.enabled` is true and snapshots differ. Check `baselinr_table_state` for `decision=skip`. |
| Partial profiling ignored | Make sure `partition.key` is set (either explicitly or via metadata inference) so the planner can apply `specific_values`. |
| Cost deferrals too aggressive | Increase `max_rows_scanned` or switch fallback to `sample`. |
| Planner errors about missing metadata table | Set `storage.create_tables: true` or manually apply `baselinr/storage/schema*.sql`. |
| Dagster still running every table | Update your sensor/op to call `PlanBuilder.get_tables_to_run()` instead of iterating static table lists. |

---

## Testing & Validation

- Unit tests in `tests/test_incremental_planner.py` cover skip/partial/cost scenarios.
- End‑to‑end test plans: run the CLI twice against a warehouse, insert fresh rows in between, and verify state transitions in `baselinr_table_state`.

For additional context, review the implementation files linked above or open an issue with the metadata and planner logs from your deployment. Incremental profiling is designed to be opt‑in, so you can roll it out gradually by enabling it per environment or workspace. Happy profiling!
