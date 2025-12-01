"""
Pydantic models for lineage API endpoints.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class LineageNodeResponse(BaseModel):
    """Single node in lineage graph."""
    id: str
    type: str  # 'table' or 'column'
    label: str
    schema: Optional[str] = None
    table: Optional[str] = None
    column: Optional[str] = None
    database: Optional[str] = None
    metadata: Dict[str, Any] = {}
    metrics: Optional[Dict[str, float]] = None


class LineageEdgeResponse(BaseModel):
    """Single edge in lineage graph."""
    source: str
    target: str
    relationship_type: str
    confidence: float = 1.0
    transformation: Optional[str] = None
    provider: str = "unknown"
    metadata: Dict[str, Any] = {}


class LineageGraphResponse(BaseModel):
    """Complete lineage graph response."""
    nodes: List[LineageNodeResponse]
    edges: List[LineageEdgeResponse]
    root_id: Optional[str] = None
    direction: str = "both"


class NodeDetailsResponse(BaseModel):
    """Detailed information about a single node."""
    id: str
    type: str
    label: str
    schema: Optional[str] = None
    table: Optional[str] = None
    column: Optional[str] = None
    database: Optional[str] = None
    metadata: Dict[str, Any] = {}
    upstream_count: int = 0
    downstream_count: int = 0
    providers: List[str] = []


class TableInfoResponse(BaseModel):
    """Basic table information."""
    schema: str
    table: str
    database: Optional[str] = None


class DriftPathResponse(BaseModel):
    """Drift propagation path response."""
    table: str
    schema: Optional[str] = None
    has_drift: bool = False
    drift_severity: Optional[str] = None
    affected_downstream: List[TableInfoResponse] = []
    lineage_path: LineageGraphResponse
