"""
Dagster integration entrypoints for Baselinr.
"""

from typing import Any, Mapping, Optional, Sequence

try:
    from dagster import Definitions

    DAGSTER_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when Dagster missing
    DAGSTER_AVAILABLE = False

from .assets import BaselinrResource, create_profiling_assets, create_profiling_job
from .events import emit_profiling_event
from .sensors import baselinr_plan_sensor


def build_baselinr_definitions(
    config_path: str,
    *,
    asset_prefix: str = "baselinr",
    job_name: str = "baselinr_profile_all",
    enable_sensor: bool = True,
    group_name: str = "baselinr_profiling",
    default_tags: Optional[Mapping[str, str]] = None,
    default_metadata: Optional[Mapping[str, Any]] = None,
) -> "Definitions":
    """
    Build a Dagster ``Definitions`` object with Baselinr assets, job, and sensor.
    """

    if not DAGSTER_AVAILABLE:
        raise ImportError("Dagster is not installed. Install with `pip install baselinr[dagster]`.")

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
            baselinr_plan_sensor(
                config_path=config_path,
                job_name=job_name,
                asset_prefix=asset_prefix,
            )
        ]

    definitions = Definitions(
        assets=assets,
        jobs=[job],
        resources={"baselinr": BaselinrResource(config_path=config_path)},
        sensors=sensors,
    )
    return definitions


__all__ = [
    "BaselinrResource",
    "build_baselinr_definitions",
    "create_profiling_assets",
    "create_profiling_job",
    "emit_profiling_event",
    "baselinr_plan_sensor",
]
