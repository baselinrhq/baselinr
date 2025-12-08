"""
Pydantic models for hook management API requests and responses.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any


class HookWithId(BaseModel):
    """Hook configuration with ID."""
    id: str = Field(..., description="Hook identifier (array index)")
    hook: Dict[str, Any] = Field(..., description="Hook configuration")
    last_tested: Optional[datetime] = Field(None, description="When the hook was last tested")
    test_status: Optional[str] = Field(None, description="Last test status (success, error)")


class HooksListResponse(BaseModel):
    """Response model for GET /api/config/hooks."""
    hooks: List[HookWithId] = Field(default_factory=list, description="List of configured hooks")
    total: int = Field(..., description="Total number of hooks")
    hooks_enabled: bool = Field(..., description="Master switch for all hooks")


class SaveHookRequest(BaseModel):
    """Request body for POST/PUT /api/config/hooks."""
    hook: Dict[str, Any] = Field(..., description="Hook configuration")


class SaveHookResponse(BaseModel):
    """Response model for POST/PUT /api/config/hooks."""
    id: str = Field(..., description="Hook identifier")
    hook: HookWithId = Field(..., description="Saved hook details")


class HookTestRequest(BaseModel):
    """Request body for POST /api/config/hooks/{hook_id}/test."""
    hook: Optional[Dict[str, Any]] = Field(None, description="Optional hook config to test (if not provided, uses saved hook)")


class HookTestResponse(BaseModel):
    """Response model for POST /api/config/hooks/{hook_id}/test."""
    success: bool = Field(..., description="Whether the hook test succeeded")
    message: str = Field(..., description="Test result message")
    error: Optional[str] = Field(None, description="Error message if test failed")
    test_event: Optional[Dict[str, Any]] = Field(None, description="Test event that was sent")

