"""
Service layer for dataset configuration operations.
"""

import os
import sys
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.engine import Engine

# Add parent directory to path to import baselinr
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

try:
    from baselinr.config.loader import ConfigLoader
    from baselinr.config.schema import (
        BaselinrConfig,
        DatasetConfig,
        DatasetsConfig,
        DatasetsDirectoryConfig,
    )
    from baselinr.config.dataset_loader import DatasetFileLoader
    from baselinr.config.merger import ConfigMerger
    BASELINR_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Baselinr modules not available: {e}")
    BASELINR_AVAILABLE = False

logger = logging.getLogger(__name__)


class DatasetService:
    """Service for dataset configuration operations."""
    
    def __init__(self, config_service=None):
        """
        Initialize dataset service.
        
        Args:
            config_service: ConfigService instance for loading main config
        """
        self.config_service = config_service
        self._config_path = config_service._config_path if config_service else None
    
    def _get_datasets_dir(self) -> Optional[Path]:
        """Get datasets directory path from config."""
        if not BASELINR_AVAILABLE or not self.config_service:
            return None
        
        try:
            config = self.config_service.load_config()
            datasets_config = config.get("datasets")
            
            if not datasets_config:
                return None
            
            # Check if it's a directory config
            if isinstance(datasets_config, dict) and "datasets_dir" in datasets_config:
                datasets_dir = datasets_config["datasets_dir"]
                config_path = Path(self._config_path) if self._config_path else None
                
                if config_path:
                    # Resolve relative to config file
                    if Path(datasets_dir).is_absolute():
                        return Path(datasets_dir)
                    return config_path.parent / datasets_dir
                else:
                    return Path(datasets_dir) if Path(datasets_dir).is_absolute() else Path.cwd() / datasets_dir
            
            return None
        except Exception as e:
            logger.error(f"Failed to get datasets directory: {e}")
            return None
    
    def _generate_dataset_id(self, database: Optional[str], schema: Optional[str], table: Optional[str]) -> str:
        """Generate a unique dataset ID from identifiers."""
        parts = []
        if database:
            parts.append(f"db:{database}")
        if schema:
            parts.append(f"schema:{schema}")
        if table:
            parts.append(f"table:{table}")
        
        if not parts:
            import uuid
            return f"dataset:{uuid.uuid4().hex[:8]}"
        
        return "|".join(parts)
    
    def _parse_dataset_id(self, dataset_id: str) -> Dict[str, Optional[str]]:
        """Parse dataset ID into database/schema/table."""
        result = {"database": None, "schema": None, "table": None}
        
        for part in dataset_id.split("|"):
            if part.startswith("db:"):
                result["database"] = part[3:]
            elif part.startswith("schema:"):
                result["schema"] = part[7:]
            elif part.startswith("table:"):
                result["table"] = part[6:]
        
        return result
    
    def list_datasets(self) -> List[Dict[str, Any]]:
        """
        List all datasets with their configurations.
        
        Returns:
            List of dataset info dictionaries
        """
        if not BASELINR_AVAILABLE or not self.config_service:
            return []
        
        try:
            config = self.config_service.load_config()
            datasets_config = config.get("datasets")
            
            if not datasets_config:
                return []
            
            datasets = []
            
            # Handle directory-based configs
            if isinstance(datasets_config, dict) and "datasets_dir" in datasets_config:
                # Load from directory
                directory_config = DatasetsDirectoryConfig(**datasets_config)
                loader = DatasetFileLoader(config_file_path=Path(self._config_path) if self._config_path else None)
                dataset_configs = loader.load_from_directory(directory_config)
                
                for dataset in dataset_configs:
                    dataset_id = self._generate_dataset_id(
                        dataset.database, dataset.schema_, dataset.table
                    )
                    datasets.append({
                        "dataset_id": dataset_id,
                        "database": dataset.database,
                        "schema": dataset.schema_,
                        "table": dataset.table,
                        "source_file": dataset.source_file,
                        "config": dataset.model_dump(exclude_none=True),
                    })
            else:
                # Handle inline configs
                if isinstance(datasets_config, dict) and "datasets" in datasets_config:
                    dataset_list = datasets_config["datasets"]
                elif isinstance(datasets_config, list):
                    dataset_list = datasets_config
                else:
                    return []
                
                for dataset_dict in dataset_list:
                    if isinstance(dataset_dict, dict):
                        dataset = DatasetConfig(**dataset_dict)
                        dataset_id = self._generate_dataset_id(
                            dataset.database, dataset.schema_, dataset.table
                        )
                        datasets.append({
                            "dataset_id": dataset_id,
                            "database": dataset.database,
                            "schema": dataset.schema_,
                            "table": dataset.table,
                            "source_file": None,  # Inline config
                            "config": dataset.model_dump(exclude_none=True),
                        })
            
            return datasets
        except Exception as e:
            logger.error(f"Failed to list datasets: {e}")
            return []
    
    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get specific dataset configuration.
        
        Args:
            dataset_id: Dataset identifier
            
        Returns:
            Dataset configuration dictionary or None if not found
        """
        datasets = self.list_datasets()
        
        for dataset in datasets:
            if dataset["dataset_id"] == dataset_id:
                return dataset
        
        return None
    
    def create_dataset(self, config: Dict[str, Any], save_to_file: bool = False, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Create new dataset configuration.
        
        Args:
            config: Dataset configuration dictionary
            save_to_file: Whether to save to file
            file_path: File path if saving to file
            
        Returns:
            Created dataset info
        """
        if not BASELINR_AVAILABLE:
            raise RuntimeError("Baselinr modules not available")
        
        # Validate dataset config
        dataset = DatasetConfig(**config)
        dataset_id = self._generate_dataset_id(dataset.database, dataset.schema_, dataset.table)
        
        if save_to_file:
            # Save to file
            if not file_path:
                # Generate file path from dataset identifiers
                if dataset.table:
                    file_path = f"{dataset.table}.yml"
                elif dataset.schema_:
                    file_path = f"{dataset.schema_}.yml"
                else:
                    file_path = f"dataset_{dataset_id[:8]}.yml"
            
            self._save_dataset_to_file(file_path, dataset)
            dataset.source_file = file_path
        
        # Add to main config
        self._add_dataset_to_config(dataset)
        
        return {
            "dataset_id": dataset_id,
            "config": dataset.model_dump(exclude_none=True),
            "source_file": dataset.source_file,
        }
    
    def update_dataset(self, dataset_id: str, config: Dict[str, Any], save_to_file: Optional[bool] = None) -> Dict[str, Any]:
        """
        Update dataset configuration.
        
        Args:
            dataset_id: Dataset identifier
            config: Updated configuration
            save_to_file: Whether to save to file (None = keep current)
            
        Returns:
            Updated dataset info
        """
        if not BASELINR_AVAILABLE:
            raise RuntimeError("Baselinr modules not available")
        
        # Get existing dataset
        existing = self.get_dataset(dataset_id)
        if not existing:
            raise ValueError(f"Dataset not found: {dataset_id}")
        
        # Validate new config
        dataset = DatasetConfig(**config)
        
        # Update source file if needed
        if save_to_file is not None:
            if save_to_file and not existing["source_file"]:
                # Create new file
                if dataset.table:
                    file_path = f"{dataset.table}.yml"
                else:
                    file_path = f"dataset_{dataset_id[:8]}.yml"
                dataset.source_file = file_path
            elif not save_to_file:
                dataset.source_file = None
        
        # Save to file if it has a source file
        if dataset.source_file:
            self._save_dataset_to_file(dataset.source_file, dataset)
        
        # Update in main config
        self._update_dataset_in_config(dataset_id, dataset)
        
        return {
            "dataset_id": dataset_id,
            "config": dataset.model_dump(exclude_none=True),
            "source_file": dataset.source_file,
        }
    
    def delete_dataset(self, dataset_id: str) -> bool:
        """
        Delete dataset configuration.
        
        Args:
            dataset_id: Dataset identifier
            
        Returns:
            True if deleted, False if not found
        """
        existing = self.get_dataset(dataset_id)
        if not existing:
            return False
        
        # Delete file if it exists
        if existing.get("source_file"):
            self._delete_dataset_file(existing["source_file"])
        
        # Remove from main config
        self._remove_dataset_from_config(dataset_id)
        
        return True
    
    def get_dataset_preview(self, dataset_id: str) -> Dict[str, Any]:
        """
        Get merged config preview for a dataset.
        
        Args:
            dataset_id: Dataset identifier
            
        Returns:
            Dictionary with merged_config and precedence
        """
        if not BASELINR_AVAILABLE or not self.config_service:
            raise RuntimeError("Baselinr modules not available")
        
        # Get main config
        config = self.config_service.load_config()
        
        # Get dataset
        dataset_info = self.get_dataset(dataset_id)
        if not dataset_info:
            raise ValueError(f"Dataset not found: {dataset_id}")
        
        # Use ConfigMerger to get merged config
        try:
            baselinr_config = BaselinrConfig(**config)
            merger = ConfigMerger(baselinr_config)
            
            # Get merged config for this dataset
            # This is a simplified version - full implementation would use merger methods
            merged_config = dataset_info["config"]
            
            # Build precedence info
            precedence = {}
            source_file = dataset_info.get("source_file")
            if source_file:
                precedence["source"] = source_file
            else:
                precedence["source"] = "inline"
            
            return {
                "merged_config": merged_config,
                "precedence": precedence,
            }
        except Exception as e:
            logger.error(f"Failed to get dataset preview: {e}")
            raise
    
    def validate_dataset(self, dataset_id: str, config: Optional[Dict[str, Any]] = None) -> Tuple[bool, List[str], List[str]]:
        """
        Validate dataset configuration.
        
        Args:
            dataset_id: Dataset identifier
            config: Optional config to validate (None = use existing)
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        if not BASELINR_AVAILABLE:
            return False, ["Baselinr modules not available"], []
        
        errors = []
        warnings = []
        
        try:
            if config is None:
                dataset_info = self.get_dataset(dataset_id)
                if not dataset_info:
                    return False, [f"Dataset not found: {dataset_id}"], []
                config = dataset_info["config"]
            
            # Validate using Pydantic
            dataset = DatasetConfig(**config)
            
            return True, [], []
        except Exception as e:
            if hasattr(e, 'errors'):
                # Pydantic validation errors
                for error in e.errors():
                    field = '.'.join(str(loc) for loc in error.get('loc', []))
                    msg = error.get('msg', 'Validation error')
                    errors.append(f"{field}: {msg}")
            else:
                errors.append(str(e))
            
            return False, errors, warnings
    
    def list_files(self) -> List[Dict[str, Any]]:
        """
        List files in datasets directory.
        
        Returns:
            List of file info dictionaries
        """
        datasets_dir = self._get_datasets_dir()
        if not datasets_dir or not datasets_dir.exists():
            return []
        
        files = []
        for file_path in datasets_dir.rglob("*.yml"):
            if file_path.is_file():
                rel_path = file_path.relative_to(datasets_dir)
                files.append({
                    "path": str(rel_path),
                    "absolute_path": str(file_path),
                    "exists": True,
                    "modified": False,  # Would need to track this
                    "error": None,
                })
        
        return files
    
    def get_file_content(self, file_path: str) -> Optional[str]:
        """
        Get content of a dataset file.
        
        Args:
            file_path: File path relative to datasets directory
            
        Returns:
            File content as string or None if not found
        """
        datasets_dir = self._get_datasets_dir()
        if not datasets_dir:
            return None
        
        full_path = datasets_dir / file_path
        if not full_path.exists():
            return None
        
        try:
            with open(full_path, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return None
    
    def save_file(self, file_path: str, content: str) -> bool:
        """
        Save content to a dataset file.
        
        Args:
            file_path: File path relative to datasets directory
            content: File content (YAML)
            
        Returns:
            True if saved successfully
        """
        datasets_dir = self._get_datasets_dir()
        if not datasets_dir:
            # Create datasets directory
            datasets_dir = Path("./datasets")
            datasets_dir.mkdir(exist_ok=True)
        
        full_path = datasets_dir / file_path
        
        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Validate YAML
            yaml.safe_load(content)
            
            with open(full_path, 'w') as f:
                f.write(content)
            
            return True
        except Exception as e:
            logger.error(f"Failed to save file {file_path}: {e}")
            raise
    
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a dataset file.
        
        Args:
            file_path: File path relative to datasets directory
            
        Returns:
            True if deleted successfully
        """
        datasets_dir = self._get_datasets_dir()
        if not datasets_dir:
            return False
        
        full_path = datasets_dir / file_path
        if not full_path.exists():
            return False
        
        try:
            full_path.unlink()
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return False
    
    def _save_dataset_to_file(self, file_path: str, dataset: DatasetConfig):
        """Save dataset config to file."""
        datasets_dir = self._get_datasets_dir()
        if not datasets_dir:
            datasets_dir = Path("./datasets")
            datasets_dir.mkdir(exist_ok=True)
        
        full_path = datasets_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        dataset_dict = dataset.model_dump(exclude_none=True, exclude={"source_file"})
        
        with open(full_path, 'w') as f:
            yaml.dump(dataset_dict, f, default_flow_style=False, sort_keys=False)
    
    def _delete_dataset_file(self, file_path: str):
        """Delete dataset file."""
        datasets_dir = self._get_datasets_dir()
        if not datasets_dir:
            return
        
        full_path = datasets_dir / file_path
        if full_path.exists():
            full_path.unlink()
    
    def _add_dataset_to_config(self, dataset: DatasetConfig):
        """Add dataset to main config."""
        if not self.config_service:
            return
        
        config = self.config_service.load_config()
        
        # Ensure datasets section exists
        if "datasets" not in config:
            config["datasets"] = {"datasets": []}
        
        datasets_config = config["datasets"]
        if isinstance(datasets_config, dict) and "datasets" in datasets_config:
            datasets_config["datasets"].append(dataset.model_dump(exclude_none=True))
        elif isinstance(datasets_config, list):
            datasets_config.append(dataset.model_dump(exclude_none=True))
        else:
            config["datasets"] = {"datasets": [dataset.model_dump(exclude_none=True)]}
        
        # Save config
        self.config_service.save_config(config)
    
    def _update_dataset_in_config(self, dataset_id: str, dataset: DatasetConfig):
        """Update dataset in main config."""
        if not self.config_service:
            return
        
        config = self.config_service.load_config()
        datasets_config = config.get("datasets")
        
        if not datasets_config:
            return
        
        # Find and update dataset
        if isinstance(datasets_config, dict) and "datasets" in datasets_config:
            dataset_list = datasets_config["datasets"]
        elif isinstance(datasets_config, list):
            dataset_list = datasets_config
        else:
            return
        
        identifiers = self._parse_dataset_id(dataset_id)
        
        for i, ds in enumerate(dataset_list):
            if isinstance(ds, dict):
                if (ds.get("database") == identifiers["database"] and
                    ds.get("schema") == identifiers["schema"] and
                    ds.get("table") == identifiers["table"]):
                    dataset_list[i] = dataset.model_dump(exclude_none=True)
                    break
        
        # Save config
        self.config_service.save_config(config)
    
    def _remove_dataset_from_config(self, dataset_id: str):
        """Remove dataset from main config."""
        if not self.config_service:
            return
        
        config = self.config_service.load_config()
        datasets_config = config.get("datasets")
        
        if not datasets_config:
            return
        
        # Find and remove dataset
        if isinstance(datasets_config, dict) and "datasets" in datasets_config:
            dataset_list = datasets_config["datasets"]
        elif isinstance(datasets_config, list):
            dataset_list = datasets_config
        else:
            return
        
        identifiers = self._parse_dataset_id(dataset_id)
        
        dataset_list[:] = [
            ds for ds in dataset_list
            if isinstance(ds, dict) and not (
                ds.get("database") == identifiers["database"] and
                ds.get("schema") == identifiers["schema"] and
                ds.get("table") == identifiers["table"]
            )
        ]
        
        # Save config
        self.config_service.save_config(config)

