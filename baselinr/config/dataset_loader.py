"""
Dataset file loader for loading dataset configurations from directory structure.
"""

import logging
from pathlib import Path
from typing import List, Optional

import yaml  # type: ignore[import-untyped]

from .schema import DatasetConfig, DatasetsDirectoryConfig

logger = logging.getLogger(__name__)


class DatasetFileLoader:
    """Loads dataset configurations from directory structure."""

    def __init__(self, config_file_path: Optional[Path] = None):
        """
        Initialize dataset file loader.

        Args:
            config_file_path: Path to main config file (for resolving relative paths)
        """
        self.config_file_path = config_file_path

    def load_from_directory(self, directory_config: DatasetsDirectoryConfig) -> List[DatasetConfig]:
        """
        Load all dataset configs from directory.

        Args:
            directory_config: DatasetsDirectoryConfig instance

        Returns:
            List of DatasetConfig instances with source_file set
        """
        datasets_dir = self._resolve_path(directory_config.datasets_dir)

        if not datasets_dir.exists():
            logger.warning(f"Datasets directory does not exist: {datasets_dir}")
            return []

        if not datasets_dir.is_dir():
            raise ValueError(f"Datasets path is not a directory: {datasets_dir}")

        # Find all matching files
        files = self._discover_files(datasets_dir, directory_config)

        # Load and parse each file
        datasets = []
        for file_path in files:
            try:
                file_datasets = self._load_file(file_path, directory_config)
                datasets.extend(file_datasets)
            except Exception as e:
                logger.error(f"Failed to load dataset file {file_path}: {e}")
                raise

        return datasets

    def _resolve_path(self, path_str: str) -> Path:
        """Resolve path relative to config file or as absolute."""
        path = Path(path_str)
        if path.is_absolute():
            return path

        if self.config_file_path:
            # Resolve relative to config file's directory
            return self.config_file_path.parent / path

        # Resolve relative to current working directory
        return Path.cwd() / path

    def _discover_files(self, directory: Path, config: DatasetsDirectoryConfig) -> List[Path]:
        """Discover YAML files matching pattern."""
        files = []

        pattern = config.file_pattern
        if config.recursive:
            pattern = f"**/{pattern}"

        for file_path in directory.glob(pattern):
            if file_path.is_file():
                # Check exclude patterns
                if config.exclude_patterns:
                    excluded = False
                    for exclude in config.exclude_patterns:
                        # Try pattern matching first
                        if file_path.match(exclude):
                            excluded = True
                            break
                        # For directory exclusions (e.g., **/templates/**),
                        # check if directory name is in path
                        # Extract directory name from pattern (remove wildcards and slashes)
                        dir_name = (
                            exclude.replace("**/", "")
                            .replace("/**", "")
                            .replace("*", "")
                            .strip("/")
                        )
                        if dir_name and dir_name in file_path.parts:
                            excluded = True
                            break
                    if excluded:
                        continue
                files.append(file_path)

        return sorted(files)

    def _load_file(self, file_path: Path, config: DatasetsDirectoryConfig) -> List[DatasetConfig]:
        """Load dataset configs from a single file."""
        with open(file_path, "r") as f:
            content = yaml.safe_load(f)

        if not content:
            return []

        # File can contain:
        # 1. Single dataset config (dict)
        # 2. List of dataset configs (list)
        # 3. Dict with 'datasets' key (list)

        datasets = []
        if isinstance(content, dict):
            if "datasets" in content:
                # Multiple datasets in one file
                dataset_list = content["datasets"]
            else:
                # Single dataset config
                dataset_list = [content]
        elif isinstance(content, list):
            dataset_list = content
        else:
            raise ValueError(f"Invalid dataset file format in {file_path}")

        # Convert to DatasetConfig instances
        for dataset_dict in dataset_list:
            if isinstance(dataset_dict, dict):
                dataset = DatasetConfig(**dataset_dict)
                dataset.source_file = str(file_path)
                datasets.append(dataset)

        return datasets
