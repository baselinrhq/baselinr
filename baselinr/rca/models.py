"""
Data models for Root Cause Analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def parse_fully_qualified_table(table_identifier: str) -> Tuple[Optional[str], Optional[str], str]:
    """
    Parse a fully qualified table identifier.

    Supports formats:
    - database.schema.table
    - schema.table
    - table

    Args:
        table_identifier: Table identifier string

    Returns:
        Tuple of (database_name, schema_name, table_name)
    """
    parts = table_identifier.split(".")
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    elif len(parts) == 2:
        return None, parts[0], parts[1]
    else:
        return None, None, parts[0]


@dataclass
class PipelineRun:
    """Represents a pipeline execution."""

    run_id: str
    pipeline_name: str
    pipeline_type: str  # dbt, airflow, dagster, etc.
    started_at: datetime
    status: str  # success, failed, running
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    input_row_count: Optional[int] = None
    output_row_count: Optional[int] = None
    git_commit_sha: Optional[str] = None
    git_branch: Optional[str] = None
    affected_tables: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "pipeline_name": self.pipeline_name,
            "pipeline_type": self.pipeline_type,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "input_row_count": self.input_row_count,
            "output_row_count": self.output_row_count,
            "git_commit_sha": self.git_commit_sha,
            "git_branch": self.git_branch,
            "affected_tables": self.affected_tables,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class CodeDeployment:
    """Represents a code deployment/change event."""

    deployment_id: str
    deployed_at: datetime
    git_commit_sha: Optional[str] = None
    git_branch: Optional[str] = None
    changed_files: List[str] = field(default_factory=list)
    deployment_type: str = "code"  # code, schema, config
    affected_pipelines: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "deployment_id": self.deployment_id,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
            "git_commit_sha": self.git_commit_sha,
            "git_branch": self.git_branch,
            "changed_files": self.changed_files,
            "deployment_type": self.deployment_type,
            "affected_pipelines": self.affected_pipelines,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class PipelineCause:
    """Probable cause from pipeline run."""

    cause_type: str  # pipeline_failure, pipeline_degradation, data_quality
    cause_id: str  # pipeline run ID
    confidence_score: float
    description: str
    affected_assets: List[str] = field(default_factory=list)
    suggested_action: Optional[str] = None
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cause_type": self.cause_type,
            "cause_id": self.cause_id,
            "confidence_score": self.confidence_score,
            "description": self.description,
            "affected_assets": self.affected_assets,
            "suggested_action": self.suggested_action,
            "evidence": self.evidence,
        }


@dataclass
class CodeChangeCause:
    """Probable cause from code deployment."""

    cause_type: str = "code_change"
    cause_id: str = ""  # deployment ID
    confidence_score: float = 0.0
    description: str = ""
    affected_assets: List[str] = field(default_factory=list)
    suggested_action: Optional[str] = None
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cause_type": self.cause_type,
            "cause_id": self.cause_id,
            "confidence_score": self.confidence_score,
            "description": self.description,
            "affected_assets": self.affected_assets,
            "suggested_action": self.suggested_action,
            "evidence": self.evidence,
        }


@dataclass
class UpstreamAnomalyCause:
    """Probable cause from upstream anomaly."""

    cause_type: str = "upstream_anomaly"
    cause_id: str = ""  # upstream anomaly ID
    upstream_table: str = ""
    upstream_column: Optional[str] = None
    upstream_metric: Optional[str] = None
    confidence_score: float = 0.0
    lineage_distance: int = 0  # hops in lineage graph
    description: str = ""
    affected_assets: List[str] = field(default_factory=list)
    suggested_action: Optional[str] = None
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cause_type": self.cause_type,
            "cause_id": self.cause_id,
            "upstream_table": self.upstream_table,
            "upstream_column": self.upstream_column,
            "upstream_metric": self.upstream_metric,
            "confidence_score": self.confidence_score,
            "lineage_distance": self.lineage_distance,
            "description": self.description,
            "affected_assets": self.affected_assets,
            "suggested_action": self.suggested_action,
            "evidence": self.evidence,
        }


@dataclass
class ImpactAnalysis:
    """Analysis of anomaly impact."""

    upstream_affected: List[str] = field(default_factory=list)
    downstream_affected: List[str] = field(default_factory=list)
    blast_radius_score: float = 0.0  # 0-1 score of impact breadth

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "upstream_affected": self.upstream_affected,
            "downstream_affected": self.downstream_affected,
            "blast_radius_score": self.blast_radius_score,
        }


@dataclass
class RCAResult:
    """Root cause analysis result for an anomaly."""

    anomaly_id: str
    table_name: str
    analyzed_at: datetime
    probable_causes: List[Dict[str, Any]] = field(default_factory=list)
    impact_analysis: Optional[ImpactAnalysis] = None
    database_name: Optional[str] = None
    schema_name: Optional[str] = None
    column_name: Optional[str] = None
    metric_name: Optional[str] = None
    rca_status: str = "analyzed"  # pending, analyzed, dismissed
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "anomaly_id": self.anomaly_id,
            "table_name": self.table_name,
            "database_name": self.database_name,
            "schema_name": self.schema_name,
            "column_name": self.column_name,
            "metric_name": self.metric_name,
            "analyzed_at": self.analyzed_at.isoformat() if self.analyzed_at else None,
            "rca_status": self.rca_status,
            "probable_causes": self.probable_causes,
            "impact_analysis": self.impact_analysis.to_dict() if self.impact_analysis else None,
            "metadata": self.metadata,
        }
