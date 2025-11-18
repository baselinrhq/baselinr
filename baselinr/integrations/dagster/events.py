"""
Event emission for Dagster integration.

Provides structured event logging for profiling activities
in Dagster pipelines.
"""

import logging
from typing import Any, Optional

try:

    DAGSTER_AVAILABLE = True
except ImportError:
    DAGSTER_AVAILABLE = False

logger = logging.getLogger(__name__)


def emit_profiling_event(context: Optional[Any], event_type: str, dataset_name: str, **kwargs):
    """
    Emit a profiling event.

    Args:
        context: Dagster execution context (if available)
        event_type: Type of event (profiling_started, profiling_completed, profiling_failed)
        dataset_name: Name of the dataset being profiled
        **kwargs: Additional event metadata
    """
    event_data = {"event_type": event_type, "dataset_name": dataset_name, **kwargs}

    # Log the event
    if event_type == "profiling_started":
        logger.info(f"Profiling started: {dataset_name}")
    elif event_type == "profiling_completed":
        logger.info(f"Profiling completed: {dataset_name} (run_id: {kwargs.get('run_id')})")
    elif event_type == "profiling_failed":
        logger.error(f"Profiling failed: {dataset_name} - {kwargs.get('error')}")

    # Emit to Dagster if context is available
    if DAGSTER_AVAILABLE and context is not None:
        try:
            context.log.info(f"Baselinr Event: {event_type}", extra=event_data)
        except Exception as e:
            logger.warning(f"Failed to emit Dagster event: {e}")
