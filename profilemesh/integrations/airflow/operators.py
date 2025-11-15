"""
Airflow operators for ProfileMesh profiling.

Operators execute ProfileMesh profiling tasks as Airflow tasks,
emitting results via XCom and logging.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

try:
    from airflow.models import BaseOperator
    from airflow.utils.context import Context
    from airflow.utils.task_group import TaskGroup

    AIRFLOW_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when Airflow missing
    AIRFLOW_AVAILABLE = False
    BaseOperator = object  # type: ignore
    Context = dict  # type: ignore
    TaskGroup = object  # type: ignore

from ...config.loader import ConfigLoader
from ...config.schema import TablePattern
from ...profiling.core import ProfilingResult
from ...storage.writer import ResultWriter
from .events import emit_profiling_event
from .hooks import ProfileMeshHook

logger = logging.getLogger(__name__)


def _safe_task_id(name: str) -> str:
    """Convert table names into Airflow-friendly task IDs."""
    return name.replace(".", "_").replace("-", "_")


def _result_to_dict(result: ProfilingResult) -> Dict[str, Any]:
    """Convert ProfilingResult to a JSON-serializable dictionary."""
    return {
        "run_id": result.run_id,
        "dataset_name": result.dataset_name,
        "schema_name": result.schema_name,
        "profiled_at": result.profiled_at.isoformat(),
        "columns_profiled": len(result.columns),
        "row_count": result.metadata.get("row_count"),
        "metadata": result.metadata,
    }


if AIRFLOW_AVAILABLE:

    class ProfileMeshProfilingOperator(BaseOperator):
        """
        Airflow operator that executes ProfileMesh profiling.

        This operator can profile one or more tables and emit results via XCom.
        Similar to Dagster assets, it materializes profiling runs.

        Args:
            config_path: Path to ProfileMesh configuration file.
            table_patterns: Optional list of specific tables to profile.
                If None, profiles all tables in config.
            emit_xcom: Whether to emit results to XCom (default: True).
            task_id: Airflow task ID.

        Example:
            ```python
            profile_task = ProfileMeshProfilingOperator(
                task_id='profile_users_table',
                config_path='/path/to/config.yml',
                table_patterns=[{'schema': 'public', 'table': 'users'}],
            )
            ```
        """

        template_fields: Sequence[str] = ("config_path",)
        ui_color = "#4CAF50"  # Green color in Airflow UI

        def __init__(
            self,
            *,
            config_path: str,
            table_patterns: Optional[List[Dict[str, str]]] = None,
            emit_xcom: bool = True,
            **kwargs,
        ):
            super().__init__(**kwargs)
            self.config_path = config_path
            self.table_patterns = table_patterns
            self.emit_xcom = emit_xcom

        def execute(self, context: Context) -> Dict[str, Any]:
            """
            Execute profiling and return results.

            Args:
                context: Airflow execution context.

            Returns:
                Dictionary with profiling results metadata.
            """
            hook = ProfileMeshHook(config_path=self.config_path)
            config = hook.get_config()
            engine = hook.get_engine()

            # Determine which tables to profile
            if self.table_patterns:
                patterns = [
                    TablePattern(
                        schema_=p.get("schema", ""),
                        table=p["table"],
                        database=p.get("database", ""),
                    )
                    for p in self.table_patterns
                ]
            else:
                patterns = config.profiling.tables

            # Emit start event
            emit_profiling_event(
                context=context,
                event_type="profiling_started",
                environment=config.environment,
                table_count=len(patterns),
            )

            logger.info(f"Profiling {len(patterns)} table(s)")

            # Execute profiling
            results = engine.profile(table_patterns=patterns)

            if not results:
                raise ValueError("No profiling results returned")

            # Write results to storage
            writer = ResultWriter(config.storage)
            try:
                writer.write_results(results, environment=config.environment)
            finally:
                writer.close()

            # Build summary for XCom and logging
            summary = {
                "run_id": results[0].run_id,
                "environment": config.environment,
                "tables_profiled": len(results),
                "profiled_at": datetime.utcnow().isoformat(),
                "results": [_result_to_dict(r) for r in results],
            }

            # Log each result
            for result in results:
                logger.info(
                    f"Profiled {result.dataset_name}: "
                    f"{len(result.columns)} columns, "
                    f"{result.metadata.get('row_count', 'unknown')} rows"
                )

            # Emit completion event
            emit_profiling_event(
                context=context,
                event_type="profiling_completed",
                environment=config.environment,
                run_id=summary["run_id"],
                tables_profiled=len(results),
                total_columns=sum(len(r.columns) for r in results),
            )

            if self.emit_xcom:
                # Push to XCom for downstream tasks
                context["ti"].xcom_push(key="profiling_results", value=summary)

            return summary

    class ProfileMeshTableOperator(BaseOperator):
        """
        Operator that profiles a single table.

        This is useful for creating per-table tasks in a TaskGroup,
        providing better parallelism and observability.

        Args:
            config_path: Path to ProfileMesh configuration file.
            table: Table name to profile.
            schema: Optional schema name.
            database: Optional database name.
            task_id: Airflow task ID.

        Example:
            ```python
            profile_users = ProfileMeshTableOperator(
                task_id='profile_users',
                config_path='/path/to/config.yml',
                table='users',
                schema='public',
            )
            ```
        """

        template_fields: Sequence[str] = ("config_path", "table", "schema", "database")
        ui_color = "#66BB6A"  # Lighter green

        def __init__(
            self,
            *,
            config_path: str,
            table: str,
            schema: str = "",
            database: str = "",
            **kwargs,
        ):
            super().__init__(**kwargs)
            self.config_path = config_path
            self.table = table
            self.schema = schema
            self.database = database

        def execute(self, context: Context) -> Dict[str, Any]:
            """Execute profiling for a single table."""
            hook = ProfileMeshHook(config_path=self.config_path)
            config = hook.get_config()
            engine = hook.get_engine()

            pattern = TablePattern(
                schema_=self.schema,
                table=self.table,
                database=self.database,
            )

            emit_profiling_event(
                context=context,
                event_type="profiling_started",
                dataset_name=self.table,
                environment=config.environment,
            )

            logger.info(f"Profiling table: {self.table}")

            results = engine.profile(table_patterns=[pattern])

            if not results:
                raise ValueError(f"No profiling results returned for {self.table}")

            result = results[0]
            writer = ResultWriter(config.storage)
            try:
                writer.write_results([result], environment=config.environment)
            finally:
                writer.close()

            result_dict = _result_to_dict(result)

            logger.info(
                f"Profiled {result.dataset_name}: "
                f"{len(result.columns)} columns, "
                f"{result.metadata.get('row_count', 'unknown')} rows"
            )

            emit_profiling_event(
                context=context,
                event_type="profiling_completed",
                dataset_name=self.table,
                environment=config.environment,
                run_id=result.run_id,
                column_count=len(result.columns),
                row_count=result.metadata.get("row_count"),
            )

            context["ti"].xcom_push(key="profiling_result", value=result_dict)

            return result_dict


    def create_profiling_task_group(
        *,
        group_id: str,
        config_path: str,
        dag=None,
        **task_group_kwargs,
    ) -> TaskGroup:
        """
        Create a TaskGroup with one task per table from the config.

        This provides better parallelism and observability compared to a
        single operator profiling all tables.

        Args:
            group_id: ID for the TaskGroup.
            config_path: Path to ProfileMesh configuration file.
            dag: Parent DAG (optional, can be inferred from context).
            **task_group_kwargs: Additional TaskGroup parameters.

        Returns:
            TaskGroup containing one ProfileMeshTableOperator per table.

        Example:
            ```python
            with DAG('my_dag', ...) as dag:
                profiling_tasks = create_profiling_task_group(
                    group_id='profile_tables',
                    config_path='/path/to/config.yml',
                )
            ```
        """
        config = ConfigLoader.load_from_file(config_path)

        with TaskGroup(group_id=group_id, dag=dag, **task_group_kwargs) as task_group:
            for table_pattern in config.profiling.tables:
                task_id = _safe_task_id(table_pattern.table)

                ProfileMeshTableOperator(
                    task_id=task_id,
                    config_path=config_path,
                    table=table_pattern.table,
                    schema=table_pattern.schema_ or "",
                    database=table_pattern.database or "",
                    dag=dag,
                )

        return task_group


else:  # pragma: no cover - exercised when Airflow missing

    class ProfileMeshProfilingOperator:
        """Stub operator exposed when Airflow is unavailable."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "Airflow is not installed. Install with `pip install profilemesh[airflow]`."
            )

    class ProfileMeshTableOperator:
        """Stub operator exposed when Airflow is unavailable."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "Airflow is not installed. Install with `pip install profilemesh[airflow]`."
            )

    def create_profiling_task_group(*args, **kwargs):
        raise ImportError(
            "Airflow is not installed. Install with `pip install profilemesh[airflow]`."
        )


__all__ = [
    "ProfileMeshProfilingOperator",
    "ProfileMeshTableOperator",
    "create_profiling_task_group",
]
