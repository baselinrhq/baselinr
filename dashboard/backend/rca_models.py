"""
Pydantic models for RCA API responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProbableCauseResponse(BaseModel):
    """Model for a probable cause."""

    cause_type: str = Field(..., description="Type of cause (pipeline_failure, code_change, etc.)")
    cause_id: str = Field(..., description="Unique identifier for the cause")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    description: str = Field(..., description="Human-readable description")
    affected_assets: List[str] = Field(default_factory=list, description="List of affected assets")
    suggested_action: Optional[str] = Field(None, description="Suggested remediation action")
    evidence: Dict[str, Any] = Field(
        default_factory=dict, description="Supporting evidence for this cause"
    )


class ImpactAnalysisResponse(BaseModel):
    """Model for impact analysis."""

    upstream_affected: List[str] = Field(default_factory=list)
    downstream_affected: List[str] = Field(default_factory=list)
    blast_radius_score: float = Field(0.0, ge=0.0, le=1.0)


class RCAResultResponse(BaseModel):
    """Model for RCA result."""

    anomaly_id: str
    table_name: str
    schema_name: Optional[str] = None
    column_name: Optional[str] = None
    metric_name: Optional[str] = None
    analyzed_at: datetime
    rca_status: str = Field(..., description="Status: analyzed, pending, dismissed")
    probable_causes: List[ProbableCauseResponse]
    impact_analysis: Optional[ImpactAnalysisResponse] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RCAListResponse(BaseModel):
    """Model for list of recent RCA results."""

    anomaly_id: str
    table_name: str
    schema_name: Optional[str] = None
    column_name: Optional[str] = None
    metric_name: Optional[str] = None
    analyzed_at: str
    rca_status: str
    num_causes: int
    top_cause: Optional[Dict[str, Any]] = None


class RCAStatisticsResponse(BaseModel):
    """Model for RCA statistics."""

    total_analyses: int
    analyzed: int
    dismissed: int
    pending: int
    avg_causes_per_anomaly: float


class PipelineRunResponse(BaseModel):
    """Model for pipeline run."""

    run_id: str
    pipeline_name: str
    pipeline_type: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    status: str
    input_row_count: Optional[int] = None
    output_row_count: Optional[int] = None
    git_commit_sha: Optional[str] = None
    git_branch: Optional[str] = None
    affected_tables: List[str] = Field(default_factory=list)


class CodeDeploymentResponse(BaseModel):
    """Model for code deployment."""

    deployment_id: str
    deployed_at: datetime
    git_commit_sha: Optional[str] = None
    git_branch: Optional[str] = None
    changed_files: List[str] = Field(default_factory=list)
    deployment_type: str
    affected_pipelines: List[str] = Field(default_factory=list)


class EventTimelineResponse(BaseModel):
    """Model for events timeline."""

    timestamp: datetime
    event_type: str  # anomaly, pipeline_run, code_deployment
    event_data: Dict[str, Any]
    relevance_score: float = Field(ge=0.0, le=1.0)


class AnalyzeRequestBody(BaseModel):
    """Model for analyze request."""

    anomaly_id: str
    table_name: str
    anomaly_timestamp: datetime
    schema_name: Optional[str] = None
    column_name: Optional[str] = None
    metric_name: Optional[str] = None
    anomaly_type: Optional[str] = None
