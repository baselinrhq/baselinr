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

from ..config.schema import StorageConfig

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
    
    # Thresholds for drift detection (percent change)
    THRESHOLDS = {
        'low': 5.0,      # 5% change
        'medium': 15.0,   # 15% change
        'high': 30.0      # 30% change
    }
    
    def __init__(self, storage_config: StorageConfig):
        """
        Initialize drift detector.
        
        Args:
            storage_config: Storage configuration
        """
        self.storage_config = storage_config
        self.engine = self._setup_connection()
    
    def _setup_connection(self):
        """Setup database connection."""
        from ..connectors import PostgresConnector, SnowflakeConnector, SQLiteConnector
        
        if self.storage_config.connection.type == "postgres":
            connector = PostgresConnector(self.storage_config.connection)
        elif self.storage_config.connection.type == "snowflake":
            connector = SnowflakeConnector(self.storage_config.connection)
        elif self.storage_config.connection.type == "sqlite":
            connector = SQLiteConnector(self.storage_config.connection)
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
        # Get run IDs if not provided
        if current_run_id is None or baseline_run_id is None:
            run_ids = self._get_latest_runs(dataset_name, schema_name, limit=2)
            if len(run_ids) < 2:
                raise ValueError(f"Need at least 2 runs for drift detection, found {len(run_ids)}")
            
            if current_run_id is None:
                current_run_id = run_ids[0]
            if baseline_run_id is None:
                baseline_run_id = run_ids[1]
        
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
        report.schema_changes = self._detect_schema_changes(baseline_run_id, current_run_id)
        
        # Detect metric drifts
        report.column_drifts = self._detect_metric_drifts(baseline_run_id, current_run_id)
        
        # Generate summary
        report.summary = self._generate_summary(report)
        
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
        
        # Detect added columns
        added = current_columns - baseline_columns
        for col in added:
            changes.append(f"Column added: {col}")
        
        # Detect removed columns
        removed = baseline_columns - current_columns
        for col in removed:
            changes.append(f"Column removed: {col}")
        
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
    
    def _detect_metric_drifts(self, baseline_run_id: str, current_run_id: str) -> List[ColumnDrift]:
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
        """Calculate drift for a metric."""
        # Skip if either value is None
        if baseline_value is None or current_value is None:
            return None
        
        # Skip if not numeric
        if not isinstance(baseline_value, (int, float)) or not isinstance(current_value, (int, float)):
            return None
        
        # Calculate changes
        change_absolute = current_value - baseline_value
        
        if baseline_value != 0:
            change_percent = (change_absolute / abs(baseline_value)) * 100
        else:
            change_percent = None
        
        # Determine drift severity
        drift_detected = False
        drift_severity = "none"
        
        if change_percent is not None:
            abs_change_percent = abs(change_percent)
            
            if abs_change_percent >= self.THRESHOLDS['high']:
                drift_detected = True
                drift_severity = "high"
            elif abs_change_percent >= self.THRESHOLDS['medium']:
                drift_detected = True
                drift_severity = "medium"
            elif abs_change_percent >= self.THRESHOLDS['low']:
                drift_detected = True
                drift_severity = "low"
        
        return ColumnDrift(
            column_name=column_name,
            metric_name=metric_name,
            baseline_value=baseline_value,
            current_value=current_value,
            change_percent=change_percent,
            change_absolute=change_absolute,
            drift_detected=drift_detected,
            drift_severity=drift_severity
        )
    
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

