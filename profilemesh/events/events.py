"""
Event models for ProfileMesh.

These events are emitted during profiling and drift detection operations
and can be handled by registered alert hooks.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class BaseEvent:
    """Base class for all ProfileMesh events."""
    
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
    
    def __post_init__(self):
        """Populate metadata from fields."""
        if not self.metadata:
            self.metadata = {}
        self.metadata.update({
            "table": self.table,
            "column": self.column,
            "metric": self.metric,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
            "change_percent": self.change_percent,
            "drift_severity": self.drift_severity,
        })


@dataclass
class SchemaChangeDetected(BaseEvent):
    """Event emitted when a schema change is detected."""
    
    table: str
    change_type: str  # 'column_added', 'column_removed', 'type_changed'
    column: Optional[str] = None
    old_type: Optional[str] = None
    new_type: Optional[str] = None
    
    def __post_init__(self):
        """Populate metadata from fields."""
        if not self.metadata:
            self.metadata = {}
        self.metadata.update({
            "table": self.table,
            "change_type": self.change_type,
            "column": self.column,
            "old_type": self.old_type,
            "new_type": self.new_type,
        })


@dataclass
class ProfilingStarted(BaseEvent):
    """Event emitted when profiling begins."""
    
    table: str
    run_id: str
    
    def __post_init__(self):
        """Populate metadata from fields."""
        if not self.metadata:
            self.metadata = {}
        self.metadata.update({
            "table": self.table,
            "run_id": self.run_id,
        })


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
        self.metadata.update({
            "table": self.table,
            "run_id": self.run_id,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "duration_seconds": self.duration_seconds,
        })


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
        self.metadata.update({
            "table": self.table,
            "run_id": self.run_id,
            "error": self.error,
        })

