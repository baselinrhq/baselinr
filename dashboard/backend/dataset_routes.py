"""
Dataset API routes for Baselinr Dashboard.
"""

import sys
import os
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.engine import Engine

# Add parent directory to path to import baselinr
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from dataset_models import (
    DatasetListResponse,
    DatasetListItem,
    DatasetConfigResponse,
    CreateDatasetRequest,
    UpdateDatasetRequest,
    DatasetPreviewResponse,
    DatasetPrecedenceResponse,
    DatasetValidationResponse,
    DatasetFileListResponse,
    DatasetFileInfo,
    DatasetFileContentResponse,
    CreateDatasetFileRequest,
    UpdateDatasetFileRequest,
    MigrationPreviewRequest,
    MigrationPreviewResponse,
    MigrationRequest,
    MigrationResponse,
)
from dataset_service import DatasetService
from config_service import ConfigService
from database import DatabaseClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config/datasets", tags=["datasets"])

# Check if demo mode is enabled
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Global instances
_db_client = None
_config_service = None
_dataset_service = None


def get_db_client() -> DatabaseClient:
    """Get or create database client instance."""
    global _db_client
    if DEMO_MODE:
        return None
    if _db_client is None:
        _db_client = DatabaseClient()
    return _db_client


def get_config_service() -> ConfigService:
    """Get or create config service instance."""
    global _config_service
    if DEMO_MODE:
        _config_service = ConfigService(db_engine=None)
        return _config_service
    if _config_service is None:
        db_client = get_db_client()
        _config_service = ConfigService(db_client.engine)
    return _config_service


def get_dataset_service() -> DatasetService:
    """Get or create dataset service instance."""
    global _dataset_service
    if _dataset_service is None:
        config_service = get_config_service()
        _dataset_service = DatasetService(config_service)
    return _dataset_service


@router.get("", response_model=DatasetListResponse)
async def list_datasets():
    """
    List all datasets with their configurations.
    
    Returns list of datasets with basic info about what features are configured.
    """
    try:
        service = get_dataset_service()
        datasets = service.list_datasets()
        
        # Convert to list items with feature flags
        list_items = []
        for ds in datasets:
            config = ds.get("config", {})
            list_items.append(DatasetListItem(
                dataset_id=ds["dataset_id"],
                database=ds.get("database"),
                schema=ds.get("schema"),
                table=ds.get("table"),
                source_file=ds.get("source_file"),
                has_profiling=bool(config.get("profiling")),
                has_drift=bool(config.get("drift")),
                has_validation=bool(config.get("validation")),
                has_anomaly=bool(config.get("anomaly")),
                has_columns=bool(config.get("columns")),
            ))
        
        return DatasetListResponse(datasets=list_items, total=len(list_items))
    except Exception as e:
        logger.error(f"Failed to list datasets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list datasets: {str(e)}")


@router.get("/{dataset_id}", response_model=DatasetConfigResponse)
async def get_dataset(dataset_id: str):
    """
    Get specific dataset configuration.
    
    Args:
        dataset_id: Dataset identifier (format: db:name|schema:name|table:name)
    """
    try:
        service = get_dataset_service()
        dataset = service.get_dataset(dataset_id)
        
        if not dataset:
            raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")
        
        return DatasetConfigResponse(
            dataset_id=dataset_id,
            config=dataset["config"],
            source_file=dataset.get("source_file"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dataset {dataset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dataset: {str(e)}")


@router.post("", response_model=DatasetConfigResponse)
async def create_dataset(request: CreateDatasetRequest):
    """
    Create new dataset configuration.
    
    Can save to file or inline in main config.
    """
    # Prevent dataset creation in demo mode
    if DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="Dataset management is not available in demo mode"
        )
    
    try:
        service = get_dataset_service()
        result = service.create_dataset(
            request.config,
            save_to_file=request.save_to_file,
            file_path=request.file_path,
        )
        
        return DatasetConfigResponse(
            dataset_id=result["dataset_id"],
            config=result["config"],
            source_file=result.get("source_file"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create dataset: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create dataset: {str(e)}")


@router.put("/{dataset_id}", response_model=DatasetConfigResponse)
async def update_dataset(dataset_id: str, request: UpdateDatasetRequest):
    """
    Update dataset configuration.
    
    Args:
        dataset_id: Dataset identifier
    """
    # Prevent dataset updates in demo mode
    if DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="Dataset management is not available in demo mode"
        )
    
    try:
        service = get_dataset_service()
        result = service.update_dataset(
            dataset_id,
            request.config,
            save_to_file=request.save_to_file,
        )
        
        return DatasetConfigResponse(
            dataset_id=result["dataset_id"],
            config=result["config"],
            source_file=result.get("source_file"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update dataset {dataset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update dataset: {str(e)}")


@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: str):
    """
    Delete dataset configuration.
    
    Args:
        dataset_id: Dataset identifier
    """
    # Prevent dataset deletion in demo mode
    if DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="Dataset management is not available in demo mode"
        )
    
    try:
        service = get_dataset_service()
        success = service.delete_dataset(dataset_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")
        
        return {"success": True, "message": f"Dataset {dataset_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete dataset {dataset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete dataset: {str(e)}")


@router.post("/{dataset_id}/preview", response_model=DatasetPreviewResponse)
async def preview_dataset(dataset_id: str):
    """
    Get merged config preview for a dataset.
    
    Shows the final configuration after all overrides are applied.
    """
    try:
        service = get_dataset_service()
        preview = service.get_dataset_preview(dataset_id)
        
        return DatasetPreviewResponse(
            merged_config=preview["merged_config"],
            precedence=preview["precedence"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to preview dataset {dataset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to preview dataset: {str(e)}")


@router.post("/{dataset_id}/validate", response_model=DatasetValidationResponse)
async def validate_dataset(dataset_id: str, config: Optional[dict] = None):
    """
    Validate dataset configuration.
    
    Args:
        dataset_id: Dataset identifier
        config: Optional config to validate (None = use existing)
    """
    try:
        service = get_dataset_service()
        is_valid, errors, warnings = service.validate_dataset(dataset_id, config)
        
        return DatasetValidationResponse(
            valid=is_valid,
            errors=errors,
            warnings=warnings,
        )
    except Exception as e:
        logger.error(f"Failed to validate dataset {dataset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to validate dataset: {str(e)}")


# File management endpoints

@router.get("/files", response_model=DatasetFileListResponse)
async def list_files():
    """List files in datasets directory."""
    try:
        service = get_dataset_service()
        files = service.list_files()
        
        file_infos = [
            DatasetFileInfo(**f) for f in files
        ]
        
        datasets_dir = service._get_datasets_dir()
        directory = str(datasets_dir) if datasets_dir else "./datasets"
        
        return DatasetFileListResponse(files=file_infos, directory=directory)
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/files/{file_path:path}", response_model=DatasetFileContentResponse)
async def get_file(file_path: str):
    """
    Get content of a dataset file.
    
    Args:
        file_path: File path relative to datasets directory
    """
    try:
        service = get_dataset_service()
        content = service.get_file_content(file_path)
        
        if content is None:
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        return DatasetFileContentResponse(
            path=file_path,
            content=content,
            exists=True,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file {file_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get file: {str(e)}")


@router.post("/files", response_model=DatasetFileContentResponse)
async def create_file(request: CreateDatasetFileRequest):
    """Create new dataset file."""
    try:
        service = get_dataset_service()
        success = service.save_file(request.path, request.content)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create file")
        
        return DatasetFileContentResponse(
            path=request.path,
            content=request.content,
            exists=True,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create file: {str(e)}")


@router.put("/files/{file_path:path}", response_model=DatasetFileContentResponse)
async def update_file(file_path: str, request: UpdateDatasetFileRequest):
    """
    Update dataset file content.
    
    Args:
        file_path: File path relative to datasets directory
    """
    try:
        service = get_dataset_service()
        success = service.save_file(file_path, request.content)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update file")
        
        return DatasetFileContentResponse(
            path=file_path,
            content=request.content,
            exists=True,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update file {file_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update file: {str(e)}")


@router.delete("/files/{file_path:path}")
async def delete_file(file_path: str):
    """
    Delete dataset file.
    
    Args:
        file_path: File path relative to datasets directory
    """
    try:
        service = get_dataset_service()
        success = service.delete_file(file_path)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        return {"success": True, "message": f"File {file_path} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file {file_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")



