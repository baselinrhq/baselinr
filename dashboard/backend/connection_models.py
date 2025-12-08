"""
Pydantic models for connection management API requests and responses.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any


class SavedConnection(BaseModel):
    """Saved connection with metadata."""
    id: str = Field(..., description="Connection identifier")
    name: str = Field(..., description="Connection name")
    connection: Dict[str, Any] = Field(..., description="Connection configuration")
    created_at: datetime = Field(..., description="When the connection was created")
    updated_at: Optional[datetime] = Field(None, description="When the connection was last updated")
    last_tested: Optional[datetime] = Field(None, description="When the connection was last tested")
    is_active: Optional[bool] = Field(True, description="Whether the connection is active")


class ConnectionsListResponse(BaseModel):
    """Response model for GET /api/config/connections."""
    connections: List[SavedConnection] = Field(default_factory=list, description="List of saved connections")
    total: int = Field(..., description="Total number of connections")


class SaveConnectionRequest(BaseModel):
    """Request body for POST/PUT /api/config/connections."""
    name: str = Field(..., description="Connection name")
    connection: Dict[str, Any] = Field(..., description="Connection configuration")


class SaveConnectionResponse(BaseModel):
    """Response model for POST/PUT /api/config/connections."""
    id: str = Field(..., description="Connection identifier")
    connection: SavedConnection = Field(..., description="Saved connection details")


