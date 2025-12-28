"""
Core profiling engine for Baselinr.

Orchestrates the profiling of database tables and columns,
collecting schema information and computing metrics.
"""

import logging
import time
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config.merger import ConfigMerger
from ..config.schema import BaselinrConfig, TablePattern
from ..connectors.base import BaseConnector
from ..connectors.factory import create_connector
from ..events import EventBus, ProfilingCompleted, ProfilingFailed, ProfilingStarted
from .column_matcher import ColumnMatcher
from .metrics import MetricCalculator
from .query_builder import QueryBuilder

logger = logging.getLogger(__name__)


class ProfilingResult:
    """Container for profiling results."""

    def __init__(
        self, run_id: str, dataset_name: str, schema_name: Optional[str], profiled_at: datetime
    ):
        """
        Initialize profiling result container.

        Args:
            run_id: Unique identifier for this profiling run
            dataset_name: Name of the dataset/table profiled
            schema_name: Schema name (if applicable)
            profiled_at: Timestamp of profiling
        """
        self.run_id = run_id
        self.dataset_name = dataset_name
        self.schema_name = schema_name
        self.profiled_at = profiled_at
        self.columns: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}

    def add_column_metrics(self, column_name: str, column_type: str, metrics: Dict[str, Any]):
        """
        Add metrics for a column.

        Args:
            column_name: Name of the column
            column_type: Data type of the column
            metrics: Dictionary of metric_name -> metric_value
        """
        self.columns.append(
            {"column_name": column_name, "column_type": column_type, "metrics": metrics}
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "run_id": self.run_id,
            "dataset_name": self.dataset_name,
            "schema_name": self.schema_name,
            "profiled_at": self.profiled_at.isoformat(),
            "columns": self.columns,
            "metadata": self.metadata,
        }


class ProfileEngine:
    """Main profiling engine for Baselinr."""

    def __init__(
        self,
        config: BaselinrConfig,
        event_bus: Optional[EventBus] = None,
        run_context: Optional[Any] = None,
    ):
        """
        Initialize profiling engine.

        Args:
            config: Baselinr configuration
            event_bus: Optional event bus for emitting profiling events
            run_context: Optional run context with logger and run_id
        """
        self.config = config
        self.connector: Optional[BaseConnector] = None
        self._connector_cache: Dict[Optional[str], BaseConnector] = {}  # database -> connector
        self.metric_calculator: Optional[MetricCalculator] = None
        self._metric_calculator_cache: Dict[Optional[str], MetricCalculator] = (
            {}
        )  # database -> calculator
        self.event_bus = event_bus
        self.run_context = run_context

        # Get logger from run_context or create fallback
        if run_context:
            self.logger = run_context.logger
            self.run_id = run_context.run_id
        else:
            import logging

            self.logger = logging.getLogger(__name__)
            import uuid

            self.run_id = str(uuid.uuid4())

        # Initialize worker pool ONLY if parallelism is enabled
        self.execution_config = config.execution
        self.worker_pool: Optional[Any] = None
        self.progress_callback: Optional[Any] = None

        # Only create worker pool if max_workers > 1
        if self.execution_config.max_workers > 1:
            # Determine warehouse-specific worker limit
            warehouse_limit = self.execution_config.warehouse_limits.get(
                self.config.source.type, self.execution_config.max_workers
            )

            # Special handling for SQLite (single writer)
            if self.config.source.type == "sqlite":
                warehouse_limit = 1  # SQLite doesn't support concurrent writes well
                self.logger.warning(
                    "SQLite does not support parallel writes. Using sequential execution."
                )

            if warehouse_limit > 1:
                from ..utils.worker_pool import WorkerPool

                self.worker_pool = WorkerPool(
                    max_workers=warehouse_limit,
                    queue_size=self.execution_config.queue_size,
                    warehouse_type=self.config.source.type,
                )
                self.logger.info(f"Parallel execution enabled with {warehouse_limit} workers")
        else:
            from ..utils.logging import log_event

            log_event(
                self.logger,
                "execution_mode",
                "Sequential execution (max_workers=1, default)",
                level="debug",
            )

    def profile(
        self,
        table_patterns: Optional[List[TablePattern]] = None,
        progress_callback: Optional[Any] = None,
    ) -> List[ProfilingResult]:
        """
        Profile tables with optional parallel execution.

        If max_workers=1 (default), uses sequential execution (existing behavior).
        If max_workers > 1, uses parallel execution via worker pool.

        Args:
            table_patterns: Optional list of table patterns to profile
                          (uses config if not provided)
            progress_callback: Optional callback function(current, total, table_name)
                             called when starting each table

        Returns:
            List of profiling results
        """
        patterns = table_patterns or self.config.profiling.tables

        if not patterns:
            logger.warning("No table patterns specified for profiling")
            return []

        # Create connector with retry config
        retry_config = self.config.retry
        execution_config = self.config.execution

        self.connector = create_connector(
            self.config.source, retry_config=retry_config, execution_config=execution_config
        )

        # Create query builder for partition/sampling support
        self.query_builder = QueryBuilder(database_type=self.config.source.type)

        # Create metric calculator
        self.metric_calculator = MetricCalculator(
            engine=self.connector.engine,
            max_distinct_values=self.config.profiling.max_distinct_values,
            compute_histograms=self.config.profiling.compute_histograms,
            histogram_bins=self.config.profiling.histogram_bins,
            enabled_metrics=self.config.profiling.metrics,
            query_builder=self.query_builder,
            enable_enrichment=self.config.profiling.enable_enrichment,
            enable_approx_distinct=self.config.profiling.enable_approx_distinct,
            enable_type_inference=self.config.profiling.enable_type_inference,
            type_inference_sample_size=self.config.profiling.type_inference_sample_size,
        )

        # Store progress callback for use in _profile_sequential and _profile_parallel
        self.progress_callback = progress_callback

        # Route to parallel or sequential execution
        try:
            if self.worker_pool:
                return self._profile_parallel(patterns)
            else:
                return self._profile_sequential(patterns)
        finally:
            # Cleanup
            if self.connector:
                self.connector.close()
            if self.worker_pool:
                self.worker_pool.shutdown(wait=True)

    def _profile_parallel(self, patterns: List[TablePattern]) -> List[ProfilingResult]:
        """
        Profile tables in parallel using worker pool.
        Only called when max_workers > 1.

        Args:
            patterns: List of table patterns to profile

        Returns:
            List of profiling results
        """
        from ..utils.worker_pool import profile_table_task

        if self.worker_pool is None:
            raise RuntimeError("Worker pool is not initialized")

        # Submit all tasks
        futures = []
        for pattern in patterns:
            future = self.worker_pool.submit(
                profile_table_task,
                self,  # Pass engine instance
                pattern,
                self.run_context,
                self.event_bus,
            )
            futures.append(future)

        # Wait for completion
        results = self.worker_pool.wait_for_completion(futures)

        # Filter out None results (failed tasks)
        successful = [r for r in results if r is not None]
        failed_count = len(results) - len(successful)

        if failed_count > 0:
            logger.warning(
                f"Parallel profiling completed: {len(successful)} succeeded, {failed_count} failed"
            )

        return successful

    def _profile_sequential(self, patterns: List[TablePattern]) -> List[ProfilingResult]:
        """
        Profile tables sequentially (existing implementation).
        This is the default behavior when max_workers=1.

        Args:
            patterns: List of table patterns to profile

        Returns:
            List of profiling results
        """
        results = []
        warehouse = self.config.source.type  # Get warehouse type for metrics
        total = len(patterns)

        for idx, pattern in enumerate(patterns):
            assert pattern.table is not None, "Table name must be set"
            fq_table = f"{pattern.schema_}.{pattern.table}" if pattern.schema_ else pattern.table
            start_time = time.time()

            # Call progress callback if provided
            if self.progress_callback:
                try:
                    self.progress_callback(idx + 1, total, fq_table)
                except Exception as e:
                    logger.debug(f"Progress callback error: {e}")

            try:
                from ..utils.logging import log_and_emit

                # Record metrics: profiling started
                if self.run_context and self.run_context.metrics_enabled:
                    from ..utils.metrics import record_profile_started

                    assert pattern.table is not None, "Table name must be set"
                    record_profile_started(warehouse, fq_table)

                # Log and emit profiling started
                log_and_emit(
                    self.logger,
                    self.event_bus,
                    "profiling_started",
                    f"Starting profiling for table: {fq_table}",
                    table=fq_table,
                    run_id=self.run_id,
                )

                result = self._profile_table(pattern)
                results.append(result)

                # Calculate duration
                duration = time.time() - start_time

                # Record metrics: profiling completed
                if self.run_context and self.run_context.metrics_enabled:
                    from ..utils.metrics import record_profile_completed

                    record_profile_completed(
                        warehouse,
                        fq_table,
                        duration,
                        row_count=result.metadata.get("row_count", 0),
                        column_count=len(result.columns),
                    )

                # Log and emit profiling completed
                log_and_emit(
                    self.logger,
                    self.event_bus,
                    "profiling_completed",
                    f"Profiling completed for table: {fq_table}",
                    table=fq_table,
                    run_id=self.run_id,
                    metadata={
                        "column_count": len(result.columns),
                        "row_count": result.metadata.get("row_count", 0),
                    },
                )
            except Exception as e:
                from ..utils.logging import log_and_emit

                # Calculate duration
                duration = time.time() - start_time

                # Record metrics: profiling failed
                if self.run_context and self.run_context.metrics_enabled:
                    from ..utils.metrics import record_profile_failed

                    record_profile_failed(warehouse, fq_table, duration)

                # Log and emit failure
                # Safely extract error information without accessing exception internals
                # that might trigger DBAPIError reconstruction
                try:
                    error_msg = str(e) if e else "Unknown error"
                except Exception:
                    error_msg = "Unknown error (could not stringify exception)"

                try:
                    error_type = type(e).__name__ if e else "UnknownError"
                except Exception:
                    error_type = "Exception"

                try:
                    error_repr = repr(e) if e else "Unknown error"
                except Exception:
                    error_repr = "Unknown error (could not repr exception)"

                log_and_emit(
                    self.logger,
                    self.event_bus,
                    "profiling_error",
                    f"Failed to profile table {fq_table}: {error_msg}",
                    level="error",
                    table=fq_table,
                    run_id=self.run_id,
                    metadata={
                        "error": error_msg,
                        "error_type": error_type,
                        "error_repr": error_repr,
                    },
                )

                # Continue processing other tables instead of aborting
                logger.warning(f"Continuing with remaining tables after failure on {fq_table}")

        return results

    def _profile_table(self, pattern: TablePattern) -> ProfilingResult:
        """
        Profile a single table.

        Args:
            pattern: Table pattern configuration

        Returns:
            ProfilingResult for this table
        """
        # Ensure table name is set (should be after pattern expansion)
        assert pattern.table is not None, "Table name must be set for profiling"

        # Use run_id from context
        run_id = self.run_id
        profiled_at = datetime.utcnow()
        start_time = time.time()

        fq_table = f"{pattern.schema_}.{pattern.table}" if pattern.schema_ else pattern.table
        from ..utils.logging import log_event

        log_event(
            self.logger,
            "table_profiling_started",
            f"Profiling table: {fq_table}",
            table=fq_table,
            metadata={"pattern": pattern.table},
        )

        # Emit profiling started event
        if self.event_bus:
            self.event_bus.emit(
                ProfilingStarted(
                    event_type="ProfilingStarted",
                    timestamp=profiled_at,
                    table=pattern.table,
                    run_id=run_id,
                    metadata={},
                )
            )

        try:
            # Get database-specific connector
            cache_key = None if pattern.database is None else pattern.database

            if cache_key not in self._connector_cache:
                # Create database-specific connector
                if pattern.database is None:
                    # Use default connector (already created)
                    if self.connector is None:
                        self.connector = create_connector(
                            self.config.source,
                            retry_config=self.config.retry,
                            execution_config=self.config.execution,
                        )
                    connector = self.connector
                else:
                    # Create connector for specified database
                    db_config = deepcopy(self.config.source)
                    db_config.database = pattern.database
                    connector = create_connector(
                        db_config,
                        retry_config=self.config.retry,
                        execution_config=self.config.execution,
                    )
                self._connector_cache[cache_key] = connector
            else:
                connector = self._connector_cache[cache_key]

            # Also set as default connector if not set (for backward compatibility)
            if self.connector is None:
                self.connector = connector

            # Get or create database-specific metric calculator
            if cache_key not in self._metric_calculator_cache:
                calculator = MetricCalculator(
                    engine=connector.engine,
                    max_distinct_values=self.config.profiling.max_distinct_values,
                    compute_histograms=self.config.profiling.compute_histograms,
                    histogram_bins=self.config.profiling.histogram_bins,
                    enabled_metrics=self.config.profiling.metrics,
                    query_builder=self.query_builder,
                    enable_enrichment=self.config.profiling.enable_enrichment,
                    enable_approx_distinct=self.config.profiling.enable_approx_distinct,
                    enable_type_inference=self.config.profiling.enable_type_inference,
                    type_inference_sample_size=self.config.profiling.type_inference_sample_size,
                )
                self._metric_calculator_cache[cache_key] = calculator
            else:
                calculator = self._metric_calculator_cache[cache_key]

            # Also set as default metric calculator if not set (for backward compatibility)
            if self.metric_calculator is None:
                self.metric_calculator = calculator

            # Ensure table name is set (should already be set by planner expansion)
            if pattern.table is None:
                raise ValueError(f"Table name is required for profiling. Pattern: {pattern}")
            table_name = pattern.table

            # Get table metadata using database-specific connector
            table = connector.get_table(table_name, schema=pattern.schema_)

            # Resolve profiling config from contracts
            merger = ConfigMerger(self.config)
            profiling_config = merger.merge_profiling_config(
                table_pattern=pattern,
                database_name=pattern.database,
                schema=pattern.schema_,
                table=table_name,
            )

            # Extract merged config values
            partition_config = profiling_config.get("partition")
            sampling_config = profiling_config.get("sampling")
            column_configs = profiling_config.get("columns")

            # Create result container
            result = ProfilingResult(
                run_id=run_id,
                dataset_name=table_name,
                schema_name=pattern.schema_,
                profiled_at=profiled_at,
            )

            # Infer partition key if metadata_fallback is enabled
            if partition_config and partition_config.metadata_fallback and not partition_config.key:
                inferred_key = self.query_builder.infer_partition_key(table)
                if inferred_key:
                    partition_config.key = inferred_key
                    logger.info(f"Using inferred partition key: {inferred_key}")

            # Add table metadata
            current_row_count = self._get_row_count(
                table, partition_config, sampling_config, connector
            )
            result.metadata["row_count"] = current_row_count
            result.metadata["column_count"] = len(table.columns)
            result.metadata["partition_config"] = (
                partition_config.model_dump() if partition_config else None
            )
            result.metadata["sampling_config"] = (
                sampling_config.model_dump() if sampling_config else None
            )

            # Initialize column matcher if column configs exist
            column_matcher = (
                ColumnMatcher(column_configs=column_configs) if column_configs else None
            )

            # Determine which columns to profile
            all_column_names = [col.name for col in table.columns]
            if column_matcher:
                profiled_column_names = column_matcher.get_profiled_columns(
                    all_column_names, include_defaults=True
                )
            else:
                # No column configs: profile all columns (backward compatibility)
                profiled_column_names = set(all_column_names)

            # Track which columns were actually profiled (for drift/anomaly dependency checking)
            actually_profiled = set()

            # Profile each column
            for column in table.columns:
                column_name = column.name

                # Skip columns that shouldn't be profiled
                if column_name not in profiled_column_names:
                    logger.debug(f"Skipping column {column_name} (not in profiled columns)")
                    continue

                logger.debug(f"Profiling column: {column_name}")

                try:
                    if calculator is None:
                        raise RuntimeError("Metric calculator is not initialized")

                    # Get column-specific metrics if configured
                    column_metrics = None
                    if column_matcher:
                        column_metrics = column_matcher.get_column_metrics(column_name)

                    # Create column-specific calculator if needed
                    column_calculator = calculator
                    if column_metrics is not None:
                        # Create a new calculator with column-specific metrics
                        column_calculator = MetricCalculator(
                            engine=calculator.engine,
                            max_distinct_values=calculator.max_distinct_values,
                            compute_histograms=calculator.compute_histograms,
                            histogram_bins=calculator.histogram_bins,
                            enabled_metrics=column_metrics,
                            query_builder=calculator.query_builder,
                            enable_enrichment=calculator.enable_enrichment,
                            enable_approx_distinct=calculator.enable_approx_distinct,
                            enable_type_inference=calculator.enable_type_inference,
                            type_inference_sample_size=calculator.type_inference_sample_size,
                        )

                    metrics = column_calculator.calculate_all_metrics(
                        table=table,
                        column_name=column_name,
                        partition_config=partition_config,
                        sampling_config=sampling_config,
                    )

                    result.add_column_metrics(
                        column_name=column_name, column_type=str(column.type), metrics=metrics
                    )
                    actually_profiled.add(column_name)
                except Exception as e:
                    logger.error(f"Failed to profile column {column_name}: {e}")
                    # Add error marker (still counts as attempted profiling)
                    result.add_column_metrics(
                        column_name=column_name,
                        column_type=str(column.type),
                        metrics={"error": str(e)},
                    )
                    # Don't add to actually_profiled since it failed

            # Store list of actually profiled columns for drift/anomaly dependency checking
            result.metadata["profiled_columns"] = list(actually_profiled)
            result.metadata["column_configs"] = (
                [col.model_dump() for col in column_configs] if column_configs else None
            )

            # Store schema snapshot for enrichment metrics (calculated during storage write)
            if self.config.profiling.enable_enrichment:
                current_columns = {col["column_name"]: col["column_type"] for col in result.columns}
                result.metadata["column_schema"] = current_columns

            # Schema change detection happens in storage writer
            # where we have access to storage engine

            # Calculate duration
            duration = time.time() - start_time

            # Emit profiling completed event
            if self.event_bus:
                self.event_bus.emit(
                    ProfilingCompleted(
                        event_type="ProfilingCompleted",
                        timestamp=datetime.utcnow(),
                        table=table_name,
                        run_id=run_id,
                        row_count=result.metadata.get("row_count", 0),
                        column_count=result.metadata.get("column_count", 0),
                        duration_seconds=duration,
                        metadata={},
                    )
                )

            logger.info(
                f"Successfully profiled {table_name} with {len(result.columns)} "
                f"columns in {duration:.2f}s"
            )
            return result

        except Exception as e:
            # Emit profiling failed event
            if self.event_bus:
                # Use table_name if available, otherwise fall back to pattern.table or "unknown"
                failed_table = table_name or pattern.table or "unknown"
                self.event_bus.emit(
                    ProfilingFailed(
                        event_type="ProfilingFailed",
                        timestamp=datetime.utcnow(),
                        table=failed_table,
                        run_id=run_id,
                        error=str(e),
                        metadata={},
                    )
                )
            raise

    def _get_row_count(
        self, table, partition_config=None, sampling_config=None, connector=None
    ) -> int:
        """
        Get row count for a table (with optional partition/sampling).

        Args:
            table: SQLAlchemy Table object
            partition_config: Partition configuration
            sampling_config: Sampling configuration
            connector: Optional connector to use (defaults to self.connector)

        Returns:
            Row count
        """
        from sqlalchemy import func, select

        # Use provided connector or fall back to default
        conn_to_use = connector if connector is not None else self.connector
        if conn_to_use is None:
            raise RuntimeError("Connector is not initialized")
        with conn_to_use.engine.connect() as conn:
            # Build query with partition filtering
            query, _ = self.query_builder.build_profiling_query(
                table=table,
                partition_config=partition_config,
                sampling_config=None,  # Don't apply sampling for count
            )

            # Count rows
            count_query = select(func.count()).select_from(query.alias())
            result = conn.execute(count_query).scalar()
            return int(result) if result is not None else 0
