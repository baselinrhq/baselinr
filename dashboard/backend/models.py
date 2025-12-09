"""
Pydantic models for Baselinr Dashboard API responses.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any


class RunHistoryResponse(BaseModel):
    """Response model for run history list."""
    run_id: str
    dataset_name: str
    schema_name: Optional[str]
    warehouse_type: str
    profiled_at: datetime
    status: str  # success, failed, drift_detected
    row_count: Optional[int]
    column_count: Optional[int]
    duration_seconds: Optional[float] = None
    has_drift: bool = False


class ColumnMetrics(BaseModel):
    """Column-level metrics."""
    column_name: str
    column_type: str
    null_count: Optional[int]
    null_percent: Optional[float]
    distinct_count: Optional[int]
    distinct_percent: Optional[float]
    min_value: Optional[Any]
    max_value: Optional[Any]
    mean: Optional[float]
    stddev: Optional[float]
    histogram: Optional[Any]  # Can be List[Dict] or Dict, stored as JSON string


class ProfilingResultResponse(BaseModel):
    """Detailed profiling result for a single run."""
    run_id: str
    dataset_name: str
    schema_name: Optional[str]
    warehouse_type: str
    profiled_at: datetime
    environment: str
    row_count: int
    column_count: int
    columns: List[ColumnMetrics]
    metadata: Dict[str, Any] = {}


class DriftAlertResponse(BaseModel):
    """Drift detection alert."""
    event_id: str
    run_id: str
    table_name: str
    column_name: Optional[str]
    metric_name: str
    baseline_value: Optional[float]
    current_value: Optional[float]
    change_percent: Optional[float]
    severity: str  # low, medium, high
    timestamp: datetime
    warehouse_type: str


class TableMetricsTrend(BaseModel):
    """Historical trend data for a table metric."""
    timestamp: datetime
    value: float


class TableMetricsResponse(BaseModel):
    """Detailed metrics for a specific table."""
    table_name: str
    schema_name: Optional[str]
    warehouse_type: str
    last_profiled: datetime
    row_count: int
    column_count: int
    total_runs: int
    drift_count: int
    row_count_trend: List[TableMetricsTrend]
    null_percent_trend: List[TableMetricsTrend]
    columns: List[ColumnMetrics]


class KPI(BaseModel):
    """Key Performance Indicator."""
    name: str
    value: Any
    change_percent: Optional[float] = None
    trend: str  # up, down, stable


class MetricsDashboardResponse(BaseModel):
    """Aggregate metrics for dashboard overview."""
    total_runs: int
    total_tables: int
    total_drift_events: int
    avg_row_count: float
    kpis: List[KPI]
    run_trend: List[TableMetricsTrend]
    drift_trend: List[TableMetricsTrend]
    warehouse_breakdown: Dict[str, int]
    recent_runs: List[RunHistoryResponse]
    recent_drift: List[DriftAlertResponse]
    # Enhanced metrics
    validation_pass_rate: Optional[float] = None
    total_validation_rules: int = 0
    failed_validation_rules: int = 0
    active_alerts: int = 0
    data_freshness_hours: Optional[float] = None
    stale_tables_count: int = 0
    validation_trend: List[TableMetricsTrend] = Field(default_factory=list)

