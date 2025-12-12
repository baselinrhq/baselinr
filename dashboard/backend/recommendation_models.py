"""
Pydantic models for recommendation API requests and responses.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any


class RecommendationRequest(BaseModel):
    """Request body for generating recommendations."""
    connection_id: str = Field(..., description="ID of the saved connection to analyze")
    schema: Optional[str] = Field(None, description="Optional schema to limit recommendations to")
    include_columns: bool = Field(False, description="Whether to include column-level recommendations")
    refresh: bool = Field(False, description="Force refresh recommendations")


class ColumnCheckRecommendationResponse(BaseModel):
    """Response model for column check recommendations."""
    column: str
    data_type: str
    confidence: float
    signals: List[str]
    suggested_checks: List[Dict[str, Any]]


class TableRecommendationResponse(BaseModel):
    """Response model for table recommendations."""
    schema: str
    table: str
    database: Optional[str] = None
    confidence: float
    score: float
    reasons: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggested_checks: List[str] = Field(default_factory=list)
    column_recommendations: List[ColumnCheckRecommendationResponse] = Field(default_factory=list)
    low_confidence_columns: List[ColumnCheckRecommendationResponse] = Field(default_factory=list)
    query_count: int = 0
    queries_per_day: float = 0.0
    row_count: Optional[int] = None
    last_query_days_ago: Optional[int] = None
    column_count: int = 0
    lineage_score: float = 0.0
    lineage_context: Optional[Dict[str, Any]] = None


class ExcludedTableResponse(BaseModel):
    """Response model for excluded tables."""
    schema: str
    table: str
    database: Optional[str] = None
    reasons: List[str] = Field(default_factory=list)


class RecommendationReportResponse(BaseModel):
    """Response model for complete recommendation report."""
    generated_at: datetime
    lookback_days: int
    database_type: str
    recommended_tables: List[TableRecommendationResponse] = Field(default_factory=list)
    excluded_tables: List[ExcludedTableResponse] = Field(default_factory=list)
    total_tables_analyzed: int = 0
    total_recommended: int = 0
    total_excluded: int = 0
    confidence_distribution: Dict[str, int] = Field(default_factory=dict)
    total_columns_analyzed: int = 0
    total_column_checks_recommended: int = 0
    column_confidence_distribution: Dict[str, int] = Field(default_factory=dict)
    low_confidence_suggestions: List[Dict[str, Any]] = Field(default_factory=list)


class ColumnRecommendationRequest(BaseModel):
    """Request body for getting column recommendations for a specific table."""
    connection_id: str = Field(..., description="ID of the saved connection")
    table: str = Field(..., description="Table name")
    schema: Optional[str] = Field(None, description="Schema name")
    use_profiling_data: bool = Field(True, description="Use profiling data if available")


class ApplyRecommendationsRequest(BaseModel):
    """Request body for applying recommendations."""
    connection_id: str = Field(..., description="ID of the saved connection")
    selected_tables: List[Dict[str, str]] = Field(..., description="List of selected tables with schema/table")
    column_checks: Optional[Dict[str, List[str]]] = Field(None, description="Map of table.column to selected check types")
    comment: Optional[str] = Field(None, description="Comment for the configuration change")


class AppliedTable(BaseModel):
    """Information about an applied table."""
    schema: str
    table: str
    database: Optional[str] = None
    column_checks_applied: int = 0


class ApplyRecommendationsResponse(BaseModel):
    """Response model for applying recommendations."""
    success: bool
    applied_tables: List[AppliedTable] = Field(default_factory=list)
    total_tables_applied: int = 0
    total_column_checks_applied: int = 0
    message: str


