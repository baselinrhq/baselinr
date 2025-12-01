"""
DBT run collector for RCA.

Collects dbt run metadata from:
1. dbt manifest and run_results.json files
2. Environment variables set by dbt Cloud or orchestrators
3. dbt logs (if available)
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy.engine import Engine

from ..models import PipelineRun
from .base_collector import BaseCollector

logger = logging.getLogger(__name__)


class DbtRunCollector(BaseCollector):
    """Collector for dbt pipeline runs."""

    def __init__(
        self,
        engine: Engine,
        manifest_path: Optional[str] = None,
        run_results_path: Optional[str] = None,
        project_dir: Optional[str] = None,
        enabled: bool = True,
        config: Optional[Dict] = None,
    ):
        """
        Initialize dbt run collector.

        Args:
            engine: SQLAlchemy engine for storage
            manifest_path: Path to dbt manifest.json
            run_results_path: Path to dbt run_results.json
            project_dir: DBT project directory (will look for target/ subdirectory)
            enabled: Whether collector is enabled
            config: Additional configuration
        """
        super().__init__(engine, enabled)
        self.config = config or {}

        # Determine paths
        if project_dir:
            project_path = Path(project_dir)
            target_dir = project_path / "target"
            self.manifest_path = manifest_path or str(target_dir / "manifest.json")
            self.run_results_path = run_results_path or str(target_dir / "run_results.json")
        else:
            self.manifest_path = manifest_path or "./target/manifest.json"
            self.run_results_path = run_results_path or "./target/run_results.json"

    def collect(self) -> List[PipelineRun]:
        """
        Collect dbt runs from run_results.json.

        Returns:
            List of PipelineRun objects
        """
        runs = []

        # Try to collect from run_results.json
        run_results = self._load_run_results()
        if run_results:
            run = self._parse_run_results(run_results)
            if run:
                runs.append(run)

        # Try to collect from environment variables (dbt Cloud)
        env_run = self._collect_from_env()
        if env_run:
            runs.append(env_run)

        return runs

    def _load_run_results(self) -> Optional[Dict[str, Any]]:
        """Load dbt run_results.json file."""
        try:
            path = Path(self.run_results_path)
            if not path.exists():
                logger.debug(f"run_results.json not found at {self.run_results_path}")
                return None

            with open(path, "r") as f:
                data: Dict[str, Any] = json.load(f)  # type: ignore[assignment]
                return data

        except Exception as e:
            logger.warning(f"Failed to load run_results.json: {e}")
            return None

    def _load_manifest(self) -> Optional[Dict[str, Any]]:
        """Load dbt manifest.json file."""
        try:
            path = Path(self.manifest_path)
            if not path.exists():
                logger.debug(f"manifest.json not found at {self.manifest_path}")
                return None

            with open(path, "r") as f:
                data: Dict[str, Any] = json.load(f)  # type: ignore[assignment]
                return data

        except Exception as e:
            logger.warning(f"Failed to load manifest.json: {e}")
            return None

    def _parse_run_results(self, run_results: Dict[str, Any]) -> Optional[PipelineRun]:
        """
        Parse run_results.json into PipelineRun.

        Args:
            run_results: Parsed run_results.json content

        Returns:
            PipelineRun object or None
        """
        try:
            metadata = run_results.get("metadata", {})
            elapsed_time = run_results.get("elapsed_time", 0)

            # Parse timestamps
            generated_at = metadata.get("generated_at")
            if generated_at:
                try:
                    started_at = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    started_at = datetime.utcnow()
            else:
                started_at = datetime.utcnow()

            # Determine status from results
            results = run_results.get("results", [])
            has_errors = any(r.get("status") == "error" for r in results)
            has_failures = any(r.get("status") in ["fail", "failed"] for r in results)

            if has_errors or has_failures:
                status = "failed"
            else:
                status = "success"

            # Extract affected tables
            affected_tables = []
            total_rows_affected = 0

            for result in results:
                # Get model/table name
                unique_id = result.get("unique_id", "")
                if unique_id.startswith("model."):
                    # Extract table name from unique_id (e.g., model.my_project.my_table)
                    parts = unique_id.split(".")
                    if len(parts) >= 3:
                        table_name = parts[2]
                        affected_tables.append(table_name)

                # Try to get row count
                adapter_response = result.get("adapter_response", {})
                rows_affected = adapter_response.get("rows_affected", 0)
                if rows_affected:
                    total_rows_affected += rows_affected

            # Get git info from metadata or environment
            git_commit_sha = metadata.get("env", {}).get("DBT_GIT_SHA") or os.getenv("DBT_GIT_SHA")
            git_branch = metadata.get("env", {}).get("DBT_GIT_BRANCH") or os.getenv(
                "DBT_GIT_BRANCH"
            )

            # Generate run ID from invocation_id or create new one
            run_id = metadata.get("invocation_id") or str(uuid4())

            run = PipelineRun(
                run_id=f"dbt_{run_id}",
                pipeline_name=metadata.get("project_name", "dbt_project"),
                pipeline_type="dbt",
                started_at=started_at,
                completed_at=started_at,  # Approximate
                duration_seconds=elapsed_time,
                status=status,
                input_row_count=None,  # Not available in run_results
                output_row_count=total_rows_affected if total_rows_affected > 0 else None,
                git_commit_sha=git_commit_sha,
                git_branch=git_branch,
                affected_tables=affected_tables,
                metadata={
                    "dbt_version": metadata.get("dbt_version"),
                    "adapter_type": metadata.get("adapter_type"),
                    "invocation_id": metadata.get("invocation_id"),
                    "results_count": len(results),
                },
            )

            return run

        except Exception as e:
            logger.error(f"Failed to parse run_results.json: {e}")
            return None

    def _collect_from_env(self) -> Optional[PipelineRun]:
        """
        Collect run info from environment variables (dbt Cloud).

        Common env vars:
        - DBT_CLOUD_RUN_ID
        - DBT_CLOUD_PROJECT_ID
        - DBT_CLOUD_JOB_ID
        - DBT_GIT_SHA
        - DBT_GIT_BRANCH

        Returns:
            PipelineRun object or None
        """
        run_id = os.getenv("DBT_CLOUD_RUN_ID")
        if not run_id:
            return None

        try:
            # Basic run info from environment
            project_id = os.getenv("DBT_CLOUD_PROJECT_ID", "unknown")
            job_id = os.getenv("DBT_CLOUD_JOB_ID", "unknown")

            run = PipelineRun(
                run_id=f"dbt_cloud_{run_id}",
                pipeline_name=f"dbt_project_{project_id}",
                pipeline_type="dbt",
                started_at=datetime.utcnow(),
                status="running",  # Assume running if collecting from env
                git_commit_sha=os.getenv("DBT_GIT_SHA"),
                git_branch=os.getenv("DBT_GIT_BRANCH"),
                affected_tables=[],
                metadata={
                    "dbt_cloud_job_id": job_id,
                    "dbt_cloud_project_id": project_id,
                    "collected_from": "environment_variables",
                },
            )

            return run

        except Exception as e:
            logger.error(f"Failed to collect from environment: {e}")
            return None

    def get_run_details(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific dbt run.

        Args:
            run_id: Run ID to look up

        Returns:
            Dict with run details or None
        """
        # Load manifest for additional context
        manifest = self._load_manifest()
        if not manifest:
            return None

        # Extract model information
        nodes = manifest.get("nodes", {})
        models = {
            k: v for k, v in nodes.items() if k.startswith("model.") or k.startswith("snapshot.")
        }

        return {
            "models": models,
            "sources": manifest.get("sources", {}),
            "manifest_metadata": manifest.get("metadata", {}),
        }


# Register dbt collector at module level
try:
    from .pipeline_run_collector import PipelineRunCollector

    PipelineRunCollector.register_collector("dbt", DbtRunCollector)
except ImportError:
    pass  # PipelineRunCollector may not be available during import
