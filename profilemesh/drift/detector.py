"""
Drift detector for ProfileMesh.

Compares profiling results between runs to detect schema
and statistical drift in datasets.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging
from sqlalchemy import text

from ..config.schema import StorageConfig, DriftDetectionConfig
from .strategies import create_drift_strategy, DriftDetectionStrategy
from ..events import EventBus, DataDriftDetected, SchemaChangeDetected

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
            'dataset_name': self.dataset_name,
            'schema_name': self.schema_name,
            'baseline_run_id': self.baseline_run_id,
            'current_run_id': self.current_run_id,
            'baseline_timestamp': self.baseline_timestamp.isoformat(),
            'current_timestamp': self.current_timestamp.isoformat(),
            'column_drifts': [
                {
                    'column_name': d.column_name,
                    'metric_name': d.metric_name,
                    'baseline_value': d.baseline_value,
                    'current_value': d.current_value,
                    'change_percent': d.change_percent,
                    'change_absolute': d.change_absolute,
                    'drift_detected': d.drift_detected,
                    'drift_severity': d.drift_severity
                }
                for d in self.column_drifts
            ],
            'schema_changes': self.schema_changes,
            'summary': self.summary
        }


class DriftDetector:
    """Detects drift between profiling runs."""
    
    # Metrics that should be compared for drift
    NUMERIC_DRIFT_METRICS = ['count', 'null_percent', 'distinct_percent', 'mean', 'stddev', 'min', 'max']
    
    def __init__(
        self,
        storage_config: StorageConfig,
        drift_config: Optional[DriftDetectionConfig] = None,
        event_bus: Optional[EventBus] = None,
        metrics_enabled: bool = False
    ):
        """
        Initialize drift detector.
        
        Args:
            storage_config: Storage configuration
            drift_config: Drift detection configuration (uses defaults if not provided)
            event_bus: Optional event bus for emitting drift events
            metrics_enabled: Whether Prometheus metrics are enabled
        """
        self.storage_config = storage_config
        self.drift_config = drift_config or DriftDetectionConfig()
        self.engine = self._setup_connection()
        self.event_bus = event_bus
        self.metrics_enabled = metrics_enabled
        
        # Create drift detection strategy based on config
        self.strategy = self._create_strategy()
    
    def _create_strategy(self) -> DriftDetectionStrategy:
        """Create drift detection strategy from configuration."""
        strategy_name = self.drift_config.strategy
        
        # Get parameters for the selected strategy
        if strategy_name == "absolute_threshold":
            params = self.drift_config.absolute_threshold
        elif strategy_name == "standard_deviation":
            params = self.drift_config.standard_deviation
        elif strategy_name == "ml_based":
            params = self.drift_config.ml_based
        else:
            logger.warning(f"Unknown strategy '{strategy_name}', using absolute_threshold")
            strategy_name = "absolute_threshold"
            params = self.drift_config.absolute_threshold
        
        logger.info(f"Using drift detection strategy: {strategy_name} with params: {params}")
        return create_drift_strategy(strategy_name, **params)
    
    def _setup_connection(self):
        """Setup database connection."""
        from ..connectors import (
            PostgresConnector, SnowflakeConnector, SQLiteConnector,
            MySQLConnector, BigQueryConnector, RedshiftConnector
        )
        
        if self.storage_config.connection.type == "postgres":
            connector = PostgresConnector(self.storage_config.connection)
        elif self.storage_config.connection.type == "snowflake":
            connector = SnowflakeConnector(self.storage_config.connection)
        elif self.storage_config.connection.type == "sqlite":
            connector = SQLiteConnector(self.storage_config.connection)
        elif self.storage_config.connection.type == "mysql":
            connector = MySQLConnector(self.storage_config.connection)
        elif self.storage_config.connection.type == "bigquery":
            connector = BigQueryConnector(self.storage_config.connection)
        elif self.storage_config.connection.type == "redshift":
            connector = RedshiftConnector(self.storage_config.connection)
        else:
            raise ValueError(f"Unsupported storage type: {self.storage_config.connection.type}")
        
        return connector.engine
    
    def detect_drift(
        self,
        dataset_name: str,
        baseline_run_id: Optional[str] = None,
        current_run_id: Optional[str] = None,
        schema_name: Optional[str] = None
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
        from ..logging import log_event
        import time
        
        start_time = time.time()
        log_event(
            logger, "drift_detection_started",
            f"Starting drift detection for dataset: {dataset_name}",
            metadata={
                "dataset_name": dataset_name,
                "schema_name": schema_name,
                "baseline_run_id": baseline_run_id,
                "current_run_id": current_run_id
            }
        )
        
        # Get run IDs if not provided
        if current_run_id is None or baseline_run_id is None:
            run_ids = self._get_latest_runs(dataset_name, schema_name, limit=2)
            if len(run_ids) < 2:
                error_msg = f"Need at least 2 runs for drift detection, found {len(run_ids)}"
                log_event(
                    logger, "drift_detection_failed",
                    error_msg,
                    level="error",
                    metadata={"dataset_name": dataset_name, "run_count": len(run_ids)}
                )
                raise ValueError(error_msg)
            
            if current_run_id is None:
                current_run_id = run_ids[0]
            if baseline_run_id is None:
                baseline_run_id = run_ids[1]
            
            log_event(
                logger, "drift_runs_selected",
                f"Using runs: baseline={baseline_run_id}, current={current_run_id}",
                metadata={"baseline_run_id": baseline_run_id, "current_run_id": current_run_id}
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
            baseline_timestamp=baseline_meta['profiled_at'],
            current_timestamp=current_meta['profiled_at']
        )
        
        # Detect schema changes
        log_event(logger, "schema_change_detection_started", "Detecting schema changes")
        report.schema_changes = self._detect_schema_changes(baseline_run_id, current_run_id)
        
        # Detect metric drifts
        log_event(logger, "metric_drift_detection_started", "Detecting metric drifts")
        report.column_drifts = self._detect_metric_drifts(
            baseline_run_id, 
            current_run_id,
            table_name=dataset_name
        )
        
        # Generate summary
        report.summary = self._generate_summary(report)
        
        duration = time.time() - start_time
        
        # Get warehouse type for metrics
        warehouse = self.storage_config.connection.type
        
        # Record metrics: drift detection completed
        if self.metrics_enabled:
            from ..metrics import record_drift_detection_completed
            record_drift_detection_completed(warehouse, dataset_name, duration)
        
        log_event(
            logger, "drift_detection_completed",
            f"Drift detection completed in {duration:.2f}s",
            metadata={
                "dataset_name": dataset_name,
                "duration_seconds": duration,
                "total_drifts": report.summary.get("total_drifts", 0),
                "schema_changes": len(report.schema_changes),
                "has_critical_drift": report.summary.get("has_critical_drift", False)
            }
        )
        
        # Emit events for detected drift
        if self.event_bus and report.summary.get("total_drifts", 0) > 0:
            for drift in report.column_drifts:
                if drift.drift_detected:
                    # Record metrics: drift event
                    if self.metrics_enabled:
                        from ..metrics import record_drift_event
                        record_drift_event(warehouse, dataset_name, drift.metric_name, drift.drift_severity)
                    
                    self.event_bus.emit(DataDriftDetected(
                        event_type="DataDriftDetected",
                        timestamp=datetime.utcnow(),
                        table=dataset_name,
                        column=drift.column_name,
                        metric=drift.metric_name,
                        baseline_value=drift.baseline_value,
                        current_value=drift.current_value,
                        change_percent=drift.change_percent,
                        drift_severity=drift.drift_severity,
                        metadata={}
                    ))
        
        # Emit events for schema changes
        if self.event_bus and report.schema_changes:
            # Record metrics: schema changes
            if self.metrics_enabled:
                from ..metrics import record_schema_change
                for change in report.schema_changes:
                    # Parse change type from string (e.g., "Column added: foo" -> "column_added")
                    change_type = "column_added" if "added" in change.lower() else \
                                  "column_removed" if "removed" in change.lower() else \
                                  "type_changed" if "changed" in change.lower() else "unknown"
                    record_schema_change(warehouse, dataset_name, change_type)
            
            self.event_bus.emit(SchemaChangeDetected(
                event_type="SchemaChangeDetected",
                timestamp=datetime.utcnow(),
                table=dataset_name,
                changes=report.schema_changes,
                metadata={}
            ))
        
        return report
    
    def _get_latest_runs(
        self,
        dataset_name: str,
        schema_name: Optional[str],
        limit: int = 2
    ) -> List[str]:
        """Get latest run IDs for a dataset."""
        query = text(f"""
            SELECT run_id FROM {self.storage_config.runs_table}
            WHERE dataset_name = :dataset_name
            {"AND schema_name = :schema_name" if schema_name else ""}
            ORDER BY profiled_at DESC
            LIMIT :limit
        """)
        
        params = {'dataset_name': dataset_name, 'limit': limit}
        if schema_name:
            params['schema_name'] = schema_name
        
        with self.engine.connect() as conn:
            result = conn.execute(query, params)
            return [row[0] for row in result]
    
    def _get_run_metadata(self, run_id: str) -> Dict[str, Any]:
        """Get metadata for a run."""
        query = text(f"""
            SELECT * FROM {self.storage_config.runs_table}
            WHERE run_id = :run_id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {'run_id': run_id}).fetchone()
            if not result:
                raise ValueError(f"Run not found: {run_id}")
            
            return {
                'run_id': result.run_id,
                'dataset_name': result.dataset_name,
                'schema_name': result.schema_name,
                'profiled_at': result.profiled_at,
                'row_count': result.row_count,
                'column_count': result.column_count
            }
    
    def _detect_schema_changes(self, baseline_run_id: str, current_run_id: str) -> List[str]:
        """Detect schema changes between runs."""
        changes = []
        
        # Get column lists
        baseline_columns = self._get_columns(baseline_run_id)
        current_columns = self._get_columns(current_run_id)
        
        # Get table name from metadata
        baseline_meta = self._get_run_metadata(baseline_run_id)
        table_name = baseline_meta.get('dataset_name', 'unknown')
        
        # Detect added columns
        added = current_columns - baseline_columns
        for col in added:
            changes.append(f"Column added: {col}")
            # Emit schema change event
            if self.event_bus:
                self.event_bus.emit(SchemaChangeDetected(
                    event_type="SchemaChangeDetected",
                    timestamp=datetime.utcnow(),
                    table=table_name,
                    change_type="column_added",
                    column=col,
                    metadata={}
                ))
        
        # Detect removed columns
        removed = baseline_columns - current_columns
        for col in removed:
            changes.append(f"Column removed: {col}")
            # Emit schema change event
            if self.event_bus:
                self.event_bus.emit(SchemaChangeDetected(
                    event_type="SchemaChangeDetected",
                    timestamp=datetime.utcnow(),
                    table=table_name,
                    change_type="column_removed",
                    column=col,
                    metadata={}
                ))
        
        return changes
    
    def _get_columns(self, run_id: str) -> set:
        """Get set of columns for a run."""
        query = text(f"""
            SELECT DISTINCT column_name FROM {self.storage_config.results_table}
            WHERE run_id = :run_id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {'run_id': run_id})
            return {row[0] for row in result}
    
    def _detect_metric_drifts(
        self, 
        baseline_run_id: str, 
        current_run_id: str,
        table_name: Optional[str] = None
    ) -> List[ColumnDrift]:
        """Detect metric drifts between runs."""
        drifts = []
        
        # Get metrics for both runs
        baseline_metrics = self._get_metrics(baseline_run_id)
        current_metrics = self._get_metrics(current_run_id)
        
        # Compare metrics
        for (column, metric), baseline_value in baseline_metrics.items():
            if (column, metric) not in current_metrics:
                continue
            
            current_value = current_metrics[(column, metric)]
            
            # Only compare numeric drift metrics
            if metric not in self.NUMERIC_DRIFT_METRICS:
                continue
            
            # Calculate drift
            drift = self._calculate_drift(column, metric, baseline_value, current_value)
            if drift:
                drifts.append(drift)
                
                # Emit drift event if detected and event bus is available
                if drift.drift_detected and self.event_bus and table_name:
                    self.event_bus.emit(DataDriftDetected(
                        event_type="DataDriftDetected",
                        timestamp=datetime.utcnow(),
                        table=table_name,
                        column=column,
                        metric=metric,
                        baseline_value=baseline_value,
                        current_value=current_value,
                        change_percent=drift.change_percent,
                        drift_severity=drift.drift_severity,
                        metadata={}
                    ))
        
        return drifts
    
    def _get_metrics(self, run_id: str) -> Dict[tuple, Any]:
        """Get all metrics for a run as {(column, metric): value}."""
        query = text(f"""
            SELECT column_name, metric_name, metric_value
            FROM {self.storage_config.results_table}
            WHERE run_id = :run_id
        """)
        
        metrics = {}
        with self.engine.connect() as conn:
            result = conn.execute(query, {'run_id': run_id})
            for row in result:
                key = (row.column_name, row.metric_name)
                # Try to convert to float
                try:
                    metrics[key] = float(row.metric_value) if row.metric_value else None
                except (ValueError, TypeError):
                    metrics[key] = row.metric_value
        
        return metrics
    
    def _calculate_drift(
        self,
        column_name: str,
        metric_name: str,
        baseline_value: Any,
        current_value: Any
    ) -> Optional[ColumnDrift]:
        """Calculate drift for a metric using the configured strategy."""
        # Use the configured strategy to calculate drift
        result = self.strategy.calculate_drift(
            baseline_value=baseline_value,
            current_value=current_value,
            metric_name=metric_name,
            column_name=column_name
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
            drift_severity=result.drift_severity
        )
        
        # Emit drift event if drift was detected and event bus is available
        if drift.drift_detected and self.event_bus:
            # Get table name from current context (we'll need to pass this through)
            # For now, we'll extract it from the run metadata
            self.event_bus.emit(DataDriftDetected(
                event_type="DataDriftDetected",
                timestamp=datetime.utcnow(),
                table="unknown",  # Will be set in detect_drift
                column=column_name,
                metric=metric_name,
                baseline_value=baseline_value,
                current_value=current_value,
                change_percent=result.change_percent,
                drift_severity=result.drift_severity,
                metadata={}
            ))
        
        return drift
    
    def _generate_summary(self, report: DriftReport) -> Dict[str, Any]:
        """Generate summary statistics for drift report."""
        total_drifts = len([d for d in report.column_drifts if d.drift_detected])
        
        drift_by_severity = {
            'high': len([d for d in report.column_drifts if d.drift_severity == 'high']),
            'medium': len([d for d in report.column_drifts if d.drift_severity == 'medium']),
            'low': len([d for d in report.column_drifts if d.drift_severity == 'low'])
        }
        
        return {
            'total_drifts': total_drifts,
            'schema_changes': len(report.schema_changes),
            'drift_by_severity': drift_by_severity,
            'has_critical_drift': drift_by_severity['high'] > 0
        }

