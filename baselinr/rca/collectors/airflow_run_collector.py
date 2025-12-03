"""
Airflow run collector for RCA.

Collects Airflow DAG run metadata from:
1. Airflow REST API (v1 or v2)
2. Airflow metadata database (direct SQL access)
3. Environment variables (Airflow Cloud/Managed)
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
    # Airflow imports would go here if needed for direct database access
    # For now, we use SQLAlchemy directly to query the metadata database
    AIRFLOW_AVAILABLE = True
except ImportError:
    AIRFLOW_AVAILABLE = False


class AirflowRunCollector(BaseCollector):
    """Collector for Airflow pipeline runs."""

    def __init__(
        self,
        engine: Engine,
        api_url: Optional[str] = None,
        api_version: str = "v1",  # v1 or v2
        username: Optional[str] = None,
        password: Optional[str] = None,
        metadata_db_connection: Optional[str] = None,
        dag_ids: Optional[List[str]] = None,
        enabled: bool = True,
        config: Optional[Dict] = None,
    ):
        """
        Initialize Airflow run collector.

        Args:
            engine: SQLAlchemy engine for storage
            api_url: URL to Airflow REST API (e.g., http://localhost:8080/api/v1)
            api_version: Airflow API version (v1 or v2)
            username: Username for API authentication
            password: Password for API authentication
            metadata_db_connection: Connection string for direct database access
            dag_ids: Optional list of DAG IDs to filter (None = all DAGs)
            enabled: Whether collector is enabled
            config: Additional configuration
        """
        super().__init__(engine, enabled)
        self.config = config or {}
        self.api_url = api_url or os.getenv("AIRFLOW_API_URL")
        # Use env var if provided, otherwise use passed value or default
        env_api_version = os.getenv("AIRFLOW_API_VERSION")
        if env_api_version:
            self.api_version = env_api_version
        else:
            self.api_version = api_version or "v1"
        self.username = username or os.getenv("AIRFLOW_USERNAME")
        self.password = password or os.getenv("AIRFLOW_PASSWORD")
        self.metadata_db_connection = metadata_db_connection or os.getenv(
            "AIRFLOW_METADATA_DB_CONNECTION"
        )
        self.dag_ids = dag_ids or self.config.get("dag_ids")

        if not AIRFLOW_AVAILABLE:
            logger.warning("Airflow not available. Install with: pip install apache-airflow")

    def collect(self) -> List[PipelineRun]:
        """
        Collect Airflow runs.

        Returns:
            List of PipelineRun objects
        """
        runs: List[PipelineRun] = []

        if not AIRFLOW_AVAILABLE:
            logger.warning("Airflow not available, skipping collection")
            return runs

        # Try to collect from REST API
        api_runs = self._collect_from_api()
        if api_runs:
            runs.extend(api_runs)

        # Try to collect from metadata database
        db_runs = self._collect_from_database()
        if db_runs:
            runs.extend(db_runs)

        # Try to collect from environment variables (Airflow Cloud/Managed)
        env_run = self._collect_from_env()
        if env_run:
            runs.append(env_run)

        return runs

    def _collect_from_api(self) -> List[PipelineRun]:
        """
        Collect runs from Airflow REST API.

        Returns:
            List of PipelineRun objects
        """
        if not self.api_url:
            logger.debug("No Airflow API URL configured")
            return []

        try:
            import requests  # type: ignore[import-untyped]

            # Build API endpoint based on version
            if self.api_version == "v2":
                endpoint = f"{self.api_url}/dags/~/dagRuns"
            else:
                endpoint = f"{self.api_url}/dags/~/dag_runs"

            # Prepare authentication
            auth = None
            if self.username and self.password:
                auth = (self.username, self.password)

            # Query parameters
            params: Dict[str, Any] = {"limit": 100}
            if self.dag_ids:
                params["dag_ids"] = ",".join(self.dag_ids)

            response = requests.get(endpoint, auth=auth, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Parse response based on API version
            if self.api_version == "v2":
                dag_runs = data.get("dag_runs", [])
            else:
                dag_runs = data.get("dag_runs", [])

            pipeline_runs = []
            for dag_run_data in dag_runs:
                pipeline_run = self._convert_api_run(dag_run_data)
                if pipeline_run:
                    pipeline_runs.append(pipeline_run)

            return pipeline_runs

        except ImportError:
            logger.warning("requests library not available for REST API")
            return []
        except Exception as e:
            logger.warning(f"Failed to collect from Airflow API: {e}")
            return []

    def _collect_from_database(self) -> List[PipelineRun]:
        """
        Collect runs from Airflow metadata database.

        Returns:
            List of PipelineRun objects
        """
        if not self.metadata_db_connection:
            logger.debug("No Airflow metadata DB connection configured")
            return []

        if not AIRFLOW_AVAILABLE:
            logger.debug("Airflow not available for database access")
            return []

        try:
            from sqlalchemy import create_engine, text

            # Create engine for Airflow metadata DB
            airflow_engine = create_engine(self.metadata_db_connection)

            # Query dag_run table
            query = text(
                """
                SELECT dag_id, run_id, state, execution_date, start_date, end_date
                FROM dag_run
                WHERE execution_date >= NOW() - INTERVAL '24 hours'
                ORDER BY execution_date DESC
                LIMIT 100
                """
            )

            if self.dag_ids:
                query = text(
                    """
                    SELECT dag_id, run_id, state, execution_date, start_date, end_date
                    FROM dag_run
                    WHERE execution_date >= NOW() - INTERVAL '24 hours'
                    AND dag_id IN :dag_ids
                    ORDER BY execution_date DESC
                    LIMIT 100
                    """
                )

            with airflow_engine.connect() as conn:
                if self.dag_ids:
                    results = conn.execute(query, {"dag_ids": tuple(self.dag_ids)}).fetchall()
                else:
                    results = conn.execute(query).fetchall()

            pipeline_runs = []
            for row in results:
                dag_id, run_id, state, execution_date, start_date, end_date = row
                pipeline_run = self._convert_db_run(
                    dag_id, run_id, state, execution_date, start_date, end_date
                )
                if pipeline_run:
                    pipeline_runs.append(pipeline_run)

            return pipeline_runs

        except Exception as e:
            logger.warning(f"Failed to collect from Airflow database: {e}")
            return []

    def _collect_from_env(self) -> Optional[PipelineRun]:
        """
        Collect run info from environment variables (Airflow Cloud/Managed).

        Common env vars:
        - AIRFLOW_CTX_DAG_ID
        - AIRFLOW_CTX_RUN_ID
        - AIRFLOW_CTX_TASK_ID
        - AIRFLOW_CTX_EXECUTION_DATE

        Returns:
            PipelineRun object or None
        """
        dag_id = os.getenv("AIRFLOW_CTX_DAG_ID")
        run_id = os.getenv("AIRFLOW_CTX_RUN_ID")
        if not dag_id or not run_id:
            return None

        try:
            execution_date_str = os.getenv("AIRFLOW_CTX_EXECUTION_DATE")
            started_at = datetime.utcnow()
            if execution_date_str:
                try:
                    started_at = datetime.fromisoformat(execution_date_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass

            run = PipelineRun(
                run_id=f"airflow_{run_id}",
                pipeline_name=dag_id,
                pipeline_type="airflow",
                started_at=started_at,
                status="running",  # Assume running if collecting from env
                affected_tables=[],
                metadata={
                    "airflow_dag_id": dag_id,
                    "airflow_run_id": run_id,
                    "airflow_task_id": os.getenv("AIRFLOW_CTX_TASK_ID"),
                    "collected_from": "environment_variables",
                },
            )

            return run

        except Exception as e:
            logger.error(f"Failed to collect from environment: {e}")
            return None

    def _convert_api_run(self, dag_run_data: Dict[str, Any]) -> Optional[PipelineRun]:
        """
        Convert Airflow API run data to PipelineRun.

        Args:
            dag_run_data: Run data from REST API

        Returns:
            PipelineRun object or None
        """
        try:
            # Map Airflow state to our status
            status_map = {
                "success": "success",
                "failed": "failed",
                "running": "running",
                "queued": "running",
                "up_for_retry": "running",
                "up_for_reschedule": "running",
                "deferred": "running",
                "skipped": "success",
            }

            airflow_state = dag_run_data.get("state", "unknown")
            status = status_map.get(airflow_state.lower(), "unknown")

            # Parse timestamps
            execution_date_str = dag_run_data.get("execution_date") or dag_run_data.get(
                "logical_date"
            )
            started_at = datetime.utcnow()
            if execution_date_str:
                try:
                    started_at = datetime.fromisoformat(execution_date_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass

            end_time = None
            end_date_str = dag_run_data.get("end_date")
            if end_date_str:
                try:
                    end_time = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass

            duration_seconds = None
            if end_time and started_at:
                duration_seconds = (end_time - started_at).total_seconds()

            # Extract DAG ID
            dag_id = dag_run_data.get("dag_id", "airflow_dag")
            run_id = dag_run_data.get("dag_run_id") or dag_run_data.get("run_id", "")

            # Extract affected tables from task logs or XCom (if available)
            affected_tables: List[str] = []
            # Note: Extracting affected tables from API would require additional API calls
            # to get task instances and XCom values. This is left as an extension point.

            run = PipelineRun(
                run_id=f"airflow_{run_id}",
                pipeline_name=dag_id,
                pipeline_type="airflow",
                started_at=started_at,
                completed_at=end_time,
                duration_seconds=duration_seconds,
                status=status,
                affected_tables=affected_tables,
                metadata={
                    "airflow_dag_id": dag_id,
                    "airflow_run_id": run_id,
                    "airflow_state": airflow_state,
                    "collected_from": "rest_api",
                },
            )

            return run

        except Exception as e:
            logger.error(f"Failed to convert Airflow API run: {e}")
            return None

    def _convert_db_run(
        self,
        dag_id: str,
        run_id: str,
        state: str,
        execution_date: Any,
        start_date: Optional[Any],
        end_date: Optional[Any],
    ) -> Optional[PipelineRun]:
        """
        Convert Airflow database run to PipelineRun.

        Args:
            dag_id: DAG ID
            run_id: Run ID
            state: Run state
            execution_date: Execution date
            start_date: Start date
            end_date: End date

        Returns:
            PipelineRun object or None
        """
        try:
            # Map Airflow state to our status
            status_map = {
                "success": "success",
                "failed": "failed",
                "running": "running",
                "queued": "running",
                "up_for_retry": "running",
                "up_for_reschedule": "running",
                "deferred": "running",
                "skipped": "success",
            }

            airflow_state = str(state).lower() if state else "unknown"
            status = status_map.get(airflow_state, "unknown")

            # Parse timestamps
            started_at = datetime.utcnow()
            if execution_date:
                if isinstance(execution_date, datetime):
                    started_at = execution_date
                elif isinstance(execution_date, str):
                    try:
                        started_at = datetime.fromisoformat(execution_date.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        pass

            end_time = None
            if end_date:
                if isinstance(end_date, datetime):
                    end_time = end_date
                elif isinstance(end_date, str):
                    try:
                        end_time = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        pass

            duration_seconds = None
            if end_time and started_at:
                duration_seconds = (end_time - started_at).total_seconds()

            # Extract affected tables (would require additional queries to task_instance/xcom)
            affected_tables: List[str] = []

            run = PipelineRun(
                run_id=f"airflow_{run_id}",
                pipeline_name=dag_id,
                pipeline_type="airflow",
                started_at=started_at,
                completed_at=end_time,
                duration_seconds=duration_seconds,
                status=status,
                affected_tables=affected_tables,
                metadata={
                    "airflow_dag_id": dag_id,
                    "airflow_run_id": run_id,
                    "airflow_state": airflow_state,
                    "collected_from": "metadata_database",
                },
            )

            return run

        except Exception as e:
            logger.error(f"Failed to convert Airflow DB run: {e}")
            return None


# Register Airflow collector
if AIRFLOW_AVAILABLE:
    from .pipeline_run_collector import PipelineRunCollector

    PipelineRunCollector.register_collector("airflow", AirflowRunCollector)
