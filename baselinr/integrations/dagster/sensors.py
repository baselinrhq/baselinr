"""
Plan-aware Dagster sensors for Baselinr.

Sensors monitor the profiling plan and trigger Dagster runs whenever the plan
changes (new tables, modified sampling rules, etc.).
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Mapping, Optional

try:
    from dagster import AssetKey, RunRequest, SensorDefinition, SensorEvaluationContext, sensor

    DAGSTER_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when Dagster missing
    DAGSTER_AVAILABLE = False

from ...config.loader import ConfigLoader
from ...planner import PlanBuilder, ProfilingPlan

logger = logging.getLogger(__name__)


def _safe_asset_suffix(name: str) -> str:
    """Mirror the sanitization logic used for Dagster asset names."""
    return name.replace(".", "_").replace("-", "_")


def _plan_snapshot(plan: ProfilingPlan) -> Dict[str, Any]:
    """Serialize relevant plan fields for cursor storage."""
    tables: Dict[str, Dict[str, Any]] = {}
    for table in plan.tables:
        tables[table.full_name] = {
            "name": table.name,
            "schema": table.schema,
            "metrics": table.metrics,
            "partition": table.partition_config,
            "sampling": table.sampling_config,
            "asset_suffix": _safe_asset_suffix(table.name),
        }

    payload = {
        "environment": plan.environment,
        "drift_strategy": plan.drift_strategy,
        "tables": tables,
    }
    payload["signature"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return payload


def _deserialize_cursor(cursor: Optional[str]) -> Optional[Dict[str, Any]]:
    if not cursor:
        return None
    try:
        result = json.loads(cursor)
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        logger.warning("Invalid Baselinr plan sensor cursor; resetting.")
        return None


def _serialize_cursor(snapshot: Dict[str, Any]) -> str:
    return json.dumps(snapshot, sort_keys=True)


def _detect_changed_tables(
    previous: Optional[Dict[str, Any]],
    current: Dict[str, Any],
) -> List[str]:
    """Return table names whose metadata changed."""
    if not previous:
        return list(current["tables"].keys())

    changed: List[str] = []
    prev_tables: Mapping[str, Mapping[str, Any]] = previous.get("tables", {})
    for table_name, current_payload in current["tables"].items():
        prev_payload = prev_tables.get(table_name)
        if prev_payload != current_payload:
            changed.append(table_name)
    return changed


if DAGSTER_AVAILABLE:

    def baselinr_plan_sensor(
        *,
        config_path: str,
        job_name: str,
        asset_prefix: str = "baselinr",
        sensor_name: Optional[str] = None,
        minimum_interval_seconds: int = 300,
        force_run: bool = False,
    ) -> SensorDefinition:
        """
        Build a plan-aware Dagster sensor for Baselinr assets.
        """

        name = sensor_name or f"{asset_prefix}_plan_sensor"

        @sensor(name=name, job_name=job_name, minimum_interval_seconds=minimum_interval_seconds)
        def _plan_sensor(context: SensorEvaluationContext):
            config = ConfigLoader.load_from_file(config_path)
            plan = PlanBuilder(config, config_file_path=config_path).build_plan()
            snapshot = _plan_snapshot(plan)
            previous = _deserialize_cursor(context.cursor)
            changed_tables = _detect_changed_tables(previous, snapshot)

            if force_run and not changed_tables:
                changed_tables = list(snapshot["tables"].keys())

            if not changed_tables:
                context.update_cursor(_serialize_cursor(snapshot))
                context.log.info("Baselinr plan unchanged; sensor idle.")
                return

            changed_entries = [snapshot["tables"][name] for name in changed_tables]
            metrics_total = sum(len(entry["metrics"]) for entry in changed_entries)

            asset_keys: List[AssetKey] = [
                AssetKey(f"{asset_prefix}_{entry['asset_suffix']}") for entry in changed_entries
            ]

            run_request = RunRequest(
                run_key=f"{job_name}:{snapshot['signature']}",
                asset_selection=asset_keys,
                run_config={
                    "baselinr": {
                        "environment": snapshot["environment"],
                        "tables": changed_tables,
                        "metrics_requested": metrics_total,
                        "drift_strategy": snapshot["drift_strategy"],
                    }
                },
                tags={
                    "baselinr/environment": snapshot["environment"],
                    "baselinr/plan_signature": snapshot["signature"],
                    "baselinr/changed_tables": json.dumps(changed_tables),
                    "baselinr/metrics_requested": str(metrics_total),
                },
            )

            context.update_cursor(_serialize_cursor(snapshot))
            yield run_request

        return _plan_sensor

else:  # pragma: no cover - exercised when Dagster missing

    def baselinr_plan_sensor(  # type: ignore[misc]
        *,
        config_path: str,
        job_name: str,
        asset_prefix: str = "baselinr",
        sensor_name: Optional[str] = None,
        minimum_interval_seconds: int = 300,
        force_run: bool = False,
    ) -> Any:
        raise ImportError("Dagster is not installed. Install with `pip install baselinr[dagster]`.")


__all__ = ["baselinr_plan_sensor"]
