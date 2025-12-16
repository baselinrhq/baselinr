"""
Drift detector for Baselinr.

Compares profiling results between runs to detect schema
and statistical drift in datasets.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import text

from ..config.schema import ColumnConfig, DriftDetectionConfig, StorageConfig
from ..events import DataDriftDetected, EventBus, SchemaChangeDetected
from ..profiling.column_matcher import ColumnMatcher
from .baseline_selector import BaselineResult, BaselineSelector
from .strategies import DriftDetectionStrategy, create_drift_strategy
from .type_normalizer import normalize_column_type
from .type_thresholds import create_type_thresholds

logger = logging.getLogger(__name__)


@dataclass
class ColumnDrift:
    """Represents drift detected in a single column."""

    column_name: str
    metric_name: str
    baseline_value: Any
    current_value: Any
    change_percent: Optional[float] = None
    change_absolute: Optional[float] = None
    drift_detected: bool = False
    drift_severity: str = "none"  # none, low, medium, high
    metadata: Optional[Dict[str, Any]] = None
    explanation: Optional[str] = None  # Human-readable explanation

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DriftReport:
    """Complete drift detection report."""

    dataset_name: str
    schema_name: Optional[str]
    baseline_run_id: str
    current_run_id: str
    baseline_timestamp: datetime
    current_timestamp: datetime
    column_drifts: List[ColumnDrift] = field(default_factory=list)
    schema_changes: List[str] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "dataset_name": self.dataset_name,
            "schema_name": self.schema_name,
            "baseline_run_id": self.baseline_run_id,
            "current_run_id": self.current_run_id,
            "baseline_timestamp": self.baseline_timestamp.isoformat(),
            "current_timestamp": self.current_timestamp.isoformat(),
            "column_drifts": [
                {
                    "column_name": d.column_name,
                    "metric_name": d.metric_name,
                    "baseline_value": d.baseline_value,
                    "current_value": d.current_value,
                    "change_percent": d.change_percent,
                    "change_absolute": d.change_absolute,
                    "drift_detected": d.drift_detected,
                    "drift_severity": d.drift_severity,
                    "metadata": d.metadata or {},
                    "explanation": d.explanation,
                }
                for d in self.column_drifts
            ],
            "schema_changes": self.schema_changes,
            "summary": self.summary,
        }


class DriftDetector:
    """Detects drift between profiling runs."""

    # Metrics that should be compared for drift
    NUMERIC_DRIFT_METRICS = [
        "count",
        "null_ratio",
        "unique_ratio",
        "mean",
        "stddev",
        "min",
        "max",
    ]

    def __init__(
        self,
        storage_config: StorageConfig,
        drift_config: Optional[DriftDetectionConfig] = None,
        event_bus: Optional[EventBus] = None,
        metrics_enabled: bool = False,
        retry_config=None,
        llm_config=None,
    ):
        """
        Initialize drift detector.

        Args:
            storage_config: Storage configuration
            drift_config: Drift detection configuration (uses defaults if not provided)
            event_bus: Optional event bus for emitting drift events
            metrics_enabled: Whether Prometheus metrics are enabled
            retry_config: Optional retry configuration
            llm_config: Optional LLM configuration for explanations
        """
        self.storage_config = storage_config
        self.drift_config = drift_config or DriftDetectionConfig()  # type: ignore[call-arg]
        self.retry_config = retry_config
        self.engine = self._setup_connection()
        self.event_bus = event_bus
        self.metrics_enabled = metrics_enabled
        self.llm_config = llm_config

        # Create type-specific thresholds if enabled
        self.type_thresholds = None
        if self.drift_config.enable_type_specific_thresholds:
            self.type_thresholds = create_type_thresholds(
                config=self.drift_config.type_specific_thresholds, enabled=True
            )

        # Create drift detection strategy based on config
        self.strategy = self._create_strategy()

    def _create_strategy(self) -> DriftDetectionStrategy:
        """Create drift detection strategy from configuration."""
        strategy_name = self.drift_config.strategy

        # Get parameters for the selected strategy
        if strategy_name == "absolute_threshold":
            params: Dict[str, Any] = self.drift_config.absolute_threshold.copy()
        elif strategy_name == "standard_deviation":
            params = self.drift_config.standard_deviation.copy()
        elif strategy_name == "ml_based":
            params = self.drift_config.ml_based.copy()
        elif strategy_name == "statistical":
            # Statistical strategy needs special handling
            stat_config = self.drift_config.statistical
            params = {
                "tests": stat_config.get("tests", ["ks_test", "psi", "chi_square"]),
                "sensitivity": stat_config.get("sensitivity", "medium"),
                "test_params": stat_config.get("test_params", {}),
            }
        else:
            logger.warning(f"Unknown strategy '{strategy_name}', using absolute_threshold")
            strategy_name = "absolute_threshold"
            params = self.drift_config.absolute_threshold.copy()

        # Add type_thresholds to params if available
        if self.type_thresholds:
            params["type_thresholds"] = self.type_thresholds

        logger.info(f"Using drift detection strategy: {strategy_name} with params: {params}")
        return create_drift_strategy(strategy_name, **params)

    def _setup_connection(self):
        """Setup database connection."""
        from ..connectors import (
            BigQueryConnector,
            MySQLConnector,
            PostgresConnector,
            RedshiftConnector,
            SnowflakeConnector,
            SQLiteConnector,
        )

        if self.storage_config.connection.type == "postgres":
            connector = PostgresConnector(self.storage_config.connection, self.retry_config)
        elif self.storage_config.connection.type == "snowflake":
            connector = SnowflakeConnector(self.storage_config.connection, self.retry_config)
        elif self.storage_config.connection.type == "sqlite":
            connector = SQLiteConnector(self.storage_config.connection, self.retry_config)
        elif self.storage_config.connection.type == "mysql":
            connector = MySQLConnector(self.storage_config.connection, self.retry_config)
        elif self.storage_config.connection.type == "bigquery":
            connector = BigQueryConnector(self.storage_config.connection, self.retry_config)
        elif self.storage_config.connection.type == "redshift":
            connector = RedshiftConnector(self.storage_config.connection, self.retry_config)
        else:
            raise ValueError(f"Unsupported storage type: {self.storage_config.connection.type}")

        return connector.engine

    def detect_drift(
        self,
        dataset_name: str,
        baseline_run_id: Optional[str] = None,
        current_run_id: Optional[str] = None,
        schema_name: Optional[str] = None,
        column_configs: Optional[List[ColumnConfig]] = None,
        profiled_columns: Optional[List[str]] = None,
    ) -> DriftReport:
        """
        Detect drift between two profiling runs.

        Args:
            dataset_name: Name of the dataset
            baseline_run_id: Run ID to use as baseline (default: second-latest)
            current_run_id: Run ID to compare against baseline (default: latest)
            schema_name: Optional schema name

        Returns:
            DriftReport with detected changes
        """
        import time

        from ..utils.logging import log_event

        start_time = time.time()
        log_event(
            logger,
            "drift_detection_started",
            f"Starting drift detection for dataset: {dataset_name}",
            metadata={
                "dataset_name": dataset_name,
                "schema_name": schema_name,
                "baseline_run_id": baseline_run_id,
                "current_run_id": current_run_id,
            },
        )

        # Get current run ID if not provided
        if current_run_id is None:
            run_ids = self._get_latest_runs(dataset_name, schema_name, limit=1)
            if len(run_ids) < 1:
                # Check if there are any runs at all, and what dataset names exist
                available_datasets = self._get_available_datasets()
                schema_hint = f" in schema '{schema_name}'" if schema_name else ""

                if not available_datasets:
                    error_msg = (
                        f"Need at least 1 run for drift detection, found {len(run_ids)}. "
                        f"No profiling runs found in database. "
                        f"Run 'baselinr profile' first to create profiling runs."
                    )
                else:
                    available_list = ", ".join(sorted(available_datasets)[:10])
                    if len(available_datasets) > 10:
                        available_list += f" (and {len(available_datasets) - 10} more)"
                    error_msg = (
                        f"Need at least 1 run for drift detection, found {len(run_ids)}. "
                        f"No profiling runs found for dataset '{dataset_name}'{schema_hint}. "
                        f"Available datasets: {available_list}. "
                        f"Run 'baselinr profile' first to create profiling runs."
                    )

                log_event(
                    logger,
                    "drift_detection_failed",
                    error_msg,
                    level="error",
                    metadata={
                        "dataset_name": dataset_name,
                        "schema_name": schema_name,
                        "run_count": len(run_ids),
                        "available_datasets": list(available_datasets),
                    },
                )
                raise ValueError(error_msg)
            current_run_id = run_ids[0]

        # Select baseline using BaselineSelector if not explicitly provided
        baseline_results: Optional[Dict[str, BaselineResult]] = None
        if baseline_run_id is None:
            baseline_strategy = self.drift_config.baselines.get("strategy", "last_run")

            # For auto-selection or non-last_run strategies, we need to select per-column
            # We'll defer the actual selection until we know which columns exist
            # For now, use BaselineSelector to get a baseline run ID for schema comparison
            if baseline_strategy == "auto" or baseline_strategy in [
                "moving_average",
                "prior_period",
                "stable_window",
            ]:
                # We'll select baselines per-column during metric drift detection
                # For schema detection, use last run as baseline
                fallback_runs = self._get_latest_runs(dataset_name, schema_name, limit=2)
                if len(fallback_runs) < 2:
                    error_msg = (
                        f"Need at least 2 runs for drift detection, " f"found {len(fallback_runs)}"
                    )
                    log_event(
                        logger,
                        "drift_detection_failed",
                        error_msg,
                        level="error",
                        metadata={"dataset_name": dataset_name, "run_count": len(fallback_runs)},
                    )
                    raise ValueError(error_msg)
                baseline_run_id = fallback_runs[1]  # Use second-latest for schema comparison
                baseline_results = {}  # Will be populated per-column
            else:
                # Simple last_run strategy: use second-latest run
                run_ids = self._get_latest_runs(dataset_name, schema_name, limit=2)
                if len(run_ids) < 2:
                    error_msg = f"Need at least 2 runs for drift detection, found {len(run_ids)}"
                    log_event(
                        logger,
                        "drift_detection_failed",
                        error_msg,
                        level="error",
                        metadata={"dataset_name": dataset_name, "run_count": len(run_ids)},
                    )
                    raise ValueError(error_msg)
                baseline_run_id = run_ids[1]

            log_event(
                logger,
                "drift_runs_selected",
                (
                    f"Using runs: baseline={baseline_run_id}, "
                    f"current={current_run_id} (strategy={baseline_strategy})"
                ),
                metadata={
                    "baseline_run_id": baseline_run_id,
                    "current_run_id": current_run_id,
                    "baseline_strategy": baseline_strategy,
                },
            )

        # Get run metadata
        baseline_meta = self._get_run_metadata(baseline_run_id)
        current_meta = self._get_run_metadata(current_run_id)

        # Create report
        report = DriftReport(
            dataset_name=dataset_name,
            schema_name=schema_name,
            baseline_run_id=baseline_run_id,
            current_run_id=current_run_id,
            baseline_timestamp=baseline_meta["profiled_at"],
            current_timestamp=current_meta["profiled_at"],
        )

        # Detect schema changes
        log_event(logger, "schema_change_detection_started", "Detecting schema changes")
        report.schema_changes = self._detect_schema_changes(baseline_run_id, current_run_id)

        # Detect metric drifts
        log_event(logger, "metric_drift_detection_started", "Detecting metric drifts")
        report.column_drifts = self._detect_metric_drifts(
            baseline_run_id,
            current_run_id,
            table_name=dataset_name,
            schema_name=schema_name,
            baseline_results=baseline_results,
            column_configs=column_configs,
            profiled_columns=profiled_columns,
        )

        # Generate summary
        report.summary = self._generate_summary(report)

        duration = time.time() - start_time

        # Get warehouse type for metrics
        warehouse = self.storage_config.connection.type

        # Record metrics: drift detection completed
        if self.metrics_enabled:
            from ..utils.metrics import record_drift_detection_completed

            record_drift_detection_completed(warehouse, dataset_name, duration)

        log_event(
            logger,
            "drift_detection_completed",
            f"Drift detection completed in {duration:.2f}s",
            metadata={
                "dataset_name": dataset_name,
                "duration_seconds": duration,
                "total_drifts": report.summary.get("total_drifts", 0),
                "schema_changes": len(report.schema_changes),
                "has_critical_drift": report.summary.get("has_critical_drift", False),
            },
        )

        # Emit events for detected drift
        if self.event_bus and report.summary.get("total_drifts", 0) > 0:
            for drift in report.column_drifts:
                if drift.drift_detected:
                    # Record metrics: drift event
                    if self.metrics_enabled:
                        from ..utils.metrics import record_drift_event

                        record_drift_event(
                            warehouse, dataset_name, drift.metric_name, drift.drift_severity
                        )

                    self.event_bus.emit(
                        DataDriftDetected(
                            event_type="DataDriftDetected",
                            timestamp=datetime.utcnow(),
                            table=dataset_name,
                            column=drift.column_name,
                            metric=drift.metric_name,
                            baseline_value=drift.baseline_value,
                            current_value=drift.current_value,
                            change_percent=drift.change_percent,
                            drift_severity=drift.drift_severity,
                            explanation=drift.explanation,
                            metadata={},
                        )
                    )

        # Emit events for schema changes
        if self.event_bus and report.schema_changes:
            # Record metrics: schema changes
            if self.metrics_enabled:
                from ..utils.metrics import record_schema_change

                for change in report.schema_changes:
                    # Parse change type from string (e.g., "Column added: foo" -> "column_added")
                    change_type = (
                        "column_added"
                        if "added" in change.lower()
                        else (
                            "column_removed"
                            if "removed" in change.lower()
                            else "type_changed" if "changed" in change.lower() else "unknown"
                        )
                    )
                    record_schema_change(warehouse, dataset_name, change_type)

            # Emit individual schema change events
            for change in report.schema_changes:
                # Parse change string like "column_added: new_column (varchar)"
                if ":" in change:
                    change_type, rest = change.split(":", 1)
                    change_type = change_type.strip()
                    column_info = rest.strip() if rest else None
                    # Try to extract column name and type
                    column = None
                    new_type = None
                    if column_info and "(" in column_info:
                        column = column_info.split("(")[0].strip()
                        type_part = column_info.split("(")[1].rstrip(")")
                        new_type = type_part.strip() if type_part else None
                    elif column_info:
                        column = column_info.strip()

                    # Generate explanation for schema change if LLM is enabled
                    explanation = None
                    if self.llm_config and self.llm_config.enabled:
                        try:
                            from ..llm.explainer import LLMExplainer

                            explainer = LLMExplainer(self.llm_config)
                            alert_data = {
                                "table": dataset_name,
                                "change_type": change_type,
                                "column": column,
                                "new_type": new_type,
                                "change_severity": "medium",
                            }
                            explanation = explainer.generate_explanation(
                                alert_data=alert_data,
                                alert_type="schema_change",
                                fallback_object=change,
                            )
                        except Exception as e:
                            logger.warning(f"Failed to generate schema change explanation: {e}")

                    self.event_bus.emit(
                        SchemaChangeDetected(
                            event_type="SchemaChangeDetected",
                            timestamp=datetime.utcnow(),
                            table=dataset_name,
                            change_type=change_type,
                            column=column,
                            new_type=new_type,
                            explanation=explanation,
                            metadata={},
                        )
                    )

        return report

    def _get_latest_runs(
        self, dataset_name: str, schema_name: Optional[str], limit: int = 2
    ) -> List[str]:
        """Get latest run IDs for a dataset.

        If schema_name is None, matches runs with any schema_name (including NULL).
        This allows drift detection to work when schema is not specified.
        """
        if schema_name:
            # Match specific schema
            query = text(
                f"""
                SELECT run_id FROM {self.storage_config.runs_table}
                WHERE dataset_name = :dataset_name
                AND schema_name = :schema_name
                ORDER BY profiled_at DESC
                LIMIT :limit
            """
            )
            params = {"dataset_name": dataset_name, "schema_name": schema_name, "limit": limit}
        else:
            # Match any schema (including NULL) - allows drift detection without schema
            query = text(
                f"""
                SELECT run_id FROM {self.storage_config.runs_table}
                WHERE dataset_name = :dataset_name
                ORDER BY profiled_at DESC
                LIMIT :limit
            """
            )
            params = {"dataset_name": dataset_name, "limit": limit}

        with self.engine.connect() as conn:
            result = conn.execute(query, params)
            return [row[0] for row in result]

    def _get_available_datasets(self) -> Set[str]:
        """Get all available dataset names from the runs table.

        Used for diagnostic purposes when drift detection fails.
        """
        try:
            query = text(
                f"""
                SELECT DISTINCT dataset_name FROM {self.storage_config.runs_table}
                ORDER BY dataset_name
            """
            )
            with self.engine.connect() as conn:
                result = conn.execute(query)
                return {row[0] for row in result}
        except Exception as e:
            logger.warning(f"Failed to query available datasets: {e}")
            return set()

    def _get_run_metadata(self, run_id: str) -> Dict[str, Any]:
        """Get metadata for a run."""
        query = text(
            f"""
            SELECT * FROM {self.storage_config.runs_table}
            WHERE run_id = :run_id
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(query, {"run_id": run_id}).fetchone()
            if not result:
                raise ValueError(f"Run not found: {run_id}")

            return {
                "run_id": result.run_id,
                "dataset_name": result.dataset_name,
                "schema_name": result.schema_name,
                "profiled_at": result.profiled_at,
                "row_count": result.row_count,
                "column_count": result.column_count,
            }

    def _detect_schema_changes(self, baseline_run_id: str, current_run_id: str) -> List[str]:
        """Detect schema changes between runs."""
        changes = []

        # Get column lists
        baseline_columns = self._get_columns(baseline_run_id)
        current_columns = self._get_columns(current_run_id)

        # Get table name from metadata
        baseline_meta = self._get_run_metadata(baseline_run_id)
        table_name = baseline_meta.get("dataset_name", "unknown")

        # Detect added columns
        added = current_columns - baseline_columns
        for col in added:
            changes.append(f"Column added: {col}")
            # Emit schema change event
            if self.event_bus:
                # Generate explanation for schema change if LLM is enabled
                explanation = None
                if self.llm_config and self.llm_config.enabled:
                    try:
                        from ..llm.explainer import LLMExplainer

                        explainer = LLMExplainer(self.llm_config)
                        alert_data = {
                            "table": table_name,
                            "change_type": "column_added",
                            "column": col,
                            "change_severity": "medium",
                        }
                        explanation = explainer.generate_explanation(
                            alert_data=alert_data,
                            alert_type="schema_change",
                            fallback_object=f"Column added: {col}",
                        )
                    except Exception as e:
                        logger.warning(f"Failed to generate schema change explanation: {e}")

                self.event_bus.emit(
                    SchemaChangeDetected(
                        event_type="SchemaChangeDetected",
                        timestamp=datetime.utcnow(),
                        table=table_name,
                        change_type="column_added",
                        column=col,
                        explanation=explanation,
                        metadata={},
                    )
                )

        # Detect removed columns
        removed = baseline_columns - current_columns
        for col in removed:
            changes.append(f"Column removed: {col}")
            # Emit schema change event
            if self.event_bus:
                # Generate explanation for schema change if LLM is enabled
                explanation = None
                if self.llm_config and self.llm_config.enabled:
                    try:
                        from ..llm.explainer import LLMExplainer

                        explainer = LLMExplainer(self.llm_config)
                        alert_data = {
                            "table": table_name,
                            "change_type": "column_removed",
                            "column": col,
                            "change_severity": "high",
                        }
                        explanation = explainer.generate_explanation(
                            alert_data=alert_data,
                            alert_type="schema_change",
                            fallback_object=f"Column removed: {col}",
                        )
                    except Exception as e:
                        logger.warning(f"Failed to generate schema change explanation: {e}")

                self.event_bus.emit(
                    SchemaChangeDetected(
                        event_type="SchemaChangeDetected",
                        timestamp=datetime.utcnow(),
                        table=table_name,
                        change_type="column_removed",
                        column=col,
                        explanation=explanation,
                        metadata={},
                    )
                )

        return changes

    def _get_columns(self, run_id: str) -> set:
        """Get set of columns for a run."""
        query = text(
            f"""
            SELECT DISTINCT column_name FROM {self.storage_config.results_table}
            WHERE run_id = :run_id
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(query, {"run_id": run_id})
            return {row[0] for row in result}

    def _detect_metric_drifts(
        self,
        baseline_run_id: str,
        current_run_id: str,
        table_name: Optional[str] = None,
        schema_name: Optional[str] = None,
        baseline_results: Optional[Dict[str, BaselineResult]] = None,
        column_configs: Optional[List[ColumnConfig]] = None,
        profiled_columns: Optional[List[str]] = None,
    ) -> List[ColumnDrift]:
        """Detect metric drifts between runs."""
        drifts = []

        # Initialize column matcher if column configs provided
        column_matcher = ColumnMatcher(column_configs=column_configs) if column_configs else None
        profiled_columns_set = set(profiled_columns) if profiled_columns else None

        # Get current run metrics
        current_metrics = self._get_metrics(current_run_id)

        # Initialize baseline selector if needed
        baseline_selector = None
        if baseline_results is not None:
            baseline_selector = BaselineSelector(
                self.storage_config, self.drift_config, self.engine
            )

        # Compare metrics
        for (column, metric), current_value in current_metrics.items():
            # Only compare numeric drift metrics
            if metric not in self.NUMERIC_DRIFT_METRICS:
                continue

            # Check if column was profiled (dependency check)
            if profiled_columns_set is not None and column not in profiled_columns_set:
                logger.debug(
                    f"Skipping drift detection for column {column}: column was not profiled"
                )
                continue

            # Check if drift detection is enabled for this column
            if not self._should_detect_drift(column, column_matcher):
                logger.debug(f"Skipping drift detection for column {column}: drift disabled")
                continue

            # Get baseline value
            baseline_value = None
            baseline_result = None

            if baseline_results is not None and baseline_selector:
                # Use BaselineSelector for per-column baseline selection
                key = f"{column}:{metric}"
                if key not in baseline_results:
                    try:
                        baseline_result = baseline_selector.select_baseline(
                            dataset_name=table_name or "",
                            column_name=column,
                            metric_name=metric,
                            current_run_id=current_run_id,
                            schema_name=schema_name,
                        )
                        baseline_results[key] = baseline_result
                    except Exception as e:
                        logger.warning(
                            f"Failed to select baseline for {column}.{metric}: {e}, "
                            "falling back to simple baseline"
                        )
                        # Fallback to simple baseline
                        baseline_metrics = self._get_metrics(baseline_run_id)
                        baseline_value = baseline_metrics.get((column, metric))
                else:
                    baseline_result = baseline_results[key]

                if baseline_result:
                    baseline_value = baseline_result.baseline_value
            else:
                # Use simple baseline from baseline_run_id
                baseline_metrics = self._get_metrics(baseline_run_id)
                baseline_value = baseline_metrics.get((column, metric))

            if baseline_value is None:
                continue

            # Get merged drift config for this column
            merged_drift_config = self._get_column_drift_config(column, column_matcher)

            # Calculate drift
            # Use baseline_run_id from result if available, otherwise use the provided one
            actual_baseline_run_id = (
                baseline_result.baseline_run_id if baseline_result else baseline_run_id
            )
            drift = self._calculate_drift(
                column,
                metric,
                baseline_value,
                current_value,
                baseline_run_id=actual_baseline_run_id,
                current_run_id=current_run_id,
                merged_drift_config=merged_drift_config,
                table_name=table_name,
            )
            if drift:
                drifts.append(drift)

                # Add baseline method info to drift metadata if available
                if baseline_result:
                    drift.metadata = drift.metadata or {}
                    drift.metadata["baseline_method"] = baseline_result.method
                    if baseline_result.metadata:
                        drift.metadata.update(baseline_result.metadata)

                # Emit drift event if detected and event bus is available
                if drift.drift_detected and self.event_bus and table_name:
                    self.event_bus.emit(
                        DataDriftDetected(
                            event_type="DataDriftDetected",
                            timestamp=datetime.utcnow(),
                            table=table_name,
                            column=column,
                            metric=metric,
                            baseline_value=baseline_value,
                            current_value=current_value,
                            change_percent=drift.change_percent,
                            drift_severity=drift.drift_severity,
                            explanation=drift.explanation,
                            metadata=drift.metadata or {},
                        )
                    )

        return drifts

    def _get_metrics(self, run_id: str) -> Dict[tuple, Any]:
        """Get all metrics for a run as {(column, metric): value}."""
        query = text(
            f"""
            SELECT column_name, metric_name, metric_value
            FROM {self.storage_config.results_table}
            WHERE run_id = :run_id
        """
        )

        metrics = {}
        with self.engine.connect() as conn:
            result = conn.execute(query, {"run_id": run_id})
            for row in result:
                key = (row.column_name, row.metric_name)
                # Try to convert to float
                try:
                    metrics[key] = float(row.metric_value) if row.metric_value else None
                except (ValueError, TypeError):
                    metrics[key] = row.metric_value

        return metrics

    def _get_column_type(self, run_id: str, column_name: str) -> Optional[str]:
        """Get column type for a specific column in a run."""
        query = text(
            f"""
            SELECT DISTINCT column_type
            FROM {self.storage_config.results_table}
            WHERE run_id = :run_id AND column_name = :column_name
            LIMIT 1
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(query, {"run_id": run_id, "column_name": column_name}).fetchone()
            return result[0] if result else None

    def _get_histogram_data(self, run_id: str, column_name: str) -> Optional[Any]:
        """Get histogram data for a column if available."""
        query = text(
            f"""
            SELECT metric_value
            FROM {self.storage_config.results_table}
            WHERE run_id = :run_id
            AND column_name = :column_name
            AND metric_name = 'histogram'
            LIMIT 1
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(query, {"run_id": run_id, "column_name": column_name}).fetchone()
            return result[0] if result else None

    def _get_category_distribution(
        self, run_id: str, column_name: str
    ) -> Optional[Dict[str, float]]:
        """Get category distribution for a categorical column if available."""
        # Try to get top_values or distinct_count metrics
        query = text(
            f"""
            SELECT metric_name, metric_value
            FROM {self.storage_config.results_table}
            WHERE run_id = :run_id
            AND column_name = :column_name
            AND metric_name IN ('top_values', 'distinct_count', 'category_distribution')
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(query, {"run_id": run_id, "column_name": column_name})
            distribution = {}
            for row in result:
                if row.metric_name == "category_distribution":
                    # Parse JSON if stored as string
                    import json

                    try:
                        if isinstance(row.metric_value, str):
                            distribution = json.loads(row.metric_value)
                        else:
                            distribution = row.metric_value
                    except Exception:
                        pass
                elif row.metric_name == "top_values":
                    # Parse top values
                    import json

                    try:
                        if isinstance(row.metric_value, str):
                            distribution = json.loads(row.metric_value)
                        else:
                            distribution = row.metric_value
                    except Exception:
                        pass

            return distribution if distribution else None

    def _should_detect_drift(
        self, column_name: str, column_matcher: Optional[ColumnMatcher]
    ) -> bool:
        """
        Check if drift detection should be performed for a column.

        Args:
            column_name: Name of the column
            column_matcher: Optional column matcher with column configs

        Returns:
            True if drift should be detected, False otherwise
        """
        if column_matcher is None:
            # No column configs: use default (drift enabled)
            return True

        column_config = column_matcher.get_column_drift_config(column_name)
        if column_config and column_config.drift:
            # Check if drift is explicitly disabled
            if column_config.drift.enabled is False:
                return False
            # If enabled is None or True, proceed with drift detection
            return True

        # No column-specific config: use default (drift enabled)
        return True

    def _get_column_drift_config(self, column_name: str, column_matcher: Optional[ColumnMatcher]):
        """
        Get merged drift configuration for a column.

        Merges column-specific config with table-level and global defaults.

        Args:
            column_name: Name of the column
            column_matcher: Optional column matcher with column configs

        Returns:
            Merged drift config dict
        """
        if column_matcher is None:
            return self.drift_config

        column_config = column_matcher.get_column_drift_config(column_name)
        if column_config and column_config.drift:
            drift_cfg = column_config.drift

            # Merge column-specific config with defaults
            merged = DriftDetectionConfig(**self.drift_config.model_dump())

            # Override strategy if specified
            if drift_cfg.strategy:
                merged.strategy = drift_cfg.strategy

            # Override thresholds if specified
            if drift_cfg.thresholds:
                # Map column thresholds (low, medium, high) to config format
                threshold_map = {
                    "low": "low_threshold",
                    "medium": "medium_threshold",
                    "high": "high_threshold",
                }
                if merged.strategy == "absolute_threshold":
                    for key, mapped_key in threshold_map.items():
                        if key in drift_cfg.thresholds:
                            merged.absolute_threshold[mapped_key] = drift_cfg.thresholds[key]
                elif merged.strategy == "standard_deviation":
                    for key, mapped_key in threshold_map.items():
                        if key in drift_cfg.thresholds:
                            merged.standard_deviation[mapped_key] = drift_cfg.thresholds[key]

            # Override baselines if specified
            if drift_cfg.baselines:
                merged.baselines.update(drift_cfg.baselines)

            return merged

        return self.drift_config

    def _calculate_drift(
        self,
        column_name: str,
        metric_name: str,
        baseline_value: Any,
        current_value: Any,
        baseline_run_id: Optional[str] = None,
        current_run_id: Optional[str] = None,
        merged_drift_config: Optional[DriftDetectionConfig] = None,
        table_name: Optional[str] = None,
    ) -> Optional[ColumnDrift]:
        """Calculate drift for a metric using the configured strategy."""
        # Use column-specific drift config if provided, otherwise use default
        drift_config_to_use = merged_drift_config if merged_drift_config else self.drift_config

        # Always get column type for type-specific threshold support
        kwargs = {}
        column_type = None
        if baseline_run_id:
            column_type_raw = self._get_column_type(baseline_run_id, column_name)
            if column_type_raw:
                # Normalize column type
                column_type = normalize_column_type(column_type_raw)
                kwargs["column_type"] = column_type

        # Prepare additional data for statistical tests if strategy is statistical
        if drift_config_to_use.strategy == "statistical" and baseline_run_id and current_run_id:
            # Get histogram data if available
            baseline_hist = self._get_histogram_data(baseline_run_id, column_name)
            current_hist = self._get_histogram_data(current_run_id, column_name)

            # Get category distribution if categorical
            baseline_cat = self._get_category_distribution(baseline_run_id, column_name)
            current_cat = self._get_category_distribution(current_run_id, column_name)

            # Build baseline and current data dicts
            baseline_data = {"value": baseline_value}
            current_data = {"value": current_value}

            if baseline_hist:
                baseline_data["histogram"] = baseline_hist
            if current_hist:
                current_data["histogram"] = current_hist
            if baseline_cat:
                baseline_data["category_distribution"] = baseline_cat
            if current_cat:
                current_data["category_distribution"] = current_cat

            kwargs["baseline_data"] = baseline_data  # type: ignore[assignment]
            kwargs["current_data"] = current_data  # type: ignore[assignment]

        # Create column-specific strategy if merged_drift_config differs from default
        strategy_to_use = self.strategy
        # Check if we need a column-specific strategy by comparing key attributes
        needs_custom_strategy = False
        if merged_drift_config and merged_drift_config is not self.drift_config:
            # Check if strategy or thresholds differ
            if merged_drift_config.strategy != self.drift_config.strategy:
                needs_custom_strategy = True
            elif merged_drift_config.strategy == "absolute_threshold":
                if merged_drift_config.absolute_threshold != self.drift_config.absolute_threshold:
                    needs_custom_strategy = True
            elif merged_drift_config.strategy == "standard_deviation":
                if merged_drift_config.standard_deviation != self.drift_config.standard_deviation:
                    needs_custom_strategy = True

        if needs_custom_strategy:
            # Get parameters for the column-specific strategy
            strategy_name = drift_config_to_use.strategy
            params: Dict[str, Any] = {}
            if strategy_name == "absolute_threshold":
                params = drift_config_to_use.absolute_threshold.copy()
            elif strategy_name == "standard_deviation":
                params = drift_config_to_use.standard_deviation.copy()
            elif strategy_name == "statistical":
                stat_config = drift_config_to_use.statistical
                params = {
                    "tests": stat_config.get("tests", ["ks_test", "psi", "chi_square"]),
                    "sensitivity": stat_config.get("sensitivity", "medium"),
                    "test_params": stat_config.get("test_params", {}),
                }

            # Add type_thresholds if available
            if self.type_thresholds:
                params["type_thresholds"] = self.type_thresholds

            # Create new strategy instance with column-specific config
            strategy_to_use = create_drift_strategy(strategy_name, **params)

        # Use the configured strategy to calculate drift
        result = strategy_to_use.calculate_drift(
            baseline_value=baseline_value,
            current_value=current_value,
            metric_name=metric_name,
            column_name=column_name,
            **kwargs,
        )

        # If strategy couldn't calculate drift, return None
        if result is None:
            return None

            # Convert DriftResult to ColumnDrift
        drift = ColumnDrift(
            column_name=column_name,
            metric_name=metric_name,
            baseline_value=baseline_value,
            current_value=current_value,
            change_percent=result.change_percent,
            change_absolute=result.change_absolute,
            drift_detected=result.drift_detected,
            drift_severity=result.drift_severity,
            metadata=result.metadata or {},
        )
        # Store table name in metadata for template generation
        if table_name and drift.metadata:
            drift.metadata["table_name"] = table_name

        # Generate LLM explanation if enabled and drift was detected
        if drift.drift_detected and self.llm_config and self.llm_config.enabled:
            try:
                from ..llm.explainer import LLMExplainer

                explainer = LLMExplainer(self.llm_config)
                alert_data = {
                    "table": table_name or "unknown",
                    "column": column_name,
                    "metric": metric_name,
                    "baseline_value": baseline_value,
                    "current_value": current_value,
                    "change_percent": result.change_percent,
                    "change_absolute": result.change_absolute,
                    "drift_severity": result.drift_severity,
                    "metadata": drift.metadata,
                }
                drift.explanation = explainer.generate_explanation(
                    alert_data=alert_data, alert_type="drift", fallback_object=drift
                )
            except Exception as e:
                logger.warning(f"Failed to generate drift explanation: {e}")

        # Emit drift event if drift was detected and event bus is available
        if drift.drift_detected and self.event_bus:
            # Get table name from current context (we'll need to pass this through)
            # For now, we'll extract it from the run metadata
            self.event_bus.emit(
                DataDriftDetected(
                    event_type="DataDriftDetected",
                    timestamp=datetime.utcnow(),
                    table="unknown",  # Will be set in detect_drift
                    column=column_name,
                    metric=metric_name,
                    baseline_value=baseline_value,
                    current_value=current_value,
                    change_percent=result.change_percent,
                    drift_severity=result.drift_severity,
                    explanation=drift.explanation,
                    metadata={},
                )
            )

        return drift

    def _generate_summary(self, report: DriftReport) -> Dict[str, Any]:
        """Generate summary statistics for drift report."""
        total_drifts = len([d for d in report.column_drifts if d.drift_detected])

        drift_by_severity = {
            "high": len([d for d in report.column_drifts if d.drift_severity == "high"]),
            "medium": len([d for d in report.column_drifts if d.drift_severity == "medium"]),
            "low": len([d for d in report.column_drifts if d.drift_severity == "low"]),
        }

        return {
            "total_drifts": total_drifts,
            "schema_changes": len(report.schema_changes),
            "drift_by_severity": drift_by_severity,
            "has_critical_drift": drift_by_severity["high"] > 0,
        }
