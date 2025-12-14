"""
Event models for Baselinr.

These events are emitted during profiling and drift detection operations
and can be handled by registered alert hooks.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class BaseEvent:
    """Base class for all Baselinr events."""

    event_type: str
    timestamp: datetime
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class DataDriftDetected(BaseEvent):
    """Event emitted when data drift is detected."""

    table: str
    column: str
    metric: str
    baseline_value: float
    current_value: float
    change_percent: Optional[float]
    drift_severity: str
    explanation: Optional[str] = None  # Human-readable explanation

    def __post_init__(self):
        """Populate metadata from fields."""
        if not self.metadata:
            self.metadata = {}
        self.metadata.update(
            {
                "table": self.table,
                "column": self.column,
                "metric": self.metric,
                "baseline_value": self.baseline_value,
                "current_value": self.current_value,
                "change_percent": self.change_percent,
                "drift_severity": self.drift_severity,
                "explanation": self.explanation,
            }
        )


@dataclass
class SchemaChangeDetected(BaseEvent):
    """Event emitted when a schema change is detected."""

    table: str
    # Change types: 'column_added', 'column_removed', 'column_renamed',
    # 'type_changed', 'partition_changed'
    change_type: str
    column: Optional[str] = None
    old_column_name: Optional[str] = None  # For renames
    old_type: Optional[str] = None
    new_type: Optional[str] = None
    partition_info: Optional[Dict[str, Any]] = None  # For partition changes
    change_severity: str = "medium"  # 'low', 'medium', 'high', 'breaking'
    explanation: Optional[str] = None  # Human-readable explanation

    def __post_init__(self):
        """Populate metadata from fields."""
        if not self.metadata:
            self.metadata = {}
        self.metadata.update(
            {
                "table": self.table,
                "change_type": self.change_type,
                "column": self.column,
                "old_column_name": self.old_column_name,
                "old_type": self.old_type,
                "new_type": self.new_type,
                "partition_info": self.partition_info,
                "change_severity": self.change_severity,
                "explanation": self.explanation,
            }
        )


@dataclass
class ProfilingStarted(BaseEvent):
    """Event emitted when profiling begins."""

    table: str
    run_id: str

    def __post_init__(self):
        """Populate metadata from fields."""
        if not self.metadata:
            self.metadata = {}
        self.metadata.update(
            {
                "table": self.table,
                "run_id": self.run_id,
            }
        )


@dataclass
class ProfilingCompleted(BaseEvent):
    """Event emitted when profiling completes successfully."""

    table: str
    run_id: str
    row_count: int
    column_count: int
    duration_seconds: float

    def __post_init__(self):
        """Populate metadata from fields."""
        if not self.metadata:
            self.metadata = {}
        self.metadata.update(
            {
                "table": self.table,
                "run_id": self.run_id,
                "row_count": self.row_count,
                "column_count": self.column_count,
                "duration_seconds": self.duration_seconds,
            }
        )


@dataclass
class ProfilingFailed(BaseEvent):
    """Event emitted when profiling fails."""

    table: str
    run_id: str
    error: str

    def __post_init__(self):
        """Populate metadata from fields."""
        if not self.metadata:
            self.metadata = {}
        self.metadata.update(
            {
                "table": self.table,
                "run_id": self.run_id,
                "error": self.error,
            }
        )


@dataclass
class ProfilingSkipped(BaseEvent):
    """Event emitted when a table is skipped or deferred."""

    table: str
    schema: Optional[str]
    reason: str
    action: str
    snapshot_id: Optional[str] = None

    def __post_init__(self):
        if not self.metadata:
            self.metadata = {}
        self.metadata.update(
            {
                "table": self.table,
                "schema": self.schema,
                "reason": self.reason,
                "action": self.action,
                "snapshot_id": self.snapshot_id,
            }
        )

    @classmethod
    def create(
        cls,
        table: str,
        schema: Optional[str],
        reason: str,
        action: str,
        snapshot_id: Optional[str] = None,
    ) -> "ProfilingSkipped":
        return cls(
            event_type="ProfilingSkipped",
            timestamp=datetime.utcnow(),
            table=table,
            schema=schema,
            reason=reason,
            action=action,
            snapshot_id=snapshot_id,
            metadata={},
        )


@dataclass
class RetryAttempt(BaseEvent):
    """Event emitted when a retry is attempted."""

    function: str
    attempt: int
    error: str
    error_type: str

    def __post_init__(self):
        """Populate metadata from fields."""
        if not self.metadata:
            self.metadata = {}
        self.metadata.update(
            {
                "function": self.function,
                "attempt": self.attempt,
                "error": self.error,
                "error_type": self.error_type,
            }
        )


@dataclass
class RetryExhausted(BaseEvent):
    """Event emitted when all retry attempts are exhausted."""

    function: str
    total_attempts: int
    error: str
    error_type: str

    def __post_init__(self):
        """Populate metadata from fields."""
        if not self.metadata:
            self.metadata = {}
        self.metadata.update(
            {
                "function": self.function,
                "total_attempts": self.total_attempts,
                "error": self.error,
                "error_type": self.error_type,
            }
        )


@dataclass
class AnomalyDetected(BaseEvent):
    """Event emitted when an anomaly is detected."""

    table: str
    column: str
    metric: str
    anomaly_type: str
    expected_value: Optional[float]
    actual_value: float
    severity: str  # 'low', 'medium', 'high'
    detection_method: str
    explanation: Optional[str] = None  # Human-readable explanation

    def __post_init__(self):
        """Populate metadata from fields."""
        if not self.metadata:
            self.metadata = {}
        self.metadata.update(
            {
                "table": self.table,
                "column": self.column,
                "metric": self.metric,
                "anomaly_type": self.anomaly_type,
                "expected_value": self.expected_value,
                "actual_value": self.actual_value,
                "severity": self.severity,
                "detection_method": self.detection_method,
                "explanation": self.explanation,
            }
        )


@dataclass
class ValidationFailed(BaseEvent):
    """Event emitted when a validation rule fails."""

    table: str
    column: Optional[str]
    rule_type: str
    rule_config: Dict[str, Any]
    failure_reason: str
    sample_failures: List[Dict[str, Any]]  # Sample rows that failed
    severity: str
    total_failures: int
    total_rows: int
    failure_rate: float

    def __post_init__(self):
        """Populate metadata from fields."""
        if not self.metadata:
            self.metadata = {}
        self.metadata.update(
            {
                "table": self.table,
                "column": self.column,
                "rule_type": self.rule_type,
                "rule_config": self.rule_config,
                "failure_reason": self.failure_reason,
                "sample_failures": self.sample_failures,
                "severity": self.severity,
                "total_failures": self.total_failures,
                "total_rows": self.total_rows,
                "failure_rate": self.failure_rate,
            }
        )


@dataclass
class QualityScoreDegraded(BaseEvent):
    """Event emitted when a quality score degrades significantly."""

    table: str
    schema: Optional[str]
    current_score: float
    previous_score: float
    score_change: float
    threshold_type: str  # 'warning' or 'critical'
    explanation: Optional[str] = None  # Human-readable explanation

    def __post_init__(self):
        """Populate metadata from fields."""
        if not self.metadata:
            self.metadata = {}
        self.metadata.update(
            {
                "table": self.table,
                "schema": self.schema,
                "current_score": self.current_score,
                "previous_score": self.previous_score,
                "score_change": self.score_change,
                "threshold_type": self.threshold_type,
                "explanation": self.explanation,
            }
        )


@dataclass
class QualityScoreThresholdBreached(BaseEvent):
    """Event emitted when a quality score crosses a threshold (warning or critical)."""

    table: str
    schema: Optional[str]
    current_score: float
    threshold_type: str  # 'warning' or 'critical'
    threshold_value: float
    previous_status: Optional[str] = None  # Previous status before breach
    explanation: Optional[str] = None  # Human-readable explanation

    def __post_init__(self):
        """Populate metadata from fields."""
        if not self.metadata:
            self.metadata = {}
        self.metadata.update(
            {
                "table": self.table,
                "schema": self.schema,
                "current_score": self.current_score,
                "threshold_type": self.threshold_type,
                "threshold_value": self.threshold_value,
                "previous_status": self.previous_status,
                "explanation": self.explanation,
            }
        )
