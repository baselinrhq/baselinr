"""
Backward-compatible import location for the Dagster integration.

The real implementation now lives under ``profilemesh.integrations.dagster``.
"""

import warnings

from profilemesh.integrations.dagster import (  # noqa: F401
    ProfileMeshResource,
    build_profilemesh_definitions,
    create_profiling_assets,
    create_profiling_job,
    emit_profiling_event,
    profilemesh_plan_sensor,
)

warnings.warn(
    "profilemesh.dagster_integration is deprecated; "
    "use profilemesh.integrations.dagster instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "ProfileMeshResource",
    "build_profilemesh_definitions",
    "create_profiling_assets",
    "create_profiling_job",
    "emit_profiling_event",
    "profilemesh_plan_sensor",
]
