"""
Migration utility for converting inline dataset configs to file-based structure.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import yaml  # type: ignore[import-untyped]

from .schema import BaselinrConfig, DatasetConfig, DatasetsConfig

logger = logging.getLogger(__name__)


class ConfigMigrator:
    """Migrates inline dataset configs to file-based structure."""

    def __init__(self, config: BaselinrConfig, config_file_path: Path):
        """
        Initialize migrator.

        Args:
            config: BaselinrConfig instance
            config_file_path: Path to original config file
        """
        self.config = config
        self.config_file_path = config_file_path
        self.config_dir = config_file_path.parent

    def migrate_to_directory(
        self, output_dir: str = "datasets", create_backup: bool = True
    ) -> Dict[str, Any]:
        """
        Migrate inline dataset configs to directory structure.

        Args:
            output_dir: Directory name for dataset files
            create_backup: Whether to create backup of original config

        Returns:
            Migration report with details
        """
        if not self.config.datasets or not isinstance(self.config.datasets, DatasetsConfig):
            return {
                "migrated": False,
                "message": "No inline dataset configs found",
                "files_created": [],
            }

        if not self.config.datasets.datasets:
            return {
                "migrated": False,
                "message": "No inline dataset configs found",
                "files_created": [],
            }

        backup_path = None
        # Create backup if requested
        if create_backup:
            backup_path = self._create_backup()
            logger.info(f"Created backup: {backup_path}")

        # Create output directory
        datasets_path = self.config_dir / output_dir
        datasets_path.mkdir(exist_ok=True)

        # Migrate each dataset
        files_created = []
        for dataset in self.config.datasets.datasets:
            file_path = self._create_dataset_file(dataset, datasets_path)
            files_created.append(str(file_path))

        # Update main config file
        updated_config = self._update_config_file(output_dir)

        return {
            "migrated": True,
            "files_created": files_created,
            "backup_path": str(backup_path) if backup_path else None,
            "updated_config": updated_config,
        }

    def _create_backup(self) -> Path:
        """Create backup of original config file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.config_file_path.with_suffix(
            f".backup.{timestamp}{self.config_file_path.suffix}"
        )
        shutil.copy2(self.config_file_path, backup_path)
        return backup_path

    def _create_dataset_file(self, dataset: DatasetConfig, output_dir: Path) -> Path:
        """Create YAML file for a single dataset."""
        # Determine filename based on dataset identifier
        filename = self._generate_filename(dataset)
        file_path = output_dir / filename

        # Convert dataset to dict (excluding source_file)
        dataset_dict = dataset.model_dump(exclude={"source_file"}, exclude_none=True)

        # Write to file
        with open(file_path, "w") as f:
            yaml.dump(dataset_dict, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Created dataset file: {file_path}")
        return file_path

    def _generate_filename(self, dataset: DatasetConfig) -> str:
        """Generate filename for dataset config."""
        # Use table name if available, otherwise schema, otherwise database
        if dataset.table:
            return f"{dataset.table}.yml"
        elif dataset.schema_:
            return f"{dataset.schema_}_schema.yml"
        elif dataset.database:
            return f"{dataset.database}_database.yml"
        else:
            return f"dataset_{abs(hash(str(dataset.model_dump())))}.yml"

    def _update_config_file(self, datasets_dir: str) -> bool:
        """Update main config file to use directory-based config."""
        # Load original config as dict
        with open(self.config_file_path, "r") as f:
            if self.config_file_path.suffix in [".yaml", ".yml"]:
                config_dict = yaml.safe_load(f)
            else:
                config_dict = json.load(f)

        # Replace inline datasets with directory config
        config_dict["datasets"] = {
            "datasets_dir": datasets_dir,
            "auto_discover": True,
            "recursive": True,
        }

        # Write updated config
        with open(self.config_file_path, "w") as f:
            if self.config_file_path.suffix in [".yaml", ".yml"]:
                yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
            else:
                json.dump(config_dict, f, indent=2)

        return True
