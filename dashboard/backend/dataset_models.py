"""
Pydantic models for dataset API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class DatasetIdentifier(BaseModel):
    """Dataset identifier (database/schema/table)."""
    database: Optional[str] = None
    schema: Optional[str] = None
    table: Optional[str] = None


class DatasetFileInfo(BaseModel):
    """File metadata for dataset configuration."""
    path: str = Field(..., description="File path relative to datasets directory")
    absolute_path: str = Field(..., description="Absolute file path")
    exists: bool = Field(..., description="Whether file exists")
    modified: bool = Field(False, description="Whether file has unsaved changes")
    error: Optional[str] = Field(None, description="Error message if file has issues")


class DatasetListItem(BaseModel):
    """Dataset list item with basic info."""
    dataset_id: str = Field(..., description="Unique dataset identifier")
    database: Optional[str] = None
    schema: Optional[str] = None
    table: Optional[str] = None
    source_file: Optional[str] = Field(None, description="Source file path if file-based")
    has_profiling: bool = Field(False, description="Whether profiling is configured")
    has_drift: bool = Field(False, description="Whether drift detection is configured")
    has_validation: bool = Field(False, description="Whether validation is configured")
    has_anomaly: bool = Field(False, description="Whether anomaly detection is configured")
    has_columns: bool = Field(False, description="Whether column configs exist")


class DatasetListResponse(BaseModel):
    """Response model for GET /api/config/datasets."""
    datasets: List[DatasetListItem] = Field(default_factory=list)
    total: int = Field(..., description="Total number of datasets")


class DatasetConfigResponse(BaseModel):
    """Response model for GET /api/config/datasets/{dataset_id}."""
    dataset_id: str = Field(..., description="Unique dataset identifier")
    config: Dict[str, Any] = Field(..., description="Full dataset configuration")
    source_file: Optional[str] = Field(None, description="Source file path if file-based")


class CreateDatasetRequest(BaseModel):
    """Request body for POST /api/config/datasets."""
    config: Dict[str, Any] = Field(..., description="Dataset configuration")
    save_to_file: bool = Field(False, description="Whether to save to file or inline")
    file_path: Optional[str] = Field(None, description="File path if save_to_file is true")


class UpdateDatasetRequest(BaseModel):
    """Request body for PUT /api/config/datasets/{dataset_id}."""
    config: Dict[str, Any] = Field(..., description="Updated dataset configuration")
    save_to_file: Optional[bool] = Field(None, description="Whether to save to file (if changing)")


class DatasetPreviewResponse(BaseModel):
    """Response model for POST /api/config/datasets/{dataset_id}/preview."""
    merged_config: Dict[str, Any] = Field(..., description="Merged configuration with all overrides")
    precedence: Dict[str, str] = Field(..., description="Map of config keys to their source (file path or 'inline')")


class ConfigPrecedenceInfo(BaseModel):
    """Information about config precedence."""
    key: str = Field(..., description="Config key path")
    value: Any = Field(..., description="Config value")
    source: str = Field(..., description="Source of this config (file path, 'schema', 'database', 'global', etc.)")
    priority: int = Field(..., description="Priority level (higher = more specific)")


class DatasetPrecedenceResponse(BaseModel):
    """Response model for POST /api/config/datasets/{dataset_id}/precedence."""
    precedence: List[ConfigPrecedenceInfo] = Field(..., description="List of config precedence information")


class DatasetValidationResponse(BaseModel):
    """Response model for POST /api/config/datasets/{dataset_id}/validate."""
    valid: bool = Field(..., description="Whether the configuration is valid")
    errors: List[str] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(default_factory=list, description="List of validation warnings")


class DatasetFileListResponse(BaseModel):
    """Response model for GET /api/config/datasets/files."""
    files: List[DatasetFileInfo] = Field(default_factory=list)
    directory: str = Field(..., description="Datasets directory path")


class DatasetFileContentResponse(BaseModel):
    """Response model for GET /api/config/datasets/files/{file_path}."""
    path: str = Field(..., description="File path")
    content: str = Field(..., description="File content (YAML)")
    exists: bool = Field(..., description="Whether file exists")


class CreateDatasetFileRequest(BaseModel):
    """Request body for POST /api/config/datasets/files."""
    path: str = Field(..., description="File path relative to datasets directory")
    content: str = Field(..., description="File content (YAML)")


class UpdateDatasetFileRequest(BaseModel):
    """Request body for PUT /api/config/datasets/files/{file_path}."""
    content: str = Field(..., description="File content (YAML)")


class MigrationPreviewRequest(BaseModel):
    """Request body for POST /api/config/migrate/preview."""
    config: Optional[Dict[str, Any]] = Field(None, description="Config to migrate (None = use current)")


class MigrationPreviewResponse(BaseModel):
    """Response model for POST /api/config/migrate/preview."""
    changes: Dict[str, Any] = Field(..., description="Preview of migration changes")
    files_to_create: List[str] = Field(default_factory=list, description="List of files that will be created")
    datasets_to_migrate: int = Field(..., description="Number of datasets that will be migrated")


class MigrationRequest(BaseModel):
    """Request body for POST /api/config/migrate."""
    config: Optional[Dict[str, Any]] = Field(None, description="Config to migrate (None = use current)")
    backup: bool = Field(True, description="Whether to create backup of original config")
    output_dir: Optional[str] = Field(None, description="Output directory for migrated files (default: ./datasets)")


class MigrationResponse(BaseModel):
    """Response model for POST /api/config/migrate."""
    success: bool = Field(..., description="Whether migration succeeded")
    migrated: int = Field(..., description="Number of datasets migrated")
    files_created: List[str] = Field(default_factory=list, description="List of files created")
    backup_path: Optional[str] = Field(None, description="Path to backup file if created")
    errors: List[str] = Field(default_factory=list, description="List of errors if any")

