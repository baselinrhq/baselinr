"""
Results writer for Baselinr.

Writes profiling results to storage backend with support
for historical tracking and drift detection.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text, text
from sqlalchemy.engine import Engine

from ..config.schema import BaselinrConfig, StorageConfig
from ..connectors.factory import create_connector
from ..events import EventBus, SchemaChangeDetected
from ..profiling.core import ProfilingResult

logger = logging.getLogger(__name__)


class ResultWriter:
    """Writes profiling results to storage backend."""

    def __init__(
        self,
        config: StorageConfig,
        retry_config=None,
        baselinr_config: Optional[BaselinrConfig] = None,
        event_bus: Optional[EventBus] = None,
    ):
        """
        Initialize result writer.

        Args:
            config: Storage configuration
            retry_config: Optional retry configuration
            baselinr_config: Optional full Baselinr config (for schema change detection)
            event_bus: Optional event bus for emitting schema change events
        """
        self.config = config
        self.retry_config = retry_config
        self.baselinr_config = baselinr_config
        self.event_bus = event_bus
        self.engine: Optional[Engine] = None
        self._setup_connection()

        if self.config.create_tables:
            self._create_tables()

    def _setup_connection(self):
        """Setup database connection for storage."""
        connector = create_connector(self.config.connection, self.retry_config)
        self.engine = connector.engine

    def _create_tables(self):
        """Create storage tables if they don't exist."""
        metadata = MetaData()

        # Runs table - tracks profiling runs
        # Note: Composite primary key (run_id, dataset_name) to allow multiple tables per run
        _runs_table = Table(  # noqa: F841
            self.config.runs_table,
            metadata,
            Column("run_id", String(36), primary_key=True),
            Column("dataset_name", String(255), primary_key=True),
            Column("schema_name", String(255)),
            Column("profiled_at", DateTime, nullable=False),
            Column("environment", String(50)),
            Column("status", String(20)),
            Column("row_count", Integer),
            Column("column_count", Integer),
        )

        # Results table - stores individual metrics
        _results_table = Table(  # noqa: F841
            self.config.results_table,
            metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("run_id", String(36), nullable=False),
            Column("dataset_name", String(255), nullable=False),
            Column("schema_name", String(255)),
            Column("column_name", String(255), nullable=False),
            Column("column_type", String(100)),
            Column("metric_name", String(100), nullable=False),
            Column("metric_value", Text),
            Column("profiled_at", DateTime, nullable=False),
        )

        # Create tables
        with self.engine.connect() as conn:
            metadata.create_all(self.engine)
            conn.commit()

        logger.info("Storage tables created successfully")

        # Initialize or verify schema version
        self._init_schema_version()

    def write_results(
        self,
        results: List[ProfilingResult],
        environment: str = "development",
        enable_enrichment: bool = True,
    ):
        """
        Write profiling results to storage.

        Args:
            results: List of profiling results to write
            environment: Environment name (dev/test/prod)
            enable_enrichment: Enable calculation of enrichment metrics
        """
        if self.engine is None:
            raise RuntimeError("Engine is not initialized")
        with self.engine.connect() as conn:
            for result in results:
                # Write run metadata
                self._write_run(conn, result, environment)

                # Write column metrics
                self._write_metrics(conn, result)

                # Register schema and detect changes
                if self.baselinr_config and self.baselinr_config.schema_change.enabled:
                    self._register_schema_and_detect_changes(result)

                # Calculate and write enrichment metrics if enabled
                if enable_enrichment:
                    self._calculate_and_write_enrichment_metrics(result)

                # Learn expectations if enabled
                if self.baselinr_config and self.config.enable_expectation_learning:
                    self._learn_expectations(result)

            conn.commit()

        logger.info(f"Wrote {len(results)} profiling results to storage")

    def _write_run(self, conn, result: ProfilingResult, environment: str):
        """Write run metadata."""
        # Check if run for this specific table already exists
        # Multiple tables can share the same run_id, but each table should have its own run record
        check_query = text(
            f"""
            SELECT run_id FROM {self.config.runs_table}
            WHERE run_id = :run_id AND dataset_name = :dataset_name LIMIT 1
        """
        )
        existing = conn.execute(
            check_query, {"run_id": result.run_id, "dataset_name": result.dataset_name}
        ).fetchone()

        if existing:
            # Run for this table already exists, skip insert
            return

        insert_query = text(
            f"""
            INSERT INTO {self.config.runs_table}
            (run_id, dataset_name, schema_name, profiled_at, environment, status,
             row_count, column_count)
            VALUES (:run_id, :dataset_name, :schema_name, :profiled_at, :environment,
                    :status, :row_count, :column_count)
        """
        )

        conn.execute(
            insert_query,
            {
                "run_id": result.run_id,
                "dataset_name": result.dataset_name,
                "schema_name": result.schema_name,
                "profiled_at": result.profiled_at,
                "environment": environment,
                "status": "completed",
                "row_count": result.metadata.get("row_count"),
                "column_count": result.metadata.get("column_count"),
            },
        )

    def _write_metrics(self, conn, result: ProfilingResult):
        """Write column metrics."""
        insert_query = text(
            f"""
            INSERT INTO {self.config.results_table}
            (run_id, dataset_name, schema_name, column_name, column_type, metric_name,
             metric_value, profiled_at)
            VALUES (:run_id, :dataset_name, :schema_name, :column_name, :column_type,
                    :metric_name, :metric_value, :profiled_at)
        """
        )

        for column_data in result.columns:
            column_name = column_data["column_name"]
            column_type = column_data["column_type"]

            for metric_name, metric_value in column_data["metrics"].items():
                # Convert metric value to string for storage
                if metric_value is not None:
                    metric_value_str = str(metric_value)
                else:
                    metric_value_str = None

                conn.execute(
                    insert_query,
                    {
                        "run_id": result.run_id,
                        "dataset_name": result.dataset_name,
                        "schema_name": result.schema_name,
                        "column_name": column_name,
                        "column_type": column_type,
                        "metric_name": metric_name,
                        "metric_value": metric_value_str,
                        "profiled_at": result.profiled_at,
                    },
                )

    def get_latest_run(self, dataset_name: str, schema_name: Optional[str] = None) -> Optional[str]:
        """
        Get the latest run_id for a dataset.

        Args:
            dataset_name: Name of the dataset
            schema_name: Optional schema name

        Returns:
            Run ID or None if not found
        """
        query = text(
            f"""
            SELECT run_id FROM {self.config.runs_table}
            WHERE dataset_name = :dataset_name
            {"AND schema_name = :schema_name" if schema_name else ""}
            ORDER BY profiled_at DESC
            LIMIT 1
        """
        )

        params = {"dataset_name": dataset_name}
        if schema_name:
            params["schema_name"] = schema_name

        if self.engine is None:
            raise RuntimeError("Engine is not initialized")
        with self.engine.connect() as conn:
            result = conn.execute(query, params).fetchone()
            return result[0] if result else None

    def _get_previous_run_id(
        self, dataset_name: str, schema_name: Optional[str], current_run_id: str
    ) -> Optional[str]:
        """
        Get the previous run_id for a dataset (before current run).

        Args:
            dataset_name: Name of the dataset
            schema_name: Optional schema name
            current_run_id: Current run ID to exclude

        Returns:
            Previous run ID or None if not found
        """
        query = text(
            f"""
            SELECT run_id FROM {self.config.runs_table}
            WHERE dataset_name = :dataset_name
            {"AND schema_name = :schema_name" if schema_name else ""}
            AND run_id != :current_run_id
            ORDER BY profiled_at DESC
            LIMIT 1
        """
        )

        params = {"dataset_name": dataset_name, "current_run_id": current_run_id}
        if schema_name:
            params["schema_name"] = schema_name

        if self.engine is None:
            raise RuntimeError("Engine is not initialized")
        with self.engine.connect() as conn:
            result = conn.execute(query, params).fetchone()
            return result[0] if result else None

    def _init_schema_version(self):
        """Initialize or verify schema version."""
        from .schema_version import CURRENT_SCHEMA_VERSION, get_version_table_ddl

        # Create version table if it doesn't exist
        with self.engine.connect() as conn:
            dialect = "snowflake" if "snowflake" in str(self.engine.url) else "generic"
            conn.execute(text(get_version_table_ddl(dialect)))
            conn.commit()

            # Check current version
            version_query = text(
                """
                SELECT version FROM baselinr_schema_version
                ORDER BY version DESC LIMIT 1
            """
            )
            result = conn.execute(version_query).fetchone()

            if result is None:
                # First time - insert initial version
                insert_query = text(
                    """
                    INSERT INTO baselinr_schema_version
                    (version, description, migration_script)
                    VALUES (:version, :description, :script)
                """
                )
                conn.execute(
                    insert_query,
                    {
                        "version": CURRENT_SCHEMA_VERSION,
                        "description": "Initial schema version",
                        "script": "schema.sql",
                    },
                )
                conn.commit()
                logger.info(f"Initialized schema version: {CURRENT_SCHEMA_VERSION}")
            else:
                current_version = result[0]
                if current_version != CURRENT_SCHEMA_VERSION:
                    logger.warning(
                        f"Schema version mismatch: DB={current_version}, "
                        f"Code={CURRENT_SCHEMA_VERSION}. Migration may be needed."
                    )
                else:
                    logger.debug(f"Schema version verified: {current_version}")

    def get_schema_version(self) -> Optional[int]:
        """
        Get current schema version from database.

        Returns:
            Current schema version or None if not initialized
        """
        query = text(
            """
            SELECT version FROM baselinr_schema_version
            ORDER BY version DESC LIMIT 1
        """
        )
        try:
            if self.engine is None:
                raise RuntimeError("Engine is not initialized")
            with self.engine.connect() as conn:
                result = conn.execute(query).fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.debug(f"Could not read schema version: {e}")
            return None

    def _calculate_and_write_enrichment_metrics(self, result: ProfilingResult):
        """Calculate and write enrichment metrics (row count stability, schema freshness, etc.)."""
        # Use a separate connection for enrichment metrics to avoid transaction conflicts
        # This ensures that if there are any errors, they don't affect the main write transaction
        try:
            if self.engine is None:
                return
            with self.engine.connect() as enrichment_conn:
                dataset_name = result.dataset_name
                schema_name = result.schema_name
                current_row_count = result.metadata.get("row_count")
                current_columns = {col["column_name"]: col["column_type"] for col in result.columns}

                # Calculate row count stability
                if current_row_count is not None:
                    stability_metrics = self._calculate_row_count_stability(
                        enrichment_conn,
                        dataset_name,
                        schema_name,
                        current_row_count,
                        result.profiled_at,
                    )
                    result.metadata.update(stability_metrics)

                # Calculate schema freshness and column stability
                schema_metrics = self._calculate_schema_metrics(
                    enrichment_conn, dataset_name, schema_name, current_columns, result.profiled_at
                )
                result.metadata.update(schema_metrics)

                # Calculate column-level stability metrics
                if result.columns:
                    self._calculate_column_stability_metrics(
                        enrichment_conn, result, dataset_name, schema_name
                    )

        except Exception as e:
            logger.warning(f"Failed to calculate enrichment metrics: {e}")

    def _calculate_row_count_stability(
        self,
        conn,
        dataset_name: str,
        schema_name: Optional[str],
        current_row_count: int,
        profiled_at: datetime,
    ) -> Dict[str, Any]:
        """Calculate row count stability metrics."""
        try:
            # Get historical row counts
            query = text(
                f"""
                SELECT row_count, profiled_at
                FROM {self.config.runs_table}
                WHERE dataset_name = :dataset_name
                {"AND schema_name = :schema_name" if schema_name else ""}
                AND profiled_at < :profiled_at
                AND row_count IS NOT NULL
                ORDER BY profiled_at DESC
                LIMIT :limit
            """
            )

            params = {
                "dataset_name": dataset_name,
                "profiled_at": profiled_at,
                "limit": 7,  # Default stability window
            }
            if schema_name:
                params["schema_name"] = schema_name

            result_rows = conn.execute(query, params).fetchall()

            if not result_rows:
                return {
                    "row_count_change": 0,
                    "row_count_change_percent": 0.0,
                    "row_count_stability_score": 1.0,
                    "row_count_trend": "stable",
                }

            # Get previous row count
            previous_row_count = result_rows[0][0] if result_rows else current_row_count
            row_count_change = current_row_count - previous_row_count
            row_count_change_percent = (
                (row_count_change / previous_row_count * 100) if previous_row_count > 0 else 0.0
            )

            # Calculate stability score (coefficient of variation)
            row_counts = [current_row_count] + [row[0] for row in result_rows]
            if len(row_counts) > 1:
                import statistics

                mean_count = statistics.mean(row_counts)
                if mean_count > 0:
                    try:
                        std_dev = statistics.stdev(row_counts) if len(row_counts) > 1 else 0
                        cv = std_dev / mean_count if mean_count > 0 else 0
                        stability_score = max(0.0, 1.0 - cv)  # Higher is more stable
                    except statistics.StatisticsError:
                        stability_score = 1.0
                else:
                    stability_score = 1.0
            else:
                stability_score = 1.0

            # Determine trend
            if len(row_counts) >= 3:
                recent_trend = row_counts[0] - row_counts[2]
                if recent_trend > 0:
                    trend = "increasing"
                elif recent_trend < 0:
                    trend = "decreasing"
                else:
                    trend = "stable"
            else:
                trend = (
                    "stable"
                    if abs(row_count_change_percent) < 1.0
                    else ("increasing" if row_count_change > 0 else "decreasing")
                )

            return {
                "row_count_change": row_count_change,
                "row_count_change_percent": row_count_change_percent,
                "row_count_stability_score": stability_score,
                "row_count_trend": trend,
            }

        except Exception as e:
            logger.warning(f"Failed to calculate row count stability: {e}")
            return {}

    def _calculate_schema_metrics(
        self,
        conn,
        dataset_name: str,
        schema_name: Optional[str],
        current_columns: Dict[str, str],
        profiled_at: datetime,
    ) -> Dict[str, Any]:
        """Calculate schema freshness and stability metrics."""
        try:
            # Get previous schema snapshot
            query = text(
                f"""
                SELECT run_id, profiled_at
                FROM {self.config.runs_table}
                WHERE dataset_name = :dataset_name
                {"AND schema_name = :schema_name" if schema_name else ""}
                AND profiled_at < :profiled_at
                ORDER BY profiled_at DESC
                LIMIT 1
            """
            )

            params = {"dataset_name": dataset_name, "profiled_at": profiled_at}
            if schema_name:
                params["schema_name"] = schema_name

            previous_run = conn.execute(query, params).fetchone()

            if not previous_run:
                # First run for this table
                return {
                    "schema_freshness": profiled_at.isoformat(),
                    "schema_version": 1,
                    "column_count_change": 0,
                }

            previous_run_id = previous_run[0]

            # Get previous columns
            prev_query = text(
                f"""
                SELECT DISTINCT column_name, column_type
                FROM {self.config.results_table}
                WHERE run_id = :run_id
                AND dataset_name = :dataset_name
            """
            )

            prev_columns_result = conn.execute(
                prev_query, {"run_id": previous_run_id, "dataset_name": dataset_name}
            ).fetchall()

            previous_columns = (
                {row[0]: row[1] for row in prev_columns_result} if prev_columns_result else {}
            )

            # Detect schema changes
            added_columns = set(current_columns.keys()) - set(previous_columns.keys())
            removed_columns = set(previous_columns.keys()) - set(current_columns.keys())
            changed_types = {
                col: (previous_columns[col], current_columns[col])
                for col in set(current_columns.keys()) & set(previous_columns.keys())
                if previous_columns[col] != current_columns[col]
            }

            # Calculate schema version (increment if changes detected)
            has_changes = (
                len(added_columns) > 0 or len(removed_columns) > 0 or len(changed_types) > 0
            )

            # Get current schema version
            version_query = text(
                f"""
                SELECT MAX(CAST(JSON_EXTRACT(metadata, '$.schema_version') AS UNSIGNED))
                FROM {self.config.runs_table}
                WHERE dataset_name = :dataset_name
                {"AND schema_name = :schema_name" if schema_name else ""}
            """
            )
            try:
                version_result = conn.execute(version_query, params).fetchone()
                current_version = (
                    int(version_result[0])
                    if version_result and version_result[0] is not None
                    else 0
                )
            except Exception:
                # JSON_EXTRACT may not be available in all databases
                current_version = 0

            schema_version = current_version + 1 if has_changes else max(1, current_version)

            return {
                "schema_freshness": profiled_at.isoformat() if has_changes else None,
                "schema_version": schema_version,
                "column_count_change": len(added_columns) - len(removed_columns),
            }

        except Exception as e:
            logger.warning(f"Failed to calculate schema metrics: {e}")
            return {}

    def _calculate_column_stability_metrics(
        self, conn, result: ProfilingResult, dataset_name: str, schema_name: Optional[str]
    ):
        """Calculate column-level stability metrics."""
        try:
            # For each column, calculate stability score
            for column_data in result.columns:
                column_name = column_data["column_name"]

                # Get column appearance history
                query = text(
                    f"""
                    SELECT COUNT(DISTINCT run_id) as appearance_count,
                           MIN(profiled_at) as first_seen,
                           MAX(profiled_at) as last_seen
                    FROM {self.config.results_table}
                    WHERE dataset_name = :dataset_name
                    {"AND schema_name = :schema_name" if schema_name else ""}
                    AND column_name = :column_name
                """
                )

                params = {"dataset_name": dataset_name, "column_name": column_name}
                if schema_name:
                    params["schema_name"] = schema_name

                col_history = conn.execute(query, params).fetchone()

                # Get total runs for this table
                total_runs_query = text(
                    f"""
                    SELECT COUNT(DISTINCT run_id)
                    FROM {self.config.runs_table}
                    WHERE dataset_name = :dataset_name
                    {"AND schema_name = :schema_name" if schema_name else ""}
                """
                )

                total_runs = conn.execute(total_runs_query, params).fetchone()
                total_runs_count = int(total_runs[0]) if total_runs and total_runs[0] else 1

                if col_history:
                    appearance_count = int(col_history[0]) if col_history[0] else 1
                    first_seen = col_history[1] if col_history[1] else result.profiled_at

                    # Calculate stability score
                    stability_score = (
                        appearance_count / total_runs_count if total_runs_count > 0 else 1.0
                    )

                    # Calculate age in days
                    from datetime import datetime

                    if isinstance(first_seen, datetime):
                        age_days = (result.profiled_at - first_seen).days
                    else:
                        age_days = 0

                    # Store as column-level metrics
                    column_data["metrics"]["column_stability_score"] = stability_score
                    column_data["metrics"]["column_age_days"] = age_days

                    # Calculate type consistency
                    type_query = text(
                        f"""
                        SELECT COUNT(DISTINCT column_type) as type_count
                        FROM {self.config.results_table}
                        WHERE dataset_name = :dataset_name
                        {"AND schema_name = :schema_name" if schema_name else ""}
                        AND column_name = :column_name
                    """
                    )

                    type_result = conn.execute(type_query, params).fetchone()
                    type_count = int(type_result[0]) if type_result and type_result[0] else 1

                    type_consistency_score = 1.0 if type_count == 1 else 0.0
                    column_data["metrics"]["type_consistency_score"] = type_consistency_score

        except Exception as e:
            logger.warning(f"Failed to calculate column stability metrics: {e}")

    def _learn_expectations(self, result: ProfilingResult):
        """Learn expectations from historical profiling data if enabled."""
        try:
            if self.engine is None:
                return

            from ..learning import ExpectationLearner, ExpectationStorage

            # Initialize learner and storage
            learner = ExpectationLearner(
                storage_config=self.config,
                engine=self.engine,
                default_window_days=self.config.learning_window_days,
                min_samples=self.config.min_samples,
                ewma_lambda=self.config.ewma_lambda,
            )
            storage = ExpectationStorage(storage_config=self.config, engine=self.engine)

            # Numeric metrics to learn expectations for
            numeric_metrics = ["mean", "stddev", "null_ratio", "count", "unique_ratio"]

            # Learn expectations for each column and metric
            for column_data in result.columns:
                column_name = column_data["column_name"]
                metrics = column_data.get("metrics", {})

                for metric_name in numeric_metrics:
                    # Only learn if this metric exists for the column
                    if metric_name not in metrics:
                        continue

                    try:
                        expectation = learner.learn_expectations(
                            table_name=result.dataset_name,
                            column_name=column_name,
                            metric_name=metric_name,
                            schema_name=result.schema_name,
                            window_days=self.config.learning_window_days,
                        )

                        if expectation:
                            storage.save_expectation(expectation)
                            logger.debug(
                                f"Learned expectations for "
                                f"{result.dataset_name}.{column_name}.{metric_name}"
                            )
                    except Exception as e:
                        table_metric = f"{result.dataset_name}.{column_name}.{metric_name}"
                        logger.warning(f"Failed to learn expectations for {table_metric}: {e}")

        except Exception as e:
            logger.warning(f"Failed to learn expectations: {e}")

    def _register_schema_and_detect_changes(self, result: ProfilingResult):
        """
        Register schema snapshot and detect changes.

        Args:
            result: ProfilingResult containing column information
        """
        if not self.baselinr_config or not self.engine:
            return

        try:
            from ..profiling.schema_detector import SchemaChangeDetector, SchemaRegistry

            # Build current schema from result
            current_columns = {col["column_name"]: col["column_type"] for col in result.columns}

            # Get nullable info from table if available (placeholder - would need table object)
            nullable_info: Dict[str, bool] = {}

            # Create registry and detector
            registry = SchemaRegistry(self.engine)
            detector = SchemaChangeDetector(
                registry,
                similarity_threshold=self.baselinr_config.schema_change.similarity_threshold,
            )

            # Register current schema
            registry.register_schema(
                table_name=result.dataset_name,
                schema_name=result.schema_name,
                columns=current_columns,
                run_id=result.run_id,
                profiled_at=result.profiled_at,
                nullable_info=nullable_info,
            )

            # Get previous run ID for comparison (before current run)
            previous_run_id = self._get_previous_run_id(
                result.dataset_name, result.schema_name, result.run_id
            )

            # Detect changes
            changes = detector.detect_changes(
                table_name=result.dataset_name,
                schema_name=result.schema_name,
                current_columns=current_columns,
                current_run_id=result.run_id,
                previous_run_id=previous_run_id,
            )

            # Emit events for detected changes (with suppression)
            if self.event_bus:
                self._emit_schema_change_events(
                    result.dataset_name,
                    result.schema_name,
                    changes,
                    result.profiled_at,
                )

        except Exception as e:
            logger.warning(f"Failed to register schema or detect changes: {e}")

    def _emit_schema_change_events(
        self,
        table_name: str,
        schema_name: Optional[str],
        changes: Dict[str, Any],
        profiled_at: datetime,
    ):
        """
        Emit schema change events with suppression.

        Args:
            table_name: Name of the table
            schema_name: Schema name (if applicable)
            changes: Dict of detected changes
            profiled_at: Timestamp of profiling
        """
        if not self.baselinr_config or not self.event_bus:
            return

        suppression_rules = self.baselinr_config.schema_change.suppression

        # Emit events for added columns
        for column_name, column_type in changes.get("added_columns", []):
            if not self._should_suppress(
                table_name, schema_name, "column_added", suppression_rules
            ):
                self.event_bus.emit(
                    SchemaChangeDetected(
                        event_type="SchemaChangeDetected",
                        timestamp=profiled_at,
                        table=table_name,
                        change_type="column_added",
                        column=column_name,
                        new_type=column_type,
                        change_severity="low",
                        metadata={},
                    )
                )

        # Emit events for removed columns
        for column_name, column_type in changes.get("removed_columns", []):
            if not self._should_suppress(
                table_name, schema_name, "column_removed", suppression_rules
            ):
                self.event_bus.emit(
                    SchemaChangeDetected(
                        event_type="SchemaChangeDetected",
                        timestamp=profiled_at,
                        table=table_name,
                        change_type="column_removed",
                        column=column_name,
                        old_type=column_type,
                        change_severity="high",
                        metadata={},
                    )
                )

        # Emit events for renamed columns
        for old_name, new_name, old_type, new_type in changes.get("renamed_columns", []):
            if not self._should_suppress(
                table_name, schema_name, "column_renamed", suppression_rules
            ):
                self.event_bus.emit(
                    SchemaChangeDetected(
                        event_type="SchemaChangeDetected",
                        timestamp=profiled_at,
                        table=table_name,
                        change_type="column_renamed",
                        column=new_name,
                        old_column_name=old_name,
                        old_type=old_type,
                        new_type=new_type,
                        change_severity="medium",
                        metadata={},
                    )
                )

        # Emit events for type changes
        for column_name, old_type, new_type in changes.get("type_changes", []):
            if not self._should_suppress(
                table_name, schema_name, "type_changed", suppression_rules
            ):
                # Determine severity based on type compatibility
                severity = self._determine_type_change_severity(old_type, new_type)
                self.event_bus.emit(
                    SchemaChangeDetected(
                        event_type="SchemaChangeDetected",
                        timestamp=profiled_at,
                        table=table_name,
                        change_type="type_changed",
                        column=column_name,
                        old_type=old_type,
                        new_type=new_type,
                        change_severity=severity,
                        metadata={},
                    )
                )

        # Emit events for partition changes
        for partition_info in changes.get("partition_changes", []):
            if not self._should_suppress(
                table_name, schema_name, "partition_changed", suppression_rules
            ):
                self.event_bus.emit(
                    SchemaChangeDetected(
                        event_type="SchemaChangeDetected",
                        timestamp=profiled_at,
                        table=table_name,
                        change_type="partition_changed",
                        partition_info=partition_info,
                        change_severity="high",
                        metadata={},
                    )
                )

    def _should_suppress(
        self,
        table_name: str,
        schema_name: Optional[str],
        change_type: str,
        suppression_rules: List[Any],
    ) -> bool:
        """
        Check if a schema change event should be suppressed.

        Args:
            table_name: Name of the table
            schema_name: Schema name (if applicable)
            change_type: Type of change
            suppression_rules: List of suppression rules

        Returns:
            True if event should be suppressed
        """
        for rule in suppression_rules:
            # Check table match
            if rule.table is not None and rule.table != table_name:
                continue

            # Check schema match
            if rule.schema_ is not None and rule.schema_ != schema_name:
                continue

            # Check change type match
            if rule.change_type is not None and rule.change_type != change_type:
                continue

            # All conditions match - suppress
            return True

        return False

    def _determine_type_change_severity(self, old_type: str, new_type: str) -> str:
        """
        Determine severity of a type change.

        Args:
            old_type: Old column type
            new_type: New column type

        Returns:
            Severity level: 'low', 'medium', 'high', or 'breaking'
        """
        old_lower = str(old_type).lower()
        new_lower = str(new_type).lower()

        # Compatible changes (low severity)
        compatible_numeric = {"int", "integer", "bigint", "smallint", "tinyint"}
        compatible_string = {"varchar", "char", "text", "string", "nvarchar"}
        compatible_date = {"date", "timestamp", "datetime", "time"}

        if old_lower in compatible_numeric and new_lower in compatible_numeric:
            return "low"
        if old_lower in compatible_string and new_lower in compatible_string:
            return "low"
        if old_lower in compatible_date and new_lower in compatible_date:
            return "low"

        # Potentially breaking changes (high severity)
        if old_lower in compatible_numeric and new_lower in compatible_string:
            return "breaking"
        if old_lower in compatible_string and new_lower in compatible_numeric:
            return "breaking"

        # Other changes (medium severity)
        return "medium"

    def close(self):
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
