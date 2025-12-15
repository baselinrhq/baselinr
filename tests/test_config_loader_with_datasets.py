"""
Integration tests for ConfigLoader with directory-based datasets.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from baselinr.config.loader import ConfigLoader
from baselinr.config.schema import BaselinrConfig, DatasetsConfig


class TestConfigLoaderWithDatasets:
    """Test ConfigLoader integration with directory-based datasets."""

    def test_load_config_with_directory_datasets(self, tmp_path):
        """Test loading config with directory-based dataset configs."""
        # Create datasets directory
        datasets_dir = tmp_path / "datasets"
        datasets_dir.mkdir()

        # Create dataset files
        (datasets_dir / "customers.yml").write_text(
            yaml.dump({"table": "customers", "schema": "public"})
        )
        (datasets_dir / "orders.yml").write_text(
            yaml.dump({"table": "orders", "schema": "public"})
        )

        # Create main config file
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "environment": "development",
                    "source": {
                        "type": "postgres",
                        "host": "localhost",
                        "port": 5432,
                        "database": "testdb",
                        "username": "user",
                        "password": "pass",
                    },
                    "storage": {
                        "connection": {
                            "type": "postgres",
                            "host": "localhost",
                            "port": 5432,
                            "database": "testdb",
                            "username": "user",
                            "password": "pass",
                        },
                        "results_table": "results",
                        "runs_table": "runs",
                    },
                    "datasets": {
                        "datasets_dir": "datasets",
                        "auto_discover": True,
                        "recursive": True,
                    },
                }
            )
        )

        # Load config
        config = ConfigLoader.load_from_file(str(config_file))

        # Verify datasets were loaded
        assert config.datasets is not None
        assert isinstance(config.datasets, DatasetsConfig)
        assert len(config.datasets.datasets) == 2

        # Verify dataset configs have source_file set
        assert all(d.source_file for d in config.datasets.datasets)
        assert any("customers.yml" in d.source_file for d in config.datasets.datasets)
        assert any("orders.yml" in d.source_file for d in config.datasets.datasets)

    def test_load_config_with_inline_datasets(self, tmp_path):
        """Test loading config with inline dataset configs (backward compatibility)."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "environment": "development",
                    "source": {
                        "type": "postgres",
                        "host": "localhost",
                        "port": 5432,
                        "database": "testdb",
                        "username": "user",
                        "password": "pass",
                    },
                    "storage": {
                        "connection": {
                            "type": "postgres",
                            "host": "localhost",
                            "port": 5432,
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

        # Load config
        config = ConfigLoader.load_from_file(str(config_file))

        # Verify datasets were loaded
        assert config.datasets is not None
        assert isinstance(config.datasets, DatasetsConfig)
        assert len(config.datasets.datasets) == 2

    def test_load_config_with_recursive_datasets(self, tmp_path):
        """Test loading config with recursive directory structure."""
        # Create nested datasets directory
        datasets_dir = tmp_path / "datasets"
        datasets_dir.mkdir()
        subdir = datasets_dir / "analytics"
        subdir.mkdir()

        # Create dataset files in nested structure
        (datasets_dir / "customers.yml").write_text(
            yaml.dump({"table": "customers", "schema": "public"})
        )
        (subdir / "events.yml").write_text(
            yaml.dump({"table": "events", "schema": "analytics"})
        )

        # Create main config file
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "environment": "development",
                    "source": {
                        "type": "postgres",
                        "host": "localhost",
                        "port": 5432,
                        "database": "testdb",
                        "username": "user",
                        "password": "pass",
                    },
                    "storage": {
                        "connection": {
                            "type": "postgres",
                            "host": "localhost",
                            "port": 5432,
                            "database": "testdb",
                            "username": "user",
                            "password": "pass",
                        },
                        "results_table": "results",
                        "runs_table": "runs",
                    },
                    "datasets": {
                        "datasets_dir": "datasets",
                        "recursive": True,
                    },
                }
            )
        )

        # Load config
        config = ConfigLoader.load_from_file(str(config_file))

        # Verify all datasets were loaded
        assert config.datasets is not None
        assert len(config.datasets.datasets) == 2

    def test_load_config_with_exclude_patterns(self, tmp_path):
        """Test loading config with exclude patterns."""
        datasets_dir = tmp_path / "datasets"
        datasets_dir.mkdir()

        # Create dataset files including backup
        (datasets_dir / "customers.yml").write_text(
            yaml.dump({"table": "customers", "schema": "public"})
        )
        (datasets_dir / "customers.backup.yml").write_text(
            yaml.dump({"table": "customers_old", "schema": "public"})
        )

        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "environment": "development",
                    "source": {
                        "type": "postgres",
                        "host": "localhost",
                        "port": 5432,
                        "database": "testdb",
                        "username": "user",
                        "password": "pass",
                    },
                    "storage": {
                        "connection": {
                            "type": "postgres",
                            "host": "localhost",
                            "port": 5432,
                            "database": "testdb",
                            "username": "user",
                            "password": "pass",
                        },
                        "results_table": "results",
                        "runs_table": "runs",
                    },
                    "datasets": {
                        "datasets_dir": "datasets",
                        "exclude_patterns": ["*.backup.yml"],
                    },
                }
            )
        )

        # Load config
        config = ConfigLoader.load_from_file(str(config_file))

        # Verify only non-backup file was loaded
        assert config.datasets is not None
        assert len(config.datasets.datasets) == 1
        assert config.datasets.datasets[0].table == "customers"
