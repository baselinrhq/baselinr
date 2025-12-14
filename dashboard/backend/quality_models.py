"""
Pydantic models for quality scores API requests and responses.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict


class ScoreComponentResponse(BaseModel):
    """Component breakdown model."""
    completeness: float = Field(..., description="Completeness score (0-100)")
    validity: float = Field(..., description="Validity score (0-100)")
    consistency: float = Field(..., description="Consistency score (0-100)")
    freshness: float = Field(..., description="Freshness score (0-100)")
    uniqueness: float = Field(..., description="Uniqueness score (0-100)")
    accuracy: float = Field(..., description="Accuracy score (0-100)")


class IssuesResponse(BaseModel):
    """Issues summary model."""
    total: int = Field(..., description="Total number of issues")
    critical: int = Field(..., description="Number of critical issues")
    warnings: int = Field(..., description="Number of warnings")


class QualityScoreResponse(BaseModel):
    """Main response model for a single table score."""
    table_name: str = Field(..., description="Table name")
    schema_name: Optional[str] = Field(None, description="Schema name")
    overall_score: float = Field(..., description="Overall quality score (0-100)")
    status: str = Field(..., description="Status: healthy, warning, or critical")
    trend: Optional[str] = Field(None, description="Trend: improving, degrading, or stable")
    trend_percentage: Optional[float] = Field(None, description="Percentage change from previous score")
    components: ScoreComponentResponse = Field(..., description="Component scores breakdown")
    issues: IssuesResponse = Field(..., description="Issues summary")
    calculated_at: datetime = Field(..., description="When the score was calculated")
    run_id: Optional[str] = Field(None, description="Associated run ID")


class QualityScoresListResponse(BaseModel):
    """Response model for list of all table scores."""
    scores: List[QualityScoreResponse] = Field(default_factory=list, description="List of quality scores")
    total: int = Field(..., description="Total number of scores")


class ScoreHistoryResponse(BaseModel):
    """Historical score data response."""
    scores: List[QualityScoreResponse] = Field(default_factory=list, description="Historical scores")
    total: int = Field(..., description="Total number of historical scores")


class SchemaScoreResponse(BaseModel):
    """Schema-level aggregated score response."""
    schema_name: str = Field(..., description="Schema name")
    overall_score: float = Field(..., description="Aggregated overall score (0-100)")
    status: str = Field(..., description="Status: healthy, warning, or critical")
    table_count: int = Field(..., description="Number of tables in schema")
    healthy_count: int = Field(..., description="Number of healthy tables")
    warning_count: int = Field(..., description="Number of tables with warning status")
    critical_count: int = Field(..., description="Number of critical tables")
    tables: List[QualityScoreResponse] = Field(default_factory=list, description="Individual table scores")


class SystemScoreResponse(BaseModel):
    """System-level aggregated score response."""
    overall_score: float = Field(..., description="System-wide overall score (0-100)")
    status: str = Field(..., description="Status: healthy, warning, or critical")
    total_tables: int = Field(..., description="Total number of tables")
    healthy_count: int = Field(..., description="Number of healthy tables")
    warning_count: int = Field(..., description="Number of tables with warning status")
    critical_count: int = Field(..., description="Number of critical tables")


class TrendAnalysisResponse(BaseModel):
    """Trend analysis response."""
    direction: str = Field(..., description="Trend direction: improving, degrading, or stable")
    rate_of_change: float = Field(..., description="Percentage change per period")
    confidence: float = Field(..., description="Confidence level (0-1)")
    periods_analyzed: int = Field(..., description="Number of periods analyzed")
    overall_change: float = Field(..., description="Total percentage change")


class ColumnScoreResponse(BaseModel):
    """Column-level quality score response."""
    table_name: str = Field(..., description="Table name")
    schema_name: Optional[str] = Field(None, description="Schema name")
    column_name: str = Field(..., description="Column name")
    overall_score: float = Field(..., description="Overall quality score (0-100)")
    status: str = Field(..., description="Status: healthy, warning, or critical")
    components: ScoreComponentResponse = Field(..., description="Component scores breakdown")
    calculated_at: datetime = Field(..., description="When the score was calculated")
    run_id: Optional[str] = Field(None, description="Associated run ID")
    period_start: datetime = Field(..., description="Period start time")
    period_end: datetime = Field(..., description="Period end time")


class ColumnScoresListResponse(BaseModel):
    """Response model for list of column scores."""
    scores: List[ColumnScoreResponse] = Field(default_factory=list, description="List of column scores")
    total: int = Field(..., description="Total number of column scores")


class ScoreComparisonResponse(BaseModel):
    """Score comparison response."""
    tables: List[QualityScoreResponse] = Field(default_factory=list, description="Compared table scores")
    comparison_metrics: Dict = Field(..., description="Comparison metrics including best/worst performers")
