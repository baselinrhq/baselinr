"""Tests for configuration module."""

import pytest
from pathlib import Path
import tempfile

from profilemesh.config.loader import ConfigLoader
from profilemesh.config.schema import (
    ProfileMeshConfig,
    ConnectionConfig,
    DatabaseType,
    ProfilingConfig,
)


def test_postgres_connection_config():
    """Test PostgreSQL connection configuration."""
    config = ConnectionConfig(
        type=DatabaseType.POSTGRES,
        host="localhost",
        port=5432,
        database="testdb",
        username="user",
        password="pass",
    )

    assert config.type == "postgres"
    assert config.host == "localhost"
    assert config.port == 5432
    assert config.database == "testdb"


def test_sqlite_connection_config():
    """Test SQLite connection configuration."""
    config = ConnectionConfig(type=DatabaseType.SQLITE, database="test.db", filepath="./test.db")

    assert config.type == "sqlite"
    assert config.filepath == "./test.db"


def test_config_loader_from_yaml():
    """Test loading configuration from YAML file."""
    yaml_content = """
environment: development

source:
  type: postgres
  host: localhost
  port: 5432
  database: testdb
  username: user
  password: pass

storage:
  connection:
    type: postgres
    host: localhost
    port: 5432
    database: testdb
    username: user
    password: pass
  results_table: profilemesh_results
  runs_table: profilemesh_runs

profiling:
  tables:
    - table: test_table
      sample_ratio: 1.0
"""

    # Create temporary YAML file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        config = ConfigLoader.load_from_file(temp_path)

        assert config.environment == "development"
        assert config.source.type == "postgres"
        assert config.source.host == "localhost"
        assert len(config.profiling.tables) == 1
        assert config.profiling.tables[0].table == "test_table"
    finally:
        Path(temp_path).unlink()


def test_config_validation():
    """Test configuration validation."""
    with pytest.raises(ValueError):
        # Invalid environment
        ProfileMeshConfig(
            environment="invalid",
            source=ConnectionConfig(type=DatabaseType.POSTGRES, database="test"),
            storage={"connection": {"type": "postgres", "database": "test"}},
            profiling=ProfilingConfig(),
        )


def test_default_profiling_config():
    """Test default profiling configuration."""
    config = ProfilingConfig()

    assert config.default_sample_ratio == 1.0
    assert config.max_distinct_values == 1000
    assert config.compute_histograms is True
    assert "count" in config.metrics
    assert "null_percent" in config.metrics
