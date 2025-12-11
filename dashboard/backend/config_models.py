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
    comment: Optional[str] = Field(None, description="Optional comment for this configuration version")
    created_by: Optional[str] = Field(None, description="Optional user identifier who created this version")


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


class ConfigDiffRequest(BaseModel):
    """Request query params for GET /api/config/history/{version_id}/diff."""
    compare_with: Optional[str] = Field(None, description="Version ID to compare with (defaults to current)")


class ConfigDiffResponse(BaseModel):
    """Response model for GET /api/config/history/{version_id}/diff."""
    version_id: str = Field(..., description="Version ID being compared")
    compare_with: str = Field(..., description="Version ID or 'current' being compared against")
    added: Dict[str, Any] = Field(default_factory=dict, description="New keys/values added")
    removed: Dict[str, Any] = Field(default_factory=dict, description="Keys/values removed")
    changed: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Changed keys with old/new values")


class RestoreConfigRequest(BaseModel):
    """Request body for POST /api/config/history/{version_id}/restore."""
    confirm: bool = Field(..., description="Confirmation flag")
    comment: Optional[str] = Field(None, description="Optional comment for the restore action")


class RestoreConfigResponse(BaseModel):
    """Response model for POST /api/config/history/{version_id}/restore."""
    success: bool = Field(..., description="Whether the restore was successful")
    message: str = Field(..., description="Restore result message")
    config: Dict[str, Any] = Field(..., description="Restored configuration")


