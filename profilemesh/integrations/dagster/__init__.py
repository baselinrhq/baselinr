"""
Dagster integration entrypoints for ProfileMesh.
"""

from typing import Any, Mapping, Optional, Sequence

try:
    from dagster import Definitions

    DAGSTER_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when Dagster missing
    DAGSTER_AVAILABLE = False

from .assets import ProfileMeshResource, create_profiling_assets, create_profiling_job
from .events import emit_profiling_event
from .sensors import profilemesh_plan_sensor


def build_profilemesh_definitions(
    config_path: str,
    *,
    asset_prefix: str = "profilemesh",
    job_name: str = "profilemesh_profile_all",
    enable_sensor: bool = True,
    group_name: str = "profilemesh_profiling",
    default_tags: Optional[Mapping[str, str]] = None,
    default_metadata: Optional[Mapping[str, Any]] = None,
) -> "Definitions":
    """
    Build a Dagster ``Definitions`` object with ProfileMesh assets, job, and sensor.
    """

    if not DAGSTER_AVAILABLE:
        raise ImportError(
            "Dagster is not installed. Install with `pip install profilemesh[dagster]`."
        )

    assets = create_profiling_assets(
        config_path=config_path,
        asset_name_prefix=asset_prefix,
        group_name=group_name,
        default_tags=default_tags,
        default_metadata=default_metadata,
    )
    job = create_profiling_job(assets=assets, job_name=job_name)

    sensors: Sequence[Any] = []
    if enable_sensor:
        sensors = [
            profilemesh_plan_sensor(
                config_path=config_path,
                job_name=job_name,
                asset_prefix=asset_prefix,
            )
        ]

    definitions = Definitions(
        assets=assets,
        jobs=[job],
        resources={"profilemesh": ProfileMeshResource(config_path=config_path)},
        sensors=sensors,
    )
    return definitions


__all__ = [
    "ProfileMeshResource",
    "build_profilemesh_definitions",
    "create_profiling_assets",
    "create_profiling_job",
    "emit_profiling_event",
    "profilemesh_plan_sensor",
]
