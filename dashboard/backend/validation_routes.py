"""
Validation rules API routes for Baselinr Dashboard.
"""

import sys
import os
import logging

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.engine import Engine

# Add parent directory to path to import baselinr
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from validation_models import (
    ValidationRulesListResponse,
    ValidationRuleResponse,
    CreateValidationRuleRequest,
    UpdateValidationRuleRequest,
    TestValidationRuleResponse,
)
from validation_service import ValidationService
from database import DatabaseClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/validation/rules", tags=["validation-rules"])

# Check if demo mode is enabled
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Global database client instance
_db_client = None

def get_db_client() -> DatabaseClient:
    """Get or create database client instance."""
    global _db_client
    if DEMO_MODE:
        return None
    if _db_client is None:
        _db_client = DatabaseClient()
    return _db_client

def get_validation_service() -> ValidationService:
    """Dependency to get validation service instance."""
    if DEMO_MODE:
        return ValidationService(db_engine=None)
    db_client = get_db_client()
    return ValidationService(db_client.engine)


@router.get("", response_model=ValidationRulesListResponse)
async def list_validation_rules(
    table: str = Query(None, description="Filter by table name"),
    schema: str = Query(None, description="Filter by schema name"),
    rule_type: str = Query(None, description="Filter by rule type"),
    enabled: bool = Query(None, description="Filter by enabled status"),
    validation_service: ValidationService = Depends(get_validation_service)
):
    """
    List all validation rules with optional filters.
    
    Returns a list of all validation rules, optionally filtered by table, schema, rule type, or enabled status.
    """
    try:
        rules = validation_service.list_rules(
            table=table,
            schema=schema,
            rule_type=rule_type,
            enabled=enabled
        )
        
        rule_responses = [
            ValidationRuleResponse(
                id=rule["id"],
                rule_type=rule["rule_type"],
                table=rule["table"],
                schema=rule.get("schema"),
                column=rule.get("column"),
                config=rule.get("config", {}),
                severity=rule.get("severity", "medium"),
                enabled=rule.get("enabled", True),
                created_at=rule["created_at"],
                updated_at=rule.get("updated_at"),
                last_tested=rule.get("last_tested"),
                last_test_result=rule.get("last_test_result"),
            )
            for rule in rules
        ]
        
        return ValidationRulesListResponse(rules=rule_responses, total=len(rule_responses))
    except Exception as e:
        logger.error(f"Failed to list validation rules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list validation rules: {str(e)}")


@router.get("/{rule_id}", response_model=ValidationRuleResponse)
async def get_validation_rule(
    rule_id: str,
    validation_service: ValidationService = Depends(get_validation_service)
):
    """
    Get a specific validation rule by ID.
    
    Returns rule details by ID.
    """
    try:
        rule = validation_service.get_rule(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail=f"Validation rule not found: {rule_id}")
        
        return ValidationRuleResponse(
            id=rule["id"],
            rule_type=rule["rule_type"],
            table=rule["table"],
            schema=rule.get("schema"),
            column=rule.get("column"),
            config=rule.get("config", {}),
            severity=rule.get("severity", "medium"),
            enabled=rule.get("enabled", True),
            created_at=rule["created_at"],
            updated_at=rule.get("updated_at"),
            last_tested=rule.get("last_tested"),
            last_test_result=rule.get("last_test_result"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get validation rule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get validation rule: {str(e)}")


@router.post("", response_model=ValidationRuleResponse)
async def create_validation_rule(
    request: CreateValidationRuleRequest,
    validation_service: ValidationService = Depends(get_validation_service)
):
    """
    Create a new validation rule.
    
    Creates a new validation rule with the specified configuration.
    """
    # Prevent rule creation in demo mode
    if DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="Validation rule management is not available in demo mode"
        )
    
    try:
        # Validate rule type
        valid_types = ["format", "range", "enum", "not_null", "unique", "referential"]
        if request.rule_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid rule type: {request.rule_type}. Must be one of {valid_types}"
            )
        
        # Validate severity
        valid_severities = ["low", "medium", "high"]
        if request.severity not in valid_severities:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid severity: {request.severity}. Must be one of {valid_severities}"
            )
        
        rule_data = {
            "rule_type": request.rule_type,
            "table": request.table,
            "schema": request.schema,
            "column": request.column,
            "config": request.config,
            "severity": request.severity,
            "enabled": request.enabled,
        }
        
        created_rule = validation_service.create_rule(rule_data)
        
        return ValidationRuleResponse(
            id=created_rule["id"],
            rule_type=created_rule["rule_type"],
            table=created_rule["table"],
            schema=created_rule.get("schema"),
            column=created_rule.get("column"),
            config=created_rule.get("config", {}),
            severity=created_rule.get("severity", "medium"),
            enabled=created_rule.get("enabled", True),
            created_at=created_rule["created_at"],
            updated_at=created_rule.get("updated_at"),
            last_tested=created_rule.get("last_tested"),
            last_test_result=created_rule.get("last_test_result"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create validation rule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create validation rule: {str(e)}")


@router.put("/{rule_id}", response_model=ValidationRuleResponse)
async def update_validation_rule(
    rule_id: str,
    request: UpdateValidationRuleRequest,
    validation_service: ValidationService = Depends(get_validation_service)
):
    """
    Update an existing validation rule.
    
    Updates the specified validation rule. Only provided fields will be updated.
    """
    # Prevent rule updates in demo mode
    if DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="Validation rule management is not available in demo mode"
        )
    
    try:
        # Validate rule type if provided
        if request.rule_type is not None:
            valid_types = ["format", "range", "enum", "not_null", "unique", "referential"]
            if request.rule_type not in valid_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid rule type: {request.rule_type}. Must be one of {valid_types}"
                )
        
        # Validate severity if provided
        if request.severity is not None:
            valid_severities = ["low", "medium", "high"]
            if request.severity not in valid_severities:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid severity: {request.severity}. Must be one of {valid_severities}"
                )
        
        rule_data = {}
        if request.rule_type is not None:
            rule_data["rule_type"] = request.rule_type
        if request.table is not None:
            rule_data["table"] = request.table
        if request.schema is not None:
            rule_data["schema"] = request.schema
        if request.column is not None:
            rule_data["column"] = request.column
        if request.config is not None:
            rule_data["config"] = request.config
        if request.severity is not None:
            rule_data["severity"] = request.severity
        if request.enabled is not None:
            rule_data["enabled"] = request.enabled
        
        updated_rule = validation_service.update_rule(rule_id, rule_data)
        
        return ValidationRuleResponse(
            id=updated_rule["id"],
            rule_type=updated_rule["rule_type"],
            table=updated_rule["table"],
            schema=updated_rule.get("schema"),
            column=updated_rule.get("column"),
            config=updated_rule.get("config", {}),
            severity=updated_rule.get("severity", "medium"),
            enabled=updated_rule.get("enabled", True),
            created_at=updated_rule["created_at"],
            updated_at=updated_rule.get("updated_at"),
            last_tested=updated_rule.get("last_tested"),
            last_test_result=updated_rule.get("last_test_result"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update validation rule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update validation rule: {str(e)}")


@router.delete("/{rule_id}")
async def delete_validation_rule(
    rule_id: str,
    validation_service: ValidationService = Depends(get_validation_service)
):
    """
    Delete a validation rule.
    
    Deletes the specified validation rule by ID.
    """
    # Prevent rule deletion in demo mode
    if DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="Validation rule management is not available in demo mode"
        )
    
    try:
        deleted = validation_service.delete_rule(rule_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Validation rule not found: {rule_id}")
        
        return {"message": f"Validation rule {rule_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete validation rule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete validation rule: {str(e)}")


@router.post("/{rule_id}/test", response_model=TestValidationRuleResponse)
async def test_validation_rule(
    rule_id: str,
    validation_service: ValidationService = Depends(get_validation_service)
):
    """
    Test a validation rule.
    
    Tests the specified validation rule against the database.
    This performs basic structure validation. Full validation execution
    requires a source database connection and should be done through the ValidationExecutor.
    """
    try:
        test_result = validation_service.test_rule(rule_id)
        
        return TestValidationRuleResponse(
            rule_id=test_result["rule_id"],
            passed=test_result["passed"],
            failure_reason=test_result.get("failure_reason"),
            total_rows=test_result.get("total_rows", 0),
            failed_rows=test_result.get("failed_rows", 0),
            failure_rate=test_result.get("failure_rate", 0.0),
            sample_failures=test_result.get("sample_failures", []),
            tested_at=test_result["tested_at"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to test validation rule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to test validation rule: {str(e)}")

