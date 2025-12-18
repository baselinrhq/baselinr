"""
Configuration API routes for Baselinr Dashboard.
"""

import sys
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
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
    ParseYAMLRequest,
    ParseYAMLResponse,
    ToYAMLRequest,
    ToYAMLResponse,
    ConfigDiffRequest,
    ConfigDiffResponse,
    RestoreConfigRequest,
    RestoreConfigResponse,
)
from config_service import ConfigService
from database import DatabaseClient

router = APIRouter(prefix="/api/config", tags=["config"])

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
    Creates a history entry for this version.
    """
    # Prevent config saves in demo mode
    if DEMO_MODE:
        raise HTTPException(
            status_code=403, 
            detail="Configuration editing is not available in demo mode"
        )
    
    try:
        saved_config = config_service.save_config(
            request.config,
            comment=request.comment,
            created_by=request.created_by
        )
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


@router.get("/history/{version_id}/diff", response_model=ConfigDiffResponse)
async def get_config_diff(
    version_id: str,
    compare_with: Optional[str] = Query(None, description="Version ID to compare with (defaults to current)"),
    config_service: ConfigService = Depends(get_config_service)
):
    """
    Get diff between a configuration version and current config or another version.
    
    Query params:
        compare_with: Optional version ID to compare with (defaults to current config)
    """
    try:
        diff = config_service.get_config_diff(version_id, compare_with)
        return ConfigDiffResponse(**diff)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get config diff: {str(e)}")


@router.post("/history/{version_id}/restore", response_model=RestoreConfigResponse)
async def restore_config_version(
    version_id: str,
    request: RestoreConfigRequest,
    config_service: ConfigService = Depends(get_config_service)
):
    """
    Restore a configuration version as the current config.
    
    Creates a new history entry for the restore action.
    """
    # Prevent config restore in demo mode
    if DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="Configuration editing is not available in demo mode"
        )
    
    if not request.confirm:
        raise HTTPException(status_code=400, detail="Restore must be confirmed")
    
    try:
        restored_config = config_service.restore_config_version(version_id, request.comment)
        return RestoreConfigResponse(
            success=True,
            message=f"Configuration restored from version {version_id}",
            config=restored_config
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restore config version: {str(e)}")


@router.post("/parse-yaml", response_model=ParseYAMLResponse)
async def parse_yaml(
    request: ParseYAMLRequest,
    config_service: ConfigService = Depends(get_config_service)
):
    """
    Parse YAML string to configuration object.
    
    Parses a YAML string and validates it as a Baselinr configuration.
    """
    try:
        import yaml
        from baselinr.config.schema import BaselinrConfig
        
        # Parse YAML
        try:
            config_dict = yaml.safe_load(request.yaml)
            if not config_dict:
                raise ValueError("YAML does not contain a valid configuration object")
        except yaml.YAMLError as e:
            return ParseYAMLResponse(
                config={},
                errors=[f"YAML parsing error: {str(e)}"]
            )
        
        # Validate configuration
        try:
            validated_config = BaselinrConfig(**config_dict)
            return ParseYAMLResponse(
                config=validated_config.model_dump(mode='json'),
                errors=[]
            )
        except Exception as e:
            return ParseYAMLResponse(
                config=config_dict,
                errors=[f"Configuration validation error: {str(e)}"]
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse YAML: {str(e)}")


@router.post("/to-yaml", response_model=ToYAMLResponse)
async def to_yaml(
    request: ToYAMLRequest,
    config_service: ConfigService = Depends(get_config_service)
):
    """
    Convert configuration object to YAML string.
    
    Converts a Baselinr configuration object to its YAML representation.
    """
    try:
        import yaml
        from baselinr.config.schema import BaselinrConfig
        
        # Validate and convert config
        try:
            validated_config = BaselinrConfig(**request.config)
            config_dict = validated_config.model_dump(mode='json', exclude_none=True)
        except Exception as e:
            # If validation fails, still try to convert the dict
            config_dict = request.config
        
        # Convert to YAML
        yaml_string = yaml.dump(
            config_dict,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            allow_unicode=True,
        )
        
        return ToYAMLResponse(yaml=yaml_string)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to convert to YAML: {str(e)}")


@router.get("/quality")
async def get_quality_config(config_service: ConfigService = Depends(get_config_service)):
    """
    Get quality scoring configuration.
    
    Returns the quality_scoring section of the current configuration.
    """
    try:
        config = config_service.load_config()
        quality_config = config.get("quality_scoring")
        return quality_config if quality_config is not None else {}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Configuration file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load quality config: {str(e)}")


@router.post("/quality")
async def save_quality_config(
    quality_config: dict,
    config_service: ConfigService = Depends(get_config_service)
):
    """
    Update quality scoring configuration.
    
    Updates the quality_scoring section of the configuration and saves it.
    """
    # Prevent config edits in demo mode
    if DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="Configuration editing is not available in demo mode"
        )
    
    try:
        # Load current config
        current_config = config_service.load_config()
        
        # Update quality_scoring section
        current_config["quality_scoring"] = quality_config
        
        # Validate and save
        from baselinr.config.schema import BaselinrConfig
        validated_config = BaselinrConfig(**current_config)
        
        saved_config = config_service.save_config(
            validated_config.model_dump(mode='json'),
            comment="Updated quality scoring configuration"
        )
        
        return saved_config.get("quality_scoring", {})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save quality config: {str(e)}")

