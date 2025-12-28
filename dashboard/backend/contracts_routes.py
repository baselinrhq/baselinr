"""
ODCS Contracts API routes for Baselinr Dashboard.
"""

import logging
import os
import sys

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional

# Add parent directory to path to import baselinr
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from contracts_models import (
    ContractsListResponse,
    ContractDetailResponse,
    ContractSummary,
    ContractValidationResponse,
    ContractRulesResponse,
    ValidationRuleFromContract,
    CreateContractRequest,
    UpdateContractRequest,
    ODCSContract,
)
from contracts_service import ContractsService
from database import DatabaseClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contracts", tags=["contracts"])

# Check if demo mode is enabled
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Global service instance
_contracts_service: Optional[ContractsService] = None


def get_contracts_service() -> ContractsService:
    """Get or create contracts service instance."""
    global _contracts_service
    
    if _contracts_service is None:
        # Try to get contracts directory from config
        contracts_dir = os.getenv("CONTRACTS_DIR", "./contracts")
        
        try:
            from config_service import ConfigService
            config_service = ConfigService()
            config = config_service.load_config()
            
            # Get contracts directory from config
            contracts_config = config.get("contracts")
            if contracts_config and isinstance(contracts_config, dict):
                config_dir = contracts_config.get("directory")
                if config_dir:
                    # Resolve relative to config file if needed
                    config_path = config_service._config_path
                    if config_path:
                        from pathlib import Path
                        config_file_path = Path(config_path)
                        contracts_path = Path(config_dir)
                        if not contracts_path.is_absolute():
                            contracts_dir = str(config_file_path.parent / contracts_path)
                        else:
                            contracts_dir = config_dir
                    else:
                        contracts_dir = config_dir
        except Exception as e:
            logger.debug(f"Could not load contracts dir from config: {e}")
            # Fall back to environment variable or default
        
        _contracts_service = ContractsService(contracts_dir)
    
    return _contracts_service


def set_contracts_directory(contracts_dir: str) -> None:
    """Set the contracts directory for the service."""
    global _contracts_service
    
    if _contracts_service is None:
        _contracts_service = ContractsService(contracts_dir)
    else:
        _contracts_service.set_contracts_dir(contracts_dir)


# =============================================================================
# Routes
# =============================================================================


@router.get("", response_model=ContractsListResponse)
async def list_contracts(
    contracts_service: ContractsService = Depends(get_contracts_service)
):
    """
    List all ODCS contracts.
    
    Returns a list of contract summaries with basic information.
    """
    try:
        summaries = contracts_service.list_contracts()
        
        contract_summaries = [
            ContractSummary(
                id=s.get("id"),
                title=s.get("title"),
                status=s.get("status"),
                owner=s.get("owner"),
                domain=s.get("domain"),
                datasets=s.get("datasets", []),
                quality_rules_count=s.get("quality_rules_count", 0),
                service_levels_count=s.get("service_levels_count", 0),
                stakeholders_count=s.get("stakeholders_count", 0),
            )
            for s in summaries
        ]
        
        return ContractsListResponse(
            contracts=contract_summaries,
            total=len(contract_summaries)
        )
    except Exception as e:
        logger.error(f"Failed to list contracts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list contracts: {str(e)}")


@router.get("/validate", response_model=ContractValidationResponse)
async def validate_contracts(
    strict: bool = Query(False, description="Treat warnings as errors"),
    contracts_service: ContractsService = Depends(get_contracts_service)
):
    """
    Validate all loaded contracts.
    
    Returns validation results including errors and warnings.
    """
    try:
        result = contracts_service.validate_contracts(strict=strict)
        
        return ContractValidationResponse(
            valid=result["valid"],
            contracts_checked=result["contracts_checked"],
            errors=result["errors"],
            warnings=result["warnings"],
        )
    except Exception as e:
        logger.error(f"Failed to validate contracts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to validate contracts: {str(e)}")


@router.get("/rules", response_model=ContractRulesResponse)
async def list_contract_rules(
    contract_id: Optional[str] = Query(None, description="Filter by contract ID"),
    contracts_service: ContractsService = Depends(get_contracts_service)
):
    """
    List validation rules from contracts.
    
    Returns all validation rules extracted from ODCS contracts.
    """
    try:
        rules = contracts_service.get_validation_rules(contract_id=contract_id)
        
        rule_responses = [
            ValidationRuleFromContract(
                type=r["type"],
                table=r["table"],
                column=r.get("column"),
                severity=r.get("severity", "error"),
                dimension=r.get("dimension"),
                description=r.get("description"),
                contract_id=r.get("contract_id"),
            )
            for r in rules
        ]
        
        return ContractRulesResponse(
            rules=rule_responses,
            total=len(rule_responses)
        )
    except Exception as e:
        logger.error(f"Failed to list contract rules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list contract rules: {str(e)}")


@router.get("/{contract_id}", response_model=ContractDetailResponse)
async def get_contract(
    contract_id: str,
    contracts_service: ContractsService = Depends(get_contracts_service)
):
    """
    Get a specific contract by ID.
    
    Returns the full contract details.
    """
    try:
        contract = contracts_service.get_contract(contract_id)
        
        if not contract:
            raise HTTPException(status_code=404, detail=f"Contract not found: {contract_id}")
        
        # Remove internal fields
        contract_copy = {k: v for k, v in contract.items() if not k.startswith("_")}
        
        return ContractDetailResponse(contract=contract_copy)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get contract {contract_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get contract: {str(e)}")


@router.post("", response_model=ContractDetailResponse)
async def create_contract(
    request: CreateContractRequest,
    contracts_service: ContractsService = Depends(get_contracts_service)
):
    """
    Create a new contract.
    
    Creates a new ODCS contract file in the contracts directory.
    """
    try:
        contract = contracts_service.create_contract(request.contract.model_dump(exclude_none=True))
        return ContractDetailResponse(contract=contract)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create contract: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create contract: {str(e)}")


@router.put("/{contract_id}", response_model=ContractDetailResponse)
async def update_contract(
    contract_id: str,
    request: UpdateContractRequest,
    contracts_service: ContractsService = Depends(get_contracts_service)
):
    """
    Update an existing contract.
    
    Updates an existing ODCS contract file.
    """
    try:
        contract = contracts_service.update_contract(
            contract_id, 
            request.contract.model_dump(exclude_none=True)
        )
        return ContractDetailResponse(contract=contract)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update contract {contract_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update contract: {str(e)}")


@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: str,
    contracts_service: ContractsService = Depends(get_contracts_service)
):
    """
    Delete a contract.
    
    Deletes an ODCS contract file from the contracts directory.
    """
    try:
        contracts_service.delete_contract(contract_id)
        return {"message": f"Contract {contract_id} deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete contract {contract_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete contract: {str(e)}")

