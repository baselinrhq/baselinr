"""
Dagster run collector for RCA.

Collects Dagster run metadata from:
1. Dagster GraphQL API
2. Dagster instance metadata database
3. Environment variables set by Dagster Cloud or orchestrators
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.engine import Engine

from ..models import PipelineRun
from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

try:
    from dagster import DagsterInstance
    from dagster._core.storage.dagster_run import DagsterRun, RunStatus

    DAGSTER_AVAILABLE = True
except ImportError:
    DAGSTER_AVAILABLE = False
    DagsterInstance = None  # type: ignore
    DagsterRun = None  # type: ignore
    RunStatus = None  # type: ignore


class DagsterRunCollector(BaseCollector):
    """Collector for Dagster pipeline runs."""

    def __init__(
        self,
        engine: Engine,
        instance_path: Optional[str] = None,
        graphql_url: Optional[str] = None,
        enabled: bool = True,
        config: Optional[Dict] = None,
    ):
        """
        Initialize Dagster run collector.

        Args:
            engine: SQLAlchemy engine for storage
            instance_path: Path to Dagster instance directory (e.g., /path/to/.dagster)
            graphql_url: URL to Dagster GraphQL API (e.g., http://localhost:3000/graphql)
            enabled: Whether collector is enabled
            config: Additional configuration
        """
        super().__init__(engine, enabled)
        self.config = config or {}
        self.instance_path = instance_path or os.getenv("DAGSTER_HOME")
        self.graphql_url = graphql_url or os.getenv("DAGSTER_GRAPHQL_URL")

        if not DAGSTER_AVAILABLE:
            logger.warning("Dagster not available. Install with: pip install dagster")

    def collect(self) -> List[PipelineRun]:
        """
        Collect Dagster runs.

        Returns:
            List of PipelineRun objects
        """
        runs: List[PipelineRun] = []

        if not DAGSTER_AVAILABLE:
            logger.warning("Dagster not available, skipping collection")
            return runs

        # Try to collect from Dagster instance
        instance_runs = self._collect_from_instance()
        if instance_runs:
            runs.extend(instance_runs)

        # Try to collect from GraphQL API
        graphql_runs = self._collect_from_graphql()
        if graphql_runs:
            runs.extend(graphql_runs)

        # Try to collect from environment variables (Dagster Cloud)
        env_run = self._collect_from_env()
        if env_run:
            runs.append(env_run)

        return runs

    def _collect_from_instance(self) -> List[PipelineRun]:
        """
        Collect runs from Dagster instance.

        Returns:
            List of PipelineRun objects
        """
        if not self.instance_path:
            logger.debug("No Dagster instance path configured")
            return []

        try:
            instance = DagsterInstance.get()
            if not instance:
                logger.debug("Could not get Dagster instance")
                return []

            # Get recent runs (last 24 hours by default)
            runs = instance.get_runs(limit=100)

            pipeline_runs = []
            for dagster_run in runs:
                pipeline_run = self._convert_dagster_run(dagster_run)
                if pipeline_run:
                    pipeline_runs.append(pipeline_run)

            return pipeline_runs

        except Exception as e:
            logger.warning(f"Failed to collect from Dagster instance: {e}")
            return []

    def _collect_from_graphql(self) -> List[PipelineRun]:
        """
        Collect runs from Dagster GraphQL API.

        Returns:
            List of PipelineRun objects
        """
        if not self.graphql_url:
            logger.debug("No Dagster GraphQL URL configured")
            return []

        try:
            import requests  # type: ignore[import-untyped]

            # GraphQL query to get recent runs
            query = """
            query GetRuns($limit: Int) {
                runsOrError(limit: $limit) {
                    ... on Runs {
                        results {
                            id
                            runId
                            status
                            pipelineName
                            jobName
                            startTime
                            endTime
                            tags {
                                key
                                value
                            }
                            assets {
                                key {
                                    path
                                }
                            }
                        }
                    }
                }
            }
            """

            response = requests.post(
                self.graphql_url,
                json={"query": query, "variables": {"limit": 100}},
                timeout=10,
            )
            response.raise_for_status()

            data = response.json()
            runs_data = data.get("data", {}).get("runsOrError", {}).get("results", [])

            pipeline_runs = []
            for run_data in runs_data:
                pipeline_run = self._convert_graphql_run(run_data)
                if pipeline_run:
                    pipeline_runs.append(pipeline_run)

            return pipeline_runs

        except ImportError:
            logger.warning("requests library not available for GraphQL API")
            return []
        except Exception as e:
            logger.warning(f"Failed to collect from GraphQL API: {e}")
            return []

    def _collect_from_env(self) -> Optional[PipelineRun]:
        """
        Collect run info from environment variables (Dagster Cloud).

        Common env vars:
        - DAGSTER_CLOUD_RUN_ID
        - DAGSTER_CLOUD_DEPLOYMENT_NAME
        - DAGSTER_CLOUD_JOB_NAME
        - DAGSTER_CLOUD_REPO_NAME

        Returns:
            PipelineRun object or None
        """
        run_id = os.getenv("DAGSTER_CLOUD_RUN_ID")
        if not run_id:
            return None

        try:
            deployment_name = os.getenv("DAGSTER_CLOUD_DEPLOYMENT_NAME", "unknown")
            job_name = os.getenv("DAGSTER_CLOUD_JOB_NAME", "unknown")
            repo_name = os.getenv("DAGSTER_CLOUD_REPO_NAME", "unknown")

            run = PipelineRun(
                run_id=f"dagster_cloud_{run_id}",
                pipeline_name=f"{deployment_name}/{repo_name}",
                pipeline_type="dagster",
                started_at=datetime.utcnow(),
                status="running",  # Assume running if collecting from env
                affected_tables=[],
                metadata={
                    "dagster_cloud_deployment": deployment_name,
                    "dagster_cloud_job": job_name,
                    "dagster_cloud_repo": repo_name,
                    "collected_from": "environment_variables",
                },
            )

            return run

        except Exception as e:
            logger.error(f"Failed to collect from environment: {e}")
            return None

    def _convert_dagster_run(self, dagster_run: Any) -> Optional[PipelineRun]:
        """
        Convert Dagster run to PipelineRun.

        Args:
            dagster_run: DagsterRun object

        Returns:
            PipelineRun object or None
        """
        try:
            # Map Dagster status to our status
            status_map = {
                "SUCCESS": "success",
                "FAILURE": "failed",
                "STARTED": "running",
                "STARTING": "running",
                "CANCELED": "failed",
                "CANCELING": "running",
            }

            dagster_status = (
                str(dagster_run.status) if hasattr(dagster_run, "status") else "unknown"
            )
            status = status_map.get(dagster_status.upper(), "unknown")

            # Extract timestamps
            started_at = (
                datetime.fromtimestamp(dagster_run.create_timestamp)
                if hasattr(dagster_run, "create_timestamp") and dagster_run.create_timestamp
                else datetime.utcnow()
            )

            end_time = None
            if hasattr(dagster_run, "end_time") and dagster_run.end_time:
                end_time = datetime.fromtimestamp(dagster_run.end_time)

            # Calculate duration
            duration_seconds = None
            if end_time and started_at:
                duration_seconds = (end_time - started_at).total_seconds()

            # Extract pipeline/job name
            pipeline_name = (
                dagster_run.pipeline_name
                if hasattr(dagster_run, "pipeline_name") and dagster_run.pipeline_name
                else (
                    dagster_run.job_name
                    if hasattr(dagster_run, "job_name") and dagster_run.job_name
                    else "dagster_pipeline"
                )
            )

            # Extract affected assets/tables
            affected_tables = []
            if hasattr(dagster_run, "asset_selection") and dagster_run.asset_selection:
                for asset_key in dagster_run.asset_selection:
                    if hasattr(asset_key, "path"):
                        # Asset keys are typically like ["schema", "table"]
                        table_name = ".".join(asset_key.path) if asset_key.path else None
                        if table_name:
                            affected_tables.append(table_name)

            # Extract git info from tags
            git_commit_sha = None
            git_branch = None
            if hasattr(dagster_run, "tags") and dagster_run.tags:
                git_commit_sha = dagster_run.tags.get("dagster/git/commit_sha")
                git_branch = dagster_run.tags.get("dagster/git/branch")

            run = PipelineRun(
                run_id=f"dagster_{dagster_run.run_id}",
                pipeline_name=pipeline_name,
                pipeline_type="dagster",
                started_at=started_at,
                completed_at=end_time,
                duration_seconds=duration_seconds,
                status=status,
                git_commit_sha=git_commit_sha,
                git_branch=git_branch,
                affected_tables=affected_tables,
                metadata={
                    "dagster_run_id": dagster_run.run_id,
                    "dagster_status": dagster_status,
                    "dagster_job_name": getattr(dagster_run, "job_name", None),
                },
            )

            return run

        except Exception as e:
            logger.error(f"Failed to convert Dagster run: {e}")
            return None

    def _convert_graphql_run(self, run_data: Dict[str, Any]) -> Optional[PipelineRun]:
        """
        Convert GraphQL run data to PipelineRun.

        Args:
            run_data: Run data from GraphQL API

        Returns:
            PipelineRun object or None
        """
        try:
            # Map status
            status_map = {
                "SUCCESS": "success",
                "FAILURE": "failed",
                "STARTED": "running",
                "STARTING": "running",
                "CANCELED": "failed",
            }

            dagster_status = run_data.get("status", "unknown")
            status = status_map.get(dagster_status.upper(), "unknown")

            # Parse timestamps
            start_time = run_data.get("startTime")
            started_at = (
                datetime.fromtimestamp(start_time / 1000) if start_time else datetime.utcnow()
            )

            end_time = None
            end_time_ms = run_data.get("endTime")
            if end_time_ms:
                end_time = datetime.fromtimestamp(end_time_ms / 1000)

            duration_seconds = None
            if end_time and started_at:
                duration_seconds = (end_time - started_at).total_seconds()

            # Extract pipeline/job name
            pipeline_name = run_data.get("pipelineName") or run_data.get(
                "jobName", "dagster_pipeline"
            )

            # Extract affected assets
            affected_tables = []
            assets = run_data.get("assets", [])
            for asset in assets:
                asset_key = asset.get("key", {})
                path = asset_key.get("path", [])
                if path:
                    table_name = ".".join(path)
                    affected_tables.append(table_name)

            # Extract git info from tags
            git_commit_sha = None
            git_branch = None
            tags = run_data.get("tags", [])
            for tag in tags:
                if tag.get("key") == "dagster/git/commit_sha":
                    git_commit_sha = tag.get("value")
                elif tag.get("key") == "dagster/git/branch":
                    git_branch = tag.get("value")

            run = PipelineRun(
                run_id=f"dagster_{run_data.get('runId', run_data.get('id'))}",
                pipeline_name=pipeline_name,
                pipeline_type="dagster",
                started_at=started_at,
                completed_at=end_time,
                duration_seconds=duration_seconds,
                status=status,
                git_commit_sha=git_commit_sha,
                git_branch=git_branch,
                affected_tables=affected_tables,
                metadata={
                    "dagster_run_id": run_data.get("runId", run_data.get("id")),
                    "dagster_status": dagster_status,
                },
            )

            return run

        except Exception as e:
            logger.error(f"Failed to convert GraphQL run: {e}")
            return None


# Register dagster collector
if DAGSTER_AVAILABLE:
    from .pipeline_run_collector import PipelineRunCollector

    PipelineRunCollector.register_collector("dagster", DagsterRunCollector)
