"""
Event emission utilities for Airflow integration.

These utilities allow ProfileMesh operators to emit structured events
via Airflow's logging and XCom mechanisms.
"""

import logging
from typing import Any, Dict, Optional

try:
    from airflow.utils.context import Context

    AIRFLOW_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when Airflow missing
    AIRFLOW_AVAILABLE = False
    Context = dict  # type: ignore

logger = logging.getLogger(__name__)


def emit_profiling_event(
    context: Context,
    event_type: str,
    **event_data: Any,
) -> None:
    """
    Emit a ProfileMesh event via Airflow logging and XCom.

    Similar to Dagster's event emission, but adapted for Airflow's
    execution model.

    Args:
        context: Airflow execution context.
        event_type: Type of event (e.g., 'profiling_started', 'profiling_completed').
        **event_data: Additional event metadata.

    Example:
        ```python
        emit_profiling_event(
            context=context,
            event_type='profiling_completed',
            dataset_name='users',
            row_count=1000,
        )
        ```
    """
    if not AIRFLOW_AVAILABLE:
        return

    event_payload = {
        "event_type": event_type,
        "task_id": context.get("task_instance", {}).task_id if "task_instance" in context else None,
        "dag_id": context.get("dag", {}).dag_id if "dag" in context else None,
        "execution_date": str(context.get("execution_date", "")),
        **event_data,
    }

    # Log structured event
    logger.info(f"ProfileMesh Event: {event_type}", extra={"event_data": event_payload})

    # Store in XCom for potential downstream processing
    ti = context.get("ti")
    if ti:
        # Append to list of events
        existing_events = ti.xcom_pull(
            task_ids=ti.task_id,
            key="profilemesh_events",
            default=[],
        )
        existing_events.append(event_payload)
        ti.xcom_push(key="profilemesh_events", value=existing_events)


__all__ = ["emit_profiling_event"]
