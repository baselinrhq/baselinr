"""
Plan-aware Airflow sensors for ProfileMesh.

Sensors monitor the profiling plan and trigger DAG runs whenever the plan
changes (new tables, modified sampling rules, etc.).
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Mapping, Optional

try:
    from airflow.models import Variable
    from airflow.sensors.base import BaseSensorOperator
    from airflow.utils.context import Context
    from airflow.utils.trigger_rule import TriggerRule

    AIRFLOW_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when Airflow missing
    AIRFLOW_AVAILABLE = False
    BaseSensorOperator = object  # type: ignore
    Context = dict  # type: ignore
    TriggerRule = object  # type: ignore
    Variable = object  # type: ignore

from ...config.loader import ConfigLoader
from ...planner import PlanBuilder, ProfilingPlan

logger = logging.getLogger(__name__)


def _safe_table_name(name: str) -> str:
    """Mirror the sanitization logic used for task IDs."""
    return name.replace(".", "_").replace("-", "_")


def _plan_snapshot(plan: ProfilingPlan) -> Dict[str, Any]:
    """
    Serialize relevant plan fields for cursor storage.

    This matches the Dagster sensor's snapshot logic to maintain
    consistent plan change detection.
    """
    tables: Dict[str, Dict[str, Any]] = {}
    for table in plan.tables:
        tables[table.full_name] = {
            "name": table.name,
            "schema": table.schema,
            "metrics": table.metrics,
            "partition": table.partition_config,
            "sampling": table.sampling_config,
            "task_suffix": _safe_table_name(table.name),
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
    """Deserialize cursor from Airflow Variable storage."""
    if not cursor:
        return None
    try:
        return json.loads(cursor)
    except json.JSONDecodeError:
        logger.warning("Invalid ProfileMesh plan sensor cursor; resetting.")
        return None


def _serialize_cursor(snapshot: Dict[str, Any]) -> str:
    """Serialize snapshot to JSON for storage."""
    return json.dumps(snapshot, sort_keys=True)


def _detect_changed_tables(
    previous: Optional[Dict[str, Any]],
    current: Dict[str, Any],
) -> List[str]:
    """
    Return table names whose metadata changed.

    This matches the Dagster sensor's change detection logic.
    """
    if not previous:
        return list(current["tables"].keys())

    changed: List[str] = []
    prev_tables: Mapping[str, Mapping[str, Any]] = previous.get("tables", {})
    for table_name, current_payload in current["tables"].items():
        prev_payload = prev_tables.get(table_name)
        if prev_payload != current_payload:
            changed.append(table_name)
    return changed


if AIRFLOW_AVAILABLE:

    class ProfileMeshPlanSensor(BaseSensorOperator):
        """
        Sensor that monitors ProfileMesh plan changes.

        This sensor checks the profiling plan configuration and triggers
        when changes are detected (new tables, modified sampling, etc.).
        Similar to the Dagster plan sensor.

        Args:
            config_path: Path to ProfileMesh configuration file.
            cursor_variable: Airflow Variable name for storing cursor state.
            poke_interval: How often to check for changes (seconds).
            timeout: Sensor timeout (seconds).
            mode: 'poke' or 'reschedule' (default: poke).

        Example:
            ```python
            plan_sensor = ProfileMeshPlanSensor(
                task_id='monitor_plan_changes',
                config_path='/path/to/config.yml',
                poke_interval=300,  # Check every 5 minutes
            )
            ```
        """

        template_fields = ("config_path",)
        ui_color = "#FFA726"  # Orange color

        def __init__(
            self,
            *,
            config_path: str,
            cursor_variable: Optional[str] = None,
            **kwargs,
        ):
            super().__init__(**kwargs)
            self.config_path = config_path
            self.cursor_variable = cursor_variable or "profilemesh_plan_cursor"

        def poke(self, context: Context) -> bool:
            """
            Check if the profiling plan has changed.

            Returns:
                True if plan changed (triggers downstream tasks).
                False if plan unchanged (continues poking).
            """
            # Load current plan
            config = ConfigLoader.load_from_file(self.config_path)
            plan = PlanBuilder(config).build_plan()
            current_snapshot = _plan_snapshot(plan)

            # Load previous plan from Airflow Variable
            try:
                previous_cursor = Variable.get(self.cursor_variable, default_var=None)
                previous_snapshot = _deserialize_cursor(previous_cursor)
            except Exception as e:
                logger.warning(f"Failed to load cursor from Variable: {e}")
                previous_snapshot = None

            # Detect changes
            changed_tables = _detect_changed_tables(previous_snapshot, current_snapshot)

            if not changed_tables:
                logger.info("ProfileMesh plan unchanged; sensor idle.")
                return False

            # Plan changed - store metadata and trigger
            logger.info(f"ProfileMesh plan changed: {len(changed_tables)} table(s) affected")

            changed_entries = [
                current_snapshot["tables"][name] for name in changed_tables
            ]
            metrics_total = sum(len(entry["metrics"]) for entry in changed_entries)

            # Store new cursor
            try:
                Variable.set(self.cursor_variable, _serialize_cursor(current_snapshot))
            except Exception as e:
                logger.error(f"Failed to update cursor Variable: {e}")

            # Push metadata to XCom for downstream tasks
            context["ti"].xcom_push(
                key="plan_change_metadata",
                value={
                    "environment": current_snapshot["environment"],
                    "changed_tables": changed_tables,
                    "metrics_requested": metrics_total,
                    "drift_strategy": current_snapshot["drift_strategy"],
                    "plan_signature": current_snapshot["signature"],
                },
            )

            logger.info(
                f"Plan changed: {changed_tables}, "
                f"metrics: {metrics_total}, "
                f"signature: {current_snapshot['signature'][:8]}..."
            )

            return True


else:  # pragma: no cover - exercised when Airflow missing

    class ProfileMeshPlanSensor:
        """Stub sensor exposed when Airflow is unavailable."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "Airflow is not installed. Install with `pip install profilemesh[airflow]`."
            )


__all__ = ["ProfileMeshPlanSensor"]
