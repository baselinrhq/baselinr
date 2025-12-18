"""
Hook management API routes for Baselinr Dashboard.
"""

import sys
import os

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.engine import Engine

# Add parent directory to path to import baselinr
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from hook_models import (
    HooksListResponse,
    HookWithId,
    SaveHookRequest,
    SaveHookResponse,
    HookTestRequest,
    HookTestResponse,
)
from hook_service import HookService
from config_service import ConfigService
from database import DatabaseClient

router = APIRouter(prefix="/api/config/hooks", tags=["hooks"])

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

def get_config_service() -> ConfigService:
    """Dependency to get config service instance."""
    if DEMO_MODE:
        return ConfigService(db_engine=None)
    db_client = get_db_client()
    return ConfigService(db_client.engine)

def get_hook_service() -> HookService:
    """Dependency to get hook service instance."""
    config_service = get_config_service()
    return HookService(config_service)


@router.get("", response_model=HooksListResponse)
async def list_hooks(
    hook_service: HookService = Depends(get_hook_service)
):
    """
    List all configured hooks.
    
    Returns a list of all hooks with their configurations.
    """
    try:
        hooks_list, hooks_enabled = hook_service.list_hooks()
        hooks_with_ids = [
            HookWithId(
                id=hook["id"],
                hook=hook["hook"],
                last_tested=None,  # TODO: Store test history if needed
                test_status=None,
            )
            for hook in hooks_list
        ]
        return HooksListResponse(
            hooks=hooks_with_ids,
            total=len(hooks_with_ids),
            hooks_enabled=hooks_enabled
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list hooks: {str(e)}")


@router.get("/{hook_id}", response_model=HookWithId)
async def get_hook(
    hook_id: str,
    hook_service: HookService = Depends(get_hook_service)
):
    """
    Get specific hook.
    
    Returns hook details by ID.
    """
    try:
        hook_data = hook_service.get_hook(hook_id)
        if not hook_data:
            raise HTTPException(status_code=404, detail=f"Hook not found: {hook_id}")
        
        return HookWithId(
            id=hook_data["id"],
            hook=hook_data["hook"],
            last_tested=None,
            test_status=None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get hook: {str(e)}")


@router.post("", response_model=SaveHookResponse)
async def create_hook(
    request: SaveHookRequest,
    hook_service: HookService = Depends(get_hook_service)
):
    """
    Create new hook.
    
    Creates a new hook and adds it to the configuration.
    """
    # Prevent hook creation in demo mode
    if DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="Hook management is not available in demo mode"
        )
    
    try:
        saved = hook_service.save_hook(None, request.hook)
        return SaveHookResponse(
            id=saved["id"],
            hook=HookWithId(
                id=saved["id"],
                hook=saved["hook"],
                last_tested=None,
                test_status=None,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create hook: {str(e)}")


@router.put("/{hook_id}", response_model=SaveHookResponse)
async def update_hook(
    hook_id: str,
    request: SaveHookRequest,
    hook_service: HookService = Depends(get_hook_service)
):
    """
    Update existing hook.
    
    Updates an existing hook configuration.
    """
    # Prevent hook updates in demo mode
    if DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="Hook management is not available in demo mode"
        )
    
    try:
        saved = hook_service.save_hook(hook_id, request.hook)
        return SaveHookResponse(
            id=saved["id"],
            hook=HookWithId(
                id=saved["id"],
                hook=saved["hook"],
                last_tested=None,
                test_status=None,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update hook: {str(e)}")


@router.delete("/{hook_id}")
async def delete_hook(
    hook_id: str,
    hook_service: HookService = Depends(get_hook_service)
):
    """
    Delete hook.
    
    Deletes a hook from the configuration.
    """
    # Prevent hook deletion in demo mode
    if DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="Hook management is not available in demo mode"
        )
    
    try:
        deleted = hook_service.delete_hook(hook_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Hook not found: {hook_id}")
        
        return {"message": "Hook deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete hook: {str(e)}")


@router.post("/{hook_id}/test", response_model=HookTestResponse)
async def test_hook(
    hook_id: str,
    request: HookTestRequest,
    hook_service: HookService = Depends(get_hook_service)
):
    """
    Test hook.
    
    Tests a hook by sending a test event through it.
    If hook config is provided in request, uses that; otherwise uses saved hook.
    """
    try:
        # If hook config provided, use it; otherwise get saved hook
        if request.hook:
            hook_config = request.hook
        else:
            hook_data = hook_service.get_hook(hook_id)
            if not hook_data:
                raise HTTPException(status_code=404, detail=f"Hook not found: {hook_id}")
            hook_config = hook_data["hook"]
        
        success, message, error, test_event = hook_service.test_hook(hook_config)
        
        return HookTestResponse(
            success=success,
            message=message,
            error=error,
            test_event=test_event
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to test hook: {str(e)}")


@router.put("/enabled", response_model=dict)
async def set_hooks_enabled(
    enabled: bool,
    hook_service: HookService = Depends(get_hook_service)
):
    """
    Set master switch for all hooks.
    
    Enables or disables all hooks globally.
    """
    # Prevent hook configuration in demo mode
    if DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="Hook management is not available in demo mode"
        )
    
    try:
        success = hook_service.set_hooks_enabled(enabled)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update hooks enabled status")
        
        return {"enabled": enabled, "message": f"Hooks {'enabled' if enabled else 'disabled'}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set hooks enabled: {str(e)}")

