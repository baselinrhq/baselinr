"""
Tests for ConfigMigrator.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from baselinr.config.loader import ConfigLoader
from baselinr.config.migrate import ConfigMigrator
from baselinr.config.schema import BaselinrConfig, DatasetsConfig


class TestConfigMigrator:
    """Test ConfigMigrator functionality."""

    def test_migrate_single_dataset(self, tmp_path):
        """Test migrating a single dataset config."""
        # Create config file with inline dataset
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "environment": "development",
                    "source": {
                        "type": "postgres",
                        "host": "localhost",
                        "database": "testdb",
                        "username": "user",
                        "password": "pass",
                    },
                    "storage": {
                        "connection": {
                            "type": "postgres",
                            "host": "localhost",
                            "database": "testdb",
                            "username": "user",
                            "password": "pass",
                        },
                        "results_table": "results",
                        "runs_table": "runs",
                    },
                    "datasets": {
                        "datasets": [
                            {
                                "table": "customers",
                                "schema": "public",
                                "profiling": {"partition": {"strategy": "latest"}},
                            }
                        ]
                    },
                }
            )
        )

        # Load config
        config = ConfigLoader.load_from_file(str(config_file))

        # Migrate
        migrator = ConfigMigrator(config, config_file)
        result = migrator.migrate_to_directory(output_dir="datasets", create_backup=False)

        # Verify migration
        assert result["migrated"] is True
        assert len(result["files_created"]) == 1
        assert "customers.yml" in result["files_created"][0]

        # Verify dataset file was created
        dataset_file = tmp_path / "datasets" / "customers.yml"
        assert dataset_file.exists()

        # Verify config file was updated
        # After loading, ConfigLoader converts DatasetsDirectoryConfig to DatasetsConfig
        # So we check the raw YAML file instead
        with open(config_file, "r") as f:
            config_dict = yaml.safe_load(f)
        assert "datasets" in config_dict
        assert "datasets_dir" in config_dict["datasets"]
        assert config_dict["datasets"]["datasets_dir"] == "datasets"

    def test_migrate_multiple_datasets(self, tmp_path):
        """Test migrating multiple dataset configs."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "environment": "development",
                    "source": {
                        "type": "postgres",
                        "host": "localhost",
                        "database": "testdb",
                        "username": "user",
                        "password": "pass",
                    },
                    "storage": {
                        "connection": {
                            "type": "postgres",
                            "host": "localhost",
                            "database": "testdb",
                            "username": "user",
                            "password": "pass",
                        },
                        "results_table": "results",
                        "runs_table": "runs",
                    },
                    "datasets": {
                        "datasets": [
                            {"table": "customers", "schema": "public"},
                            {"table": "orders", "schema": "public"},
                        ]
                    },
                }
            )
        )

        config = ConfigLoader.load_from_file(str(config_file))
        migrator = ConfigMigrator(config, config_file)
        result = migrator.migrate_to_directory(output_dir="datasets", create_backup=False)

        assert result["migrated"] is True
        assert len(result["files_created"]) == 2

        # Verify both files exist
        assert (tmp_path / "datasets" / "customers.yml").exists()
        assert (tmp_path / "datasets" / "orders.yml").exists()

    def test_migrate_with_backup(self, tmp_path):
        """Test migration creates backup."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "environment": "development",
                    "source": {
                        "type": "postgres",
                        "host": "localhost",
                        "database": "testdb",
                        "username": "user",
                        "password": "pass",
                    },
                    "storage": {
                        "connection": {
                            "type": "postgres",
                            "host": "localhost",
                            "database": "testdb",
                            "username": "user",
                            "password": "pass",
                        },
                        "results_table": "results",
                        "runs_table": "runs",
                    },
                    "datasets": {
                        "datasets": [{"table": "customers", "schema": "public"}]
                    },
                }
            )
        )

        config = ConfigLoader.load_from_file(str(config_file))
        migrator = ConfigMigrator(config, config_file)
        result = migrator.migrate_to_directory(output_dir="datasets", create_backup=True)

        assert result["migrated"] is True
        assert result["backup_path"] is not None
        assert Path(result["backup_path"]).exists()

    def test_migrate_no_datasets(self, tmp_path):
        """Test migration with no datasets."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "environment": "development",
                    "source": {
                        "type": "postgres",
                        "host": "localhost",
                        "database": "testdb",
                        "username": "user",
                        "password": "pass",
                    },
                    "storage": {
                        "connection": {
                            "type": "postgres",
                            "host": "localhost",
                            "database": "testdb",
                            "username": "user",
                            "password": "pass",
                        },
                        "results_table": "results",
                        "runs_table": "runs",
                    },
                }
            )
        )

        config = ConfigLoader.load_from_file(str(config_file))
        migrator = ConfigMigrator(config, config_file)
        result = migrator.migrate_to_directory(output_dir="datasets", create_backup=False)

        assert result["migrated"] is False
        assert "No configs found to migrate" in result["message"]

    def test_generate_filename_table(self):
        """Test filename generation for table-level config."""
        from baselinr.config.schema import DatasetConfig

        dataset = DatasetConfig(table="customers", schema="public")
        migrator = ConfigMigrator(None, Path("/tmp/config.yml"))
        filename = migrator._generate_filename(dataset)
        assert filename == "customers.yml"

    def test_generate_filename_schema(self):
        """Test filename generation for schema-level config."""
        from baselinr.config.schema import DatasetConfig

        dataset = DatasetConfig(schema="public")
        migrator = ConfigMigrator(None, Path("/tmp/config.yml"))
        filename = migrator._generate_filename(dataset)
        assert filename == "public_schema.yml"

    def test_generate_filename_database(self):
        """Test filename generation for database-level config."""
        from baselinr.config.schema import DatasetConfig

        dataset = DatasetConfig(database="warehouse")
        migrator = ConfigMigrator(None, Path("/tmp/config.yml"))
        filename = migrator._generate_filename(dataset)
        assert filename == "warehouse_database.yml"

    def test_migrate_validation_rules(self, tmp_path):
        """Test migrating validation.rules[] to datasets section."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "environment": "development",
                    "source": {
                        "type": "postgres",
                        "host": "localhost",
                        "database": "testdb",
                        "username": "user",
                        "password": "pass",
                    },
                    "storage": {
                        "connection": {
                            "type": "postgres",
                            "host": "localhost",
                            "database": "testdb",
                            "username": "user",
                            "password": "pass",
                        },
                        "results_table": "results",
                        "runs_table": "runs",
                    },
                    "validation": {
                        "enabled": True,
                        "rules": [
                            {
                                "table": "customers",
                                "column": "email",
                                "type": "format",
                                "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
                                "severity": "high",
                            },
                            {
                                "table": "orders",
                                "column": "total_amount",
                                "type": "range",
                                "min": 0,
                                "max": 1000000,
                                "severity": "medium",
                            },
                        ],
                    },
                }
            )
        )

        config = ConfigLoader.load_from_file(str(config_file))
        migrator = ConfigMigrator(config, config_file)
        result = migrator.migrate_to_directory(output_dir="datasets", create_backup=False)

        # Should create dataset files for validation rules
        assert result["migrated"] is True
        assert len(result["files_created"]) >= 2  # At least customers.yml and orders.yml

        # Verify validation rules were migrated to dataset files
        customers_file = tmp_path / "datasets" / "customers.yml"
        orders_file = tmp_path / "datasets" / "orders.yml"
        
        assert customers_file.exists()
        assert orders_file.exists()

        # Verify customers.yml has validation rules in columns[].validation.rules (Phase 3.5)
        with open(customers_file, "r") as f:
            customers_config = yaml.safe_load(f)
        assert "columns" in customers_config
        email_col = next((col for col in customers_config["columns"] if col["name"] == "email"), None)
        assert email_col is not None
        assert "validation" in email_col
        assert "rules" in email_col["validation"]
        assert len(email_col["validation"]["rules"]) == 1
        assert email_col["validation"]["rules"][0]["type"] == "format"

        # Verify orders.yml has validation rules in columns[].validation.rules (Phase 3.5)
        with open(orders_file, "r") as f:
            orders_config = yaml.safe_load(f)
        assert "columns" in orders_config
        total_amount_col = next((col for col in orders_config["columns"] if col["name"] == "total_amount"), None)
        assert total_amount_col is not None
        assert "validation" in total_amount_col
        assert "rules" in total_amount_col["validation"]
        assert len(total_amount_col["validation"]["rules"]) == 1
        assert total_amount_col["validation"]["rules"][0]["type"] == "range"

        # Verify validation.rules[] was removed from main config
        with open(config_file, "r") as f:
            config_dict = yaml.safe_load(f)
        assert "validation" in config_dict
        # validation.rules[] should be removed (not present or empty)
        assert "rules" not in config_dict["validation"] or len(config_dict["validation"].get("rules", [])) == 0
