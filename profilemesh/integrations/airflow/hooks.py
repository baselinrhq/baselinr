"""
Airflow hooks for ProfileMesh.

Hooks manage the ProfileMesh configuration and provide access to the
ProfileEngine for operators and sensors.
"""

import logging
from functools import cached_property
from typing import Optional

try:
    from airflow.hooks.base import BaseHook

    AIRFLOW_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when Airflow missing
    AIRFLOW_AVAILABLE = False
    BaseHook = object  # type: ignore

from ...config.loader import ConfigLoader
from ...config.schema import ProfileMeshConfig
from ...planner import PlanBuilder, ProfilingPlan
from ...profiling.core import ProfileEngine

logger = logging.getLogger(__name__)


if AIRFLOW_AVAILABLE:

    class ProfileMeshHook(BaseHook):
        """
        Hook for interacting with ProfileMesh.

        This hook loads the ProfileMesh configuration and provides access to
        the ProfileEngine for profiling operations.
        """

        def __init__(self, config_path: str, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.config_path = config_path
            self._config: Optional[ProfileMeshConfig] = None
            self._plan: Optional[ProfilingPlan] = None

        @cached_property
        def config(self) -> ProfileMeshConfig:
            """Load and cache the ProfileMesh configuration."""
            if self._config is None:
                logger.info(f"Loading ProfileMesh config from {self.config_path}")
                self._config = ConfigLoader.load_from_file(self.config_path)
            return self._config

        def get_config(self) -> ProfileMeshConfig:
            """Return the cached ProfileMesh config."""
            return self.config

        def build_plan(self) -> ProfilingPlan:
            """Build a profiling plan from the configuration."""
            if self._plan is None:
                logger.info("Building ProfileMesh profiling plan")
                self._plan = PlanBuilder(self.config).build_plan()
            return self._plan

        def get_engine(self) -> ProfileEngine:
            """Create a ProfileEngine instance."""
            return ProfileEngine(self.config)

        def get_conn(self):
            """
            Return a connection object.

            This is required by BaseHook but not used for ProfileMesh.
            We return the config as the "connection".
            """
            return self.config

else:  # pragma: no cover - exercised when Airflow missing

    class ProfileMeshHook:
        """Stub hook exposed when Airflow is unavailable."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "Airflow is not installed. Install with `pip install profilemesh[airflow]`."
            )


__all__ = ["ProfileMeshHook"]
