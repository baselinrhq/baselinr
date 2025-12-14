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


class RunComparisonResponse(BaseModel):
    """Response model for run comparison."""
    runs: List[RunHistoryResponse]
    comparison: Dict[str, Any] = Field(default_factory=dict)  # Metrics differences, common columns, etc.


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
    # Quality scoring metrics
    system_quality_score: Optional[float] = None
    quality_score_status: Optional[str] = None
    quality_trend: Optional[str] = None


class TableListItem(BaseModel):
    """Table list item for tables explorer."""
    table_name: str
    schema_name: Optional[str]
    warehouse_type: str
    last_profiled: Optional[datetime]
    row_count: Optional[int]
    column_count: Optional[int]
    total_runs: int
    drift_count: int
    validation_pass_rate: Optional[float] = None
    has_recent_drift: bool = False
    has_failed_validations: bool = False


class TableListResponse(BaseModel):
    """Response model for table list with pagination."""
    tables: List[TableListItem]
    total: int
    page: int
    page_size: int


class TableOverviewResponse(BaseModel):
    """Enhanced table overview response."""
    table_name: str
    schema_name: Optional[str]
    warehouse_type: str
    last_profiled: datetime
    row_count: int
    column_count: int
    total_runs: int
    drift_count: int
    validation_pass_rate: Optional[float] = None
    total_validation_rules: int = 0
    failed_validation_rules: int = 0
    row_count_trend: List[TableMetricsTrend]
    null_percent_trend: List[TableMetricsTrend]
    columns: List[ColumnMetrics]
    recent_runs: List[RunHistoryResponse] = Field(default_factory=list)


class ValidationResultResponse(BaseModel):
    """Validation result response."""
    id: int
    run_id: str
    table_name: str
    schema_name: Optional[str] = None
    column_name: Optional[str] = None
    rule_type: str
    passed: bool
    failure_reason: Optional[str] = None
    total_rows: Optional[int] = None
    failed_rows: Optional[int] = None
    failure_rate: Optional[float] = None
    severity: Optional[str] = None
    validated_at: datetime


class TableDriftHistoryResponse(BaseModel):
    """Drift history for a specific table."""
    table_name: str
    schema_name: Optional[str]
    drift_events: List[DriftAlertResponse]
    summary: Dict[str, Any] = Field(default_factory=dict)


class TableValidationResultsResponse(BaseModel):
    """Validation results for a specific table."""
    table_name: str
    schema_name: Optional[str]
    validation_results: List[ValidationResultResponse]
    summary: Dict[str, Any] = Field(default_factory=dict)


class TableConfigResponse(BaseModel):
    """Table configuration response."""
    table_name: str
    schema_name: Optional[str]
    config: Dict[str, Any] = Field(default_factory=dict)


class TopAffectedTable(BaseModel):
    """Top affected table in drift summary."""
    table_name: str
    drift_count: int
    severity_breakdown: Dict[str, int] = Field(default_factory=dict)


class DriftSummaryResponse(BaseModel):
    """Drift summary statistics."""
    total_events: int
    by_severity: Dict[str, int] = Field(default_factory=dict)  # {"low": 10, "medium": 5, "high": 2}
    trending: List[TableMetricsTrend] = Field(default_factory=list)  # Events over time
    top_affected_tables: List[TopAffectedTable] = Field(default_factory=list)
    warehouse_breakdown: Dict[str, int] = Field(default_factory=dict)
    recent_activity: List[DriftAlertResponse] = Field(default_factory=list)  # Last 10 events


class DriftDetailsResponse(BaseModel):
    """Detailed drift information for a specific event."""
    event: DriftAlertResponse
    baseline_metrics: Dict[str, Any] = Field(default_factory=dict)  # Full baseline snapshot
    current_metrics: Dict[str, Any] = Field(default_factory=dict)  # Full current snapshot
    statistical_tests: Optional[List[Dict[str, Any]]] = None  # Test results if available
    historical_values: List[Dict[str, Any]] = Field(default_factory=dict)  # Previous values over time
    related_events: List[DriftAlertResponse] = Field(default_factory=list)  # Other drift events for same table/column


class DriftImpactResponse(BaseModel):
    """Drift impact analysis."""
    event_id: str
    affected_tables: List[str] = Field(default_factory=list)  # Downstream tables
    affected_metrics: int = 0
    impact_score: float = 0.0  # 0-1 scale
    recommendations: List[str] = Field(default_factory=list)


class ValidationSummaryResponse(BaseModel):
    """Validation summary statistics."""
    total_validations: int
    passed_count: int
    failed_count: int
    pass_rate: float
    by_rule_type: Dict[str, int] = Field(default_factory=dict)
    by_severity: Dict[str, int] = Field(default_factory=dict)
    by_table: Dict[str, int] = Field(default_factory=dict)
    trending: List[TableMetricsTrend] = Field(default_factory=list)
    recent_runs: List[Dict[str, Any]] = Field(default_factory=list)


class ValidationResultsListResponse(BaseModel):
    """List of validation results with pagination."""
    results: List[ValidationResultResponse]
    total: int
    page: int
    page_size: int


class ValidationResultDetailsResponse(BaseModel):
    """Detailed validation result with context."""
    result: ValidationResultResponse
    rule_config: Optional[Dict[str, Any]] = None
    run_info: Optional[Dict[str, Any]] = None
    historical_results: List[ValidationResultResponse] = Field(default_factory=list)


class ValidationFailureSamplesResponse(BaseModel):
    """Failure samples for a validation result."""
    result_id: int
    total_failures: int
    sample_failures: List[Dict[str, Any]] = Field(default_factory=list)
    failure_patterns: Optional[Dict[str, Any]] = None