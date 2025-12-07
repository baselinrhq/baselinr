"""
Configuration API routes for Baselinr Dashboard.
"""

import sys
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.engine import Engine

# Add parent directory to path to import baselinr
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from config_models import (
    ConfigResponse,
    SaveConfigRequest,
    ConfigValidationRequest,
    ConfigValidationResponse,
    ConnectionTestRequest,
    ConnectionTestResponse,
    ConfigHistoryResponse,
    ConfigVersionResponse,
    ConfigVersion,
)
from config_service import ConfigService
from database import DatabaseClient

router = APIRouter(prefix="/api/config", tags=["config"])

# Global database client instance
_db_client = None

def get_db_client() -> DatabaseClient:
    """Get or create database client instance."""
    global _db_client
    if _db_client is None:
        _db_client = DatabaseClient()
    return _db_client

def get_config_service() -> ConfigService:
    """Dependency to get config service instance."""
    db_client = get_db_client()
    return ConfigService(db_client.engine)


@router.get("", response_model=ConfigResponse)
async def get_config(config_service: ConfigService = Depends(get_config_service)):
    """
    Get current configuration.
    
    Returns the current Baselinr configuration from file or database.
    """
    try:
        config = config_service.load_config()
        return ConfigResponse(config=config)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Configuration file not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load configuration: {str(e)}")


@router.post("", response_model=ConfigResponse)
async def save_config(
    request: SaveConfigRequest,
    config_service: ConfigService = Depends(get_config_service)
):
    """
    Save configuration.
    
    Validates and saves the Baselinr configuration to file or database.
    """
    try:
        saved_config = config_service.save_config(request.config)
        return ConfigResponse(config=saved_config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save configuration: {str(e)}")


@router.post("/validate", response_model=ConfigValidationResponse)
async def validate_config(
    request: ConfigValidationRequest,
    config_service: ConfigService = Depends(get_config_service)
):
    """
    Validate configuration.
    
    Validates the configuration without saving it.
    """
    try:
        is_valid, errors = config_service.validate_config(request.config)
        return ConfigValidationResponse(valid=is_valid, errors=errors)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate configuration: {str(e)}")


@router.post("/test-connection", response_model=ConnectionTestResponse)
async def test_connection(
    request: ConnectionTestRequest,
    config_service: ConfigService = Depends(get_config_service)
):
    """
    Test database connection.
    
    Tests a database connection configuration without saving it.
    """
    try:
        success, message = config_service.test_connection(request.connection)
        return ConnectionTestResponse(success=success, message=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to test connection: {str(e)}")


@router.get("/history", response_model=ConfigHistoryResponse)
async def get_config_history(
    config_service: ConfigService = Depends(get_config_service)
):
    """
    Get configuration version history.
    
    Returns a list of configuration versions with metadata.
    """
    try:
        versions = config_service.get_config_history()
        version_models = [
            ConfigVersion(
                version_id=v["version_id"],
                created_at=v["created_at"],
                created_by=v.get("created_by"),
                comment=v.get("comment"),
            )
            for v in versions
        ]
        return ConfigHistoryResponse(versions=version_models, total=len(version_models))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get config history: {str(e)}")


@router.get("/history/{version_id}", response_model=ConfigVersionResponse)
async def get_config_version(
    version_id: str,
    config_service: ConfigService = Depends(get_config_service)
):
    """
    Get specific configuration version.
    
    Returns the configuration at a specific version.
    """
    try:
        version_data = config_service.get_config_version(version_id)
        if not version_data:
            raise HTTPException(status_code=404, detail=f"Config version not found: {version_id}")
        
        from datetime import datetime
        created_at = version_data["created_at"]
        if isinstance(created_at, str):
            # Handle ISO format strings
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except ValueError:
                # Fallback to parsing common formats
                created_at = datetime.fromisoformat(created_at)
        
        return ConfigVersionResponse(
            version_id=version_data["version_id"],
            config=version_data["config"],
            created_at=created_at,
            created_by=version_data.get("created_by"),
            comment=version_data.get("comment"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get config version: {str(e)}")

