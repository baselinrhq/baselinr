"""
Unit tests for DatasetFileLoader.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from baselinr.config.dataset_loader import DatasetFileLoader
from baselinr.config.schema import DatasetsDirectoryConfig, DatasetConfig


class TestDatasetFileLoader:
    """Test DatasetFileLoader functionality."""

    def test_resolve_absolute_path(self):
        """Test resolving absolute paths."""
        loader = DatasetFileLoader()
        abs_path = Path("/absolute/path/to/datasets")
        resolved = loader._resolve_path(str(abs_path))
        # On Windows, absolute paths starting with / get converted to C:/...
        # So we check that it's absolute and ends with the same path
        assert resolved.is_absolute()
        assert resolved.name == abs_path.name

    def test_resolve_relative_path_with_config_file(self):
        """Test resolving relative paths relative to config file."""
        config_file = Path("/config/dir/config.yml")
        loader = DatasetFileLoader(config_file_path=config_file)
        resolved = loader._resolve_path("datasets")
        assert resolved == config_file.parent / "datasets"

    def test_resolve_relative_path_without_config_file(self):
        """Test resolving relative paths relative to cwd."""
        loader = DatasetFileLoader()
        resolved = loader._resolve_path("datasets")
        assert resolved == Path.cwd() / "datasets"

    def test_discover_files_simple(self, tmp_path):
        """Test discovering files with simple pattern."""
        # Create test files
        (tmp_path / "dataset1.yml").write_text("table: test1\n")
        (tmp_path / "dataset2.yml").write_text("table: test2\n")
        (tmp_path / "other.txt").write_text("not a yaml")

        config = DatasetsDirectoryConfig(
            datasets_dir=str(tmp_path), file_pattern="*.yml", recursive=False
        )
        loader = DatasetFileLoader()

        files = loader._discover_files(tmp_path, config)
        assert len(files) == 2
        assert all(f.suffix == ".yml" for f in files)

    def test_discover_files_recursive(self, tmp_path):
        """Test discovering files recursively."""
        # Create nested structure
        (tmp_path / "dataset1.yml").write_text("table: test1\n")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "dataset2.yml").write_text("table: test2\n")

        config = DatasetsDirectoryConfig(
            datasets_dir=str(tmp_path), file_pattern="*.yml", recursive=True
        )
        loader = DatasetFileLoader()

        files = loader._discover_files(tmp_path, config)
        assert len(files) == 2

    def test_discover_files_exclude_patterns(self, tmp_path):
        """Test excluding files with patterns."""
        (tmp_path / "dataset1.yml").write_text("table: test1\n")
        (tmp_path / "dataset1.backup.yml").write_text("table: test1\n")

        config = DatasetsDirectoryConfig(
            datasets_dir=str(tmp_path),
            file_pattern="*.yml",
            exclude_patterns=["*.backup.yml"],
        )
        loader = DatasetFileLoader()

        files = loader._discover_files(tmp_path, config)
        assert len(files) == 1
        assert "backup" not in str(files[0])

    def test_load_file_single_dataset(self, tmp_path):
        """Test loading a file with a single dataset."""
        file_path = tmp_path / "test.yml"
        file_path.write_text(
            yaml.dump(
                {
                    "table": "customers",
                    "schema": "public",
                    "profiling": {"partition": {"strategy": "latest"}},
                }
            )
        )

        config = DatasetsDirectoryConfig(datasets_dir=str(tmp_path))
        loader = DatasetFileLoader()

        datasets = loader._load_file(file_path, config)
        assert len(datasets) == 1
        assert datasets[0].table == "customers"
        assert datasets[0].schema_ == "public"
        assert datasets[0].source_file == str(file_path)

    def test_load_file_multiple_datasets_list(self, tmp_path):
        """Test loading a file with multiple datasets as list."""
        file_path = tmp_path / "test.yml"
        file_path.write_text(
            yaml.dump(
                [
                    {"table": "customers", "schema": "public"},
                    {"table": "orders", "schema": "public"},
                ]
            )
        )

        config = DatasetsDirectoryConfig(datasets_dir=str(tmp_path))
        loader = DatasetFileLoader()

        datasets = loader._load_file(file_path, config)
        assert len(datasets) == 2
        assert datasets[0].table == "customers"
        assert datasets[1].table == "orders"

    def test_load_file_multiple_datasets_dict(self, tmp_path):
        """Test loading a file with multiple datasets in dict."""
        file_path = tmp_path / "test.yml"
        file_path.write_text(
            yaml.dump(
                {
                    "datasets": [
                        {"table": "customers", "schema": "public"},
                        {"table": "orders", "schema": "public"},
                    ]
                }
            )
        )

        config = DatasetsDirectoryConfig(datasets_dir=str(tmp_path))
        loader = DatasetFileLoader()

        datasets = loader._load_file(file_path, config)
        assert len(datasets) == 2

    def test_load_from_directory(self, tmp_path):
        """Test loading all datasets from directory."""
        # Create multiple dataset files
        (tmp_path / "customers.yml").write_text(
            yaml.dump({"table": "customers", "schema": "public"})
        )
        (tmp_path / "orders.yml").write_text(
            yaml.dump({"table": "orders", "schema": "public"})
        )

        config = DatasetsDirectoryConfig(datasets_dir=str(tmp_path))
        loader = DatasetFileLoader()

        datasets = loader.load_from_directory(config)
        assert len(datasets) == 2
        assert all(d.source_file for d in datasets)

    def test_load_from_directory_nonexistent(self):
        """Test loading from non-existent directory."""
        config = DatasetsDirectoryConfig(datasets_dir="/nonexistent/path")
        loader = DatasetFileLoader()

        datasets = loader.load_from_directory(config)
        assert len(datasets) == 0

    def test_load_from_directory_not_directory(self, tmp_path):
        """Test error when path is not a directory."""
        file_path = tmp_path / "notadir"
        file_path.write_text("not a directory")

        config = DatasetsDirectoryConfig(datasets_dir=str(file_path))
        loader = DatasetFileLoader()

        with pytest.raises(ValueError, match="not a directory"):
            loader.load_from_directory(config)
