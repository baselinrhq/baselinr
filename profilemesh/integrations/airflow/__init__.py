"""
Airflow integration entrypoints for ProfileMesh.

This module provides Airflow operators, sensors, and hooks for running
ProfileMesh profiling tasks as part of Airflow DAGs.
"""

from typing import Any

try:
    AIRFLOW_AVAILABLE = True
except ImportError:  # pragma: no cover
    AIRFLOW_AVAILABLE = False

from .events import emit_profiling_event
from .hooks import ProfileMeshHook
from .operators import (
    ProfileMeshProfilingOperator,
    ProfileMeshTableOperator,
    create_profiling_task_group,
)
from .sensors import ProfileMeshPlanSensor

__all__ = [
    "ProfileMeshHook",
    "ProfileMeshProfilingOperator",
    "ProfileMeshTableOperator",
    "ProfileMeshPlanSensor",
    "create_profiling_task_group",
    "emit_profiling_event",
]
