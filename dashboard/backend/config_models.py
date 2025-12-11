"""
Pydantic models for configuration API requests and responses.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any


class ConfigResponse(BaseModel):
    """Response model for GET /api/config."""
    config: Dict[str, Any] = Field(..., description="Baselinr configuration object")


class SaveConfigRequest(BaseModel):
    """Request body for POST /api/config."""
    config: Dict[str, Any] = Field(..., description="Baselinr configuration to save")


class ConfigValidationRequest(BaseModel):
    """Request body for POST /api/config/validate."""
    config: Dict[str, Any] = Field(..., description="Configuration to validate")


class ConfigValidationResponse(BaseModel):
    """Response model for POST /api/config/validate."""
    valid: bool = Field(..., description="Whether the configuration is valid")
    errors: List[str] = Field(default_factory=list, description="List of validation errors")


class ConnectionTestRequest(BaseModel):
    """Request body for POST /api/config/test-connection."""
    connection: Dict[str, Any] = Field(..., description="Connection configuration to test")


class ConnectionTestResponse(BaseModel):
    """Response model for POST /api/config/test-connection."""
    success: bool = Field(..., description="Whether the connection test succeeded")
    message: str = Field(..., description="Test result message")


class ConfigVersion(BaseModel):
    """Configuration version metadata."""
    version_id: str = Field(..., description="Version identifier")
    created_at: datetime = Field(..., description="When this version was created")
    created_by: Optional[str] = Field(None, description="User who created this version")
    comment: Optional[str] = Field(None, description="Optional comment for this version")


class ConfigHistoryResponse(BaseModel):
    """Response model for GET /api/config/history."""
    versions: List[ConfigVersion] = Field(default_factory=list, description="List of config versions")
    total: int = Field(..., description="Total number of versions")


class ConfigVersionResponse(BaseModel):
    """Response model for GET /api/config/history/{versionId}."""
    version_id: str = Field(..., description="Version identifier")
    config: Dict[str, Any] = Field(..., description="Configuration at this version")
    created_at: datetime = Field(..., description="When this version was created")
    created_by: Optional[str] = Field(None, description="User who created this version")
    comment: Optional[str] = Field(None, description="Optional comment for this version")


class ParseYAMLRequest(BaseModel):
    """Request body for POST /api/config/parse-yaml."""
    yaml: str = Field(..., description="YAML string to parse")


class ParseYAMLResponse(BaseModel):
    """Response model for POST /api/config/parse-yaml."""
    config: Dict[str, Any] = Field(..., description="Parsed configuration object")
    errors: List[str] = Field(default_factory=list, description="List of parsing/validation errors")


class ToYAMLRequest(BaseModel):
    """Request body for POST /api/config/to-yaml."""
    config: Dict[str, Any] = Field(..., description="Configuration object to convert")


class ToYAMLResponse(BaseModel):
    """Response model for POST /api/config/to-yaml."""
    yaml: str = Field(..., description="YAML string representation of the configuration")


