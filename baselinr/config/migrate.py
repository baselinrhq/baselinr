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
        # Check if there's anything to migrate
        # Load raw config to check for things to migrate
        with open(self.config_file_path, "r") as f:
            if self.config_file_path.suffix in [".yaml", ".yml"]:
                raw_config = yaml.safe_load(f) or {}
            else:
                raw_config = json.load(f) or {}

        has_inline_datasets = (
            self.config.datasets
            and isinstance(self.config.datasets, DatasetsConfig)
            and self.config.datasets.datasets
        )
        has_validation_rules = (
            raw_config.get("validation")
            and isinstance(raw_config["validation"], dict)
            and raw_config["validation"].get("rules")
        )
        has_profiling_schemas = (
            raw_config.get("profiling")
            and isinstance(raw_config["profiling"], dict)
            and raw_config["profiling"].get("schemas")
        )
        has_profiling_databases = (
            raw_config.get("profiling")
            and isinstance(raw_config["profiling"], dict)
            and raw_config["profiling"].get("databases")
        )

        if not (
            has_inline_datasets
            or has_validation_rules
            or has_profiling_schemas
            or has_profiling_databases
        ):
            return {
                "migrated": False,
                "message": "No configs found to migrate",
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
        if has_inline_datasets and isinstance(self.config.datasets, DatasetsConfig):
            for dataset in self.config.datasets.datasets:
                file_path = self._create_dataset_file(dataset, datasets_path)
                files_created.append(str(file_path))

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

        # Migrate validation.rules[] if present
        if (
            raw_config.get("validation")
            and isinstance(raw_config["validation"], dict)
            and raw_config["validation"].get("rules")
        ):
            validation_files = self._migrate_validation_rules(
                datasets_path, raw_config["validation"]["rules"]
            )
            files_created.extend(validation_files)

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

        # Phase 3.5: Consolidate column configs into unified columns field
        dataset_dict = self._consolidate_column_configs(dataset_dict)

        # Write to file
        with open(file_path, "w") as f:
            yaml.dump(dataset_dict, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Created dataset file: {file_path}")
        return file_path

    def _consolidate_column_configs(self, dataset_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Consolidate column configs from profiling.columns, drift.columns, anomaly.columns.

        Consolidates into unified columns field.

        Args:
            dataset_dict: Dataset config dictionary

        Returns:
            Updated dataset dict with consolidated columns
        """
        # Collect all column configs from different locations
        columns_by_name: Dict[str, Dict[str, Any]] = {}

        # Collect from profiling.columns
        if "profiling" in dataset_dict and isinstance(dataset_dict["profiling"], dict):
            profiling_cols = dataset_dict["profiling"].get("columns", [])
            for col in profiling_cols:
                col_name = col.get("name")
                if col_name:
                    if col_name not in columns_by_name:
                        columns_by_name[col_name] = {"name": col_name}
                    # Merge profiling, drift, anomaly configs from this column
                    if "profiling" in col:
                        columns_by_name[col_name]["profiling"] = col["profiling"]
                    if "drift" in col:
                        columns_by_name[col_name]["drift"] = col["drift"]
                    if "anomaly" in col:
                        columns_by_name[col_name]["anomaly"] = col["anomaly"]
                    if "pattern_type" in col:
                        columns_by_name[col_name]["pattern_type"] = col["pattern_type"]
                    if "metrics" in col:
                        columns_by_name[col_name]["metrics"] = col["metrics"]

        # Collect from drift.columns
        if "drift" in dataset_dict and isinstance(dataset_dict["drift"], dict):
            drift_cols = dataset_dict["drift"].get("columns", [])
            for col in drift_cols:
                col_name = col.get("name")
                if col_name:
                    if col_name not in columns_by_name:
                        columns_by_name[col_name] = {"name": col_name}
                    # Merge drift config
                    if "drift" in col:
                        columns_by_name[col_name]["drift"] = col["drift"]
                    if "pattern_type" in col:
                        columns_by_name[col_name]["pattern_type"] = col.get("pattern_type")

        # Collect from anomaly.columns
        if "anomaly" in dataset_dict and isinstance(dataset_dict["anomaly"], dict):
            anomaly_cols = dataset_dict["anomaly"].get("columns", [])
            for col in anomaly_cols:
                col_name = col.get("name")
                if col_name:
                    if col_name not in columns_by_name:
                        columns_by_name[col_name] = {"name": col_name}
                    # Merge anomaly config
                    if "anomaly" in col:
                        columns_by_name[col_name]["anomaly"] = col["anomaly"]
                    if "pattern_type" in col:
                        columns_by_name[col_name]["pattern_type"] = col.get("pattern_type")

        # Collect column-specific validation rules from validation.rules
        if "validation" in dataset_dict and isinstance(dataset_dict["validation"], dict):
            validation_rules = dataset_dict["validation"].get("rules", [])
            for rule in validation_rules:
                rule_col = rule.get("column")
                if rule_col:
                    if rule_col not in columns_by_name:
                        columns_by_name[rule_col] = {"name": rule_col}
                    # Add validation config if not exists
                    if "validation" not in columns_by_name[rule_col]:
                        columns_by_name[rule_col]["validation"] = {"rules": []}
                    columns_by_name[rule_col]["validation"]["rules"].append(rule)

        # If we have consolidated columns, add them to top-level and remove from nested locations
        if columns_by_name:
            dataset_dict["columns"] = list(columns_by_name.values())

            # Remove columns from nested locations (keep other fields)
            if "profiling" in dataset_dict and isinstance(dataset_dict["profiling"], dict):
                if "columns" in dataset_dict["profiling"]:
                    del dataset_dict["profiling"]["columns"]
            if "drift" in dataset_dict and isinstance(dataset_dict["drift"], dict):
                if "columns" in dataset_dict["drift"]:
                    del dataset_dict["drift"]["columns"]
            if "anomaly" in dataset_dict and isinstance(dataset_dict["anomaly"], dict):
                if "columns" in dataset_dict["anomaly"]:
                    del dataset_dict["anomaly"]["columns"]

            # Remove column-specific rules from validation.rules (keep table-level rules)
            if "validation" in dataset_dict and isinstance(dataset_dict["validation"], dict):
                if "rules" in dataset_dict["validation"]:
                    # Keep only table-level rules (rules without column)
                    table_level_rules = [
                        rule
                        for rule in dataset_dict["validation"]["rules"]
                        if not rule.get("column")
                    ]
                    dataset_dict["validation"]["rules"] = table_level_rules

        return dataset_dict

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

        # Remove validation.rules[] if present (migrated to datasets)
        if "validation" in config_dict and isinstance(config_dict["validation"], dict):
            if "rules" in config_dict["validation"]:
                # Remove the rules list entirely - rules are now in datasets section
                del config_dict["validation"]["rules"]
                logger.info(
                    "validation.rules[] migrated to datasets section and removed from config."
                )

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

    def _migrate_validation_rules(
        self, output_dir: Path, validation_rules: list[dict]
    ) -> list[str]:
        """Migrate validation.rules[] to dataset files.

        Groups rules by table and creates dataset files for each table.
        Global rules (without table) go into _global.yml.

        Args:
            output_dir: Directory to create validation rule files
            validation_rules: List of validation rule dicts from raw YAML

        Returns:
            List of created file paths
        """
        if not validation_rules:
            return []

        files_created = []
        # Group rules by table
        rules_by_table: Dict[str, list[dict]] = {}
        global_rules: list[dict] = []

        for rule_dict in validation_rules:
            table = rule_dict.get("table")
            if not table:
                global_rules.append(rule_dict)
            else:
                if table not in rules_by_table:
                    rules_by_table[table] = []
                rules_by_table[table].append(rule_dict)

        # Create dataset file for global rules
        if global_rules:
            global_dataset_dict = {"validation": {"rules": global_rules}}
            global_file_path = output_dir / "_global.yml"
            with open(global_file_path, "w") as f:
                yaml.dump(global_dataset_dict, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Created global validation rules file: {global_file_path}")
            files_created.append(str(global_file_path))

        # Create dataset files for table-specific rules
        # Phase 3.5: Column-specific rules go into columns[].validation.rules
        for table, rules in rules_by_table.items():
            dataset_dict: Dict[str, Any] = {"table": table}
            columns_by_name: Dict[str, Dict[str, Any]] = {}
            table_level_rules: list[dict] = []

            # Separate column-specific rules from table-level rules
            for rule_dict in rules:
                column = rule_dict.get("column")
                if column:
                    # Column-specific rule - add to columns[].validation.rules
                    if column not in columns_by_name:
                        columns_by_name[column] = {"name": column, "validation": {"rules": []}}
                    columns_by_name[column]["validation"]["rules"].append(rule_dict)
                else:
                    # Table-level rule - keep in validation.rules
                    table_level_rules.append(rule_dict)

            # Add table-level rules if any
            if table_level_rules:
                dataset_dict["validation"] = {"rules": table_level_rules}

            # Add column configs if any
            if columns_by_name:
                dataset_dict["columns"] = list(columns_by_name.values())

            filename = f"{table}.yml"
            file_path = output_dir / filename

            # Check if file already exists (from dataset migration)
            if file_path.exists():
                # Merge validation rules into existing file
                with open(file_path, "r") as f:
                    existing_dict = yaml.safe_load(f) or {}

                # Merge table-level rules
                if table_level_rules:
                    if "validation" not in existing_dict:
                        existing_dict["validation"] = {}
                    if "rules" not in existing_dict["validation"]:
                        existing_dict["validation"]["rules"] = []
                    existing_dict["validation"]["rules"].extend(table_level_rules)

                # Merge column configs
                if columns_by_name:
                    if "columns" not in existing_dict:
                        existing_dict["columns"] = []
                    # Merge columns by name
                    existing_columns = {col.get("name"): col for col in existing_dict["columns"]}
                    for col_name, col_config in columns_by_name.items():
                        if col_name in existing_columns:
                            # Merge validation rules
                            if "validation" not in existing_columns[col_name]:
                                existing_columns[col_name]["validation"] = {"rules": []}
                            existing_columns[col_name]["validation"]["rules"].extend(
                                col_config["validation"]["rules"]
                            )
                        else:
                            existing_columns[col_name] = col_config
                    existing_dict["columns"] = list(existing_columns.values())

                dataset_dict = existing_dict

            # Write to file
            with open(file_path, "w") as f:
                yaml.dump(dataset_dict, f, default_flow_style=False, sort_keys=False)

            logger.info(f"Created/updated validation rules file: {file_path}")
            files_created.append(str(file_path))

        return files_created
