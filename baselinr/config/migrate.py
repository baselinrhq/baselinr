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

from .schema import (
    BaselinrConfig,
    DatasetConfig,
    DatasetsConfig,
)

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

        # Load raw config to check for profiling.schemas and profiling.databases
        with open(self.config_file_path, "r") as f:
            if self.config_file_path.suffix in [".yaml", ".yml"]:
                raw_config = yaml.safe_load(f)
            else:
                raw_config = json.load(f)

        # Migrate profiling.schemas if present
        if (
            raw_config.get("profiling")
            and isinstance(raw_config["profiling"], dict)
            and raw_config["profiling"].get("schemas")
        ):
            schema_files = self._migrate_schema_configs(
                datasets_path, raw_config["profiling"]["schemas"]
            )
            files_created.extend(schema_files)

        # Migrate profiling.databases if present
        if (
            raw_config.get("profiling")
            and isinstance(raw_config["profiling"], dict)
            and raw_config["profiling"].get("databases")
        ):
            database_files = self._migrate_database_configs(
                datasets_path, raw_config["profiling"]["databases"]
            )
            files_created.extend(database_files)

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

        # Remove profiling.schemas and profiling.databases if present
        if "profiling" in config_dict:
            if "schemas" in config_dict["profiling"]:
                del config_dict["profiling"]["schemas"]
            if "databases" in config_dict["profiling"]:
                del config_dict["profiling"]["databases"]

        # Write updated config
        with open(self.config_file_path, "w") as f:
            if self.config_file_path.suffix in [".yaml", ".yml"]:
                yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
            else:
                json.dump(config_dict, f, indent=2)

        return True

    def _migrate_schema_configs(self, output_dir: Path, schema_configs: list[dict]) -> list[str]:
        """Migrate profiling.schemas[] to dataset files.

        Args:
            output_dir: Directory to create schema config files
            schema_configs: List of schema config dicts from raw YAML

        Returns:
            List of created file paths
        """
        if not schema_configs:
            return []

        files_created = []
        for schema_config_dict in schema_configs:
            # Convert schema config dict to dataset dict
            dataset_dict = {
                "schema": schema_config_dict.get("schema") or schema_config_dict.get("schema_"),
            }
            if schema_config_dict.get("database"):
                dataset_dict["database"] = schema_config_dict["database"]

            # Add profiling config if present
            profiling_dict = {}
            if schema_config_dict.get("partition"):
                profiling_dict["partition"] = schema_config_dict["partition"]
            if schema_config_dict.get("sampling"):
                profiling_dict["sampling"] = schema_config_dict["sampling"]
            if schema_config_dict.get("columns"):
                profiling_dict["columns"] = schema_config_dict["columns"]
            if profiling_dict:
                dataset_dict["profiling"] = profiling_dict

            # Add filters if present
            if "profiling" not in dataset_dict:
                dataset_dict["profiling"] = {}
            profiling_section = dataset_dict["profiling"]
            assert isinstance(profiling_section, dict)
            if schema_config_dict.get("table_types"):
                profiling_section["table_types"] = schema_config_dict["table_types"]
            if schema_config_dict.get("min_rows"):
                profiling_section["min_rows"] = schema_config_dict["min_rows"]
            if schema_config_dict.get("max_rows"):
                profiling_section["max_rows"] = schema_config_dict["max_rows"]
            if schema_config_dict.get("required_columns"):
                profiling_section["required_columns"] = schema_config_dict["required_columns"]
            if schema_config_dict.get("modified_since_days"):
                profiling_section["modified_since_days"] = schema_config_dict["modified_since_days"]
            if schema_config_dict.get("exclude_patterns"):
                profiling_section["exclude_patterns"] = schema_config_dict["exclude_patterns"]

            # Generate filename
            schema_name = dataset_dict.get("schema") or "unknown"
            filename = f"{schema_name}_schema.yml"
            file_path = output_dir / filename

            # Write to file
            with open(file_path, "w") as f:
                yaml.dump(dataset_dict, f, default_flow_style=False, sort_keys=False)

            logger.info(f"Created schema config file: {file_path}")
            files_created.append(str(file_path))

        return files_created

    def _migrate_database_configs(
        self, output_dir: Path, database_configs: list[dict]
    ) -> list[str]:
        """Migrate profiling.databases[] to dataset files.

        Args:
            output_dir: Directory to create database config files
            database_configs: List of database config dicts from raw YAML

        Returns:
            List of created file paths
        """
        if not database_configs:
            return []

        files_created = []
        for database_config_dict in database_configs:
            # Convert database config dict to dataset dict
            dataset_dict = {
                "database": database_config_dict.get("database"),
            }

            # Add profiling config if present
            profiling_dict = {}
            if database_config_dict.get("partition"):
                profiling_dict["partition"] = database_config_dict["partition"]
            if database_config_dict.get("sampling"):
                profiling_dict["sampling"] = database_config_dict["sampling"]
            if database_config_dict.get("columns"):
                profiling_dict["columns"] = database_config_dict["columns"]
            if profiling_dict:
                dataset_dict["profiling"] = profiling_dict

            # Add filters if present
            if "profiling" not in dataset_dict:
                dataset_dict["profiling"] = {}
            profiling_section = dataset_dict["profiling"]
            assert isinstance(profiling_section, dict)
            if database_config_dict.get("table_types"):
                profiling_section["table_types"] = database_config_dict["table_types"]
            if database_config_dict.get("min_rows"):
                profiling_section["min_rows"] = database_config_dict["min_rows"]
            if database_config_dict.get("max_rows"):
                profiling_section["max_rows"] = database_config_dict["max_rows"]
            if database_config_dict.get("required_columns"):
                profiling_section["required_columns"] = database_config_dict["required_columns"]
            if database_config_dict.get("modified_since_days"):
                profiling_section["modified_since_days"] = database_config_dict[
                    "modified_since_days"
                ]
            if database_config_dict.get("exclude_patterns"):
                profiling_section["exclude_patterns"] = database_config_dict["exclude_patterns"]

            # Generate filename
            database_name = dataset_dict.get("database") or "unknown"
            filename = f"{database_name}_database.yml"
            file_path = output_dir / filename

            # Write to file
            with open(file_path, "w") as f:
                yaml.dump(dataset_dict, f, default_flow_style=False, sort_keys=False)

            logger.info(f"Created database config file: {file_path}")
            files_created.append(str(file_path))

        return files_created
