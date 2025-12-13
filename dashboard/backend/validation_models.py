"""
Pydantic models for validation rules API requests and responses.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any


class ValidationRuleResponse(BaseModel):
    """Validation rule response model."""
    id: str = Field(..., description="Rule identifier")
    rule_type: str = Field(..., description="Rule type: format, range, enum, not_null, unique, referential")
    table: str = Field(..., description="Table name")
    schema: Optional[str] = Field(None, description="Schema name")
    column: Optional[str] = Field(None, description="Column name (None for table-level rules)")
    config: Dict[str, Any] = Field(default_factory=dict, description="Rule-specific configuration")
    severity: str = Field("medium", description="Severity level: low, medium, high")
    enabled: bool = Field(True, description="Whether this rule is enabled")
    created_at: datetime = Field(..., description="When the rule was created")
    updated_at: Optional[datetime] = Field(None, description="When the rule was last updated")
    last_tested: Optional[datetime] = Field(None, description="When the rule was last tested")
    last_test_result: Optional[bool] = Field(None, description="Result of last test (True=passed, False=failed)")


class ValidationRulesListResponse(BaseModel):
    """Response model for GET /api/validation/rules."""
    rules: List[ValidationRuleResponse] = Field(default_factory=list, description="List of validation rules")
    total: int = Field(..., description="Total number of rules")


class CreateValidationRuleRequest(BaseModel):
    """Request body for POST /api/validation/rules."""
    rule_type: str = Field(..., description="Rule type: format, range, enum, not_null, unique, referential")
    table: str = Field(..., description="Table name")
    schema: Optional[str] = Field(None, description="Schema name")
    column: Optional[str] = Field(None, description="Column name (None for table-level rules)")
    config: Dict[str, Any] = Field(default_factory=dict, description="Rule-specific configuration")
    severity: str = Field("medium", description="Severity level: low, medium, high")
    enabled: bool = Field(True, description="Whether this rule is enabled")


class UpdateValidationRuleRequest(BaseModel):
    """Request body for PUT /api/validation/rules/{id}."""
    rule_type: Optional[str] = Field(None, description="Rule type")
    table: Optional[str] = Field(None, description="Table name")
    schema: Optional[str] = Field(None, description="Schema name")
    column: Optional[str] = Field(None, description="Column name")
    config: Optional[Dict[str, Any]] = Field(None, description="Rule-specific configuration")
    severity: Optional[str] = Field(None, description="Severity level")
    enabled: Optional[bool] = Field(None, description="Whether this rule is enabled")


class TestValidationRuleResponse(BaseModel):
    """Response model for POST /api/validation/rules/{id}/test."""
    rule_id: str = Field(..., description="Rule identifier")
    passed: bool = Field(..., description="Whether the rule passed")
    failure_reason: Optional[str] = Field(None, description="Failure reason if rule failed")
    total_rows: int = Field(0, description="Total rows tested")
    failed_rows: int = Field(0, description="Number of failed rows")
    failure_rate: float = Field(0.0, description="Failure rate (0.0 to 1.0)")
    sample_failures: List[Dict[str, Any]] = Field(default_factory=list, description="Sample failed rows")
    tested_at: datetime = Field(..., description="When the test was performed")

