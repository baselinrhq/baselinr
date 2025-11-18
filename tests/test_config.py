"""Tests for configuration module."""

import tempfile
from pathlib import Path

import pytest

from baselinr.config.loader import ConfigLoader
from baselinr.config.schema import (
    BaselinrConfig,
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
  results_table: baselinr_results
  runs_table: baselinr_runs

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
        BaselinrConfig(
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
    assert "null_ratio" in config.metrics
    assert "unique_ratio" in config.metrics
    assert "null_percent" not in config.metrics  # Old metric removed
    assert "distinct_percent" not in config.metrics  # Old metric removed


def test_baseline_config_default():
    """Test default baseline configuration."""
    from baselinr.config.schema import DriftDetectionConfig

    config = DriftDetectionConfig()

    assert config.baselines["strategy"] == "last_run"
    assert config.baselines["windows"]["moving_average"] == 7
    assert config.baselines["windows"]["prior_period"] == 7
    assert config.baselines["windows"]["min_runs"] == 3


def test_baseline_config_validation():
    """Test baseline configuration validation."""
    from baselinr.config.schema import DriftDetectionConfig

    # Valid strategies
    config = DriftDetectionConfig(baselines={"strategy": "auto"})
    assert config.baselines["strategy"] == "auto"

    config = DriftDetectionConfig(baselines={"strategy": "moving_average"})
    assert config.baselines["strategy"] == "moving_average"

    config = DriftDetectionConfig(baselines={"strategy": "prior_period"})
    assert config.baselines["strategy"] == "prior_period"

    # Invalid strategy
    with pytest.raises(ValueError, match="Baseline strategy must be one of"):
        DriftDetectionConfig(baselines={"strategy": "invalid_strategy"})

    # Invalid moving_average window
    with pytest.raises(ValueError, match="moving_average window must be at least 2"):
        DriftDetectionConfig(baselines={"windows": {"moving_average": 1}})

    # Invalid prior_period
    with pytest.raises(
        ValueError, match="prior_period must be 1 \\(day\\), 7 \\(week\\), or 30 \\(month\\)"
    ):
        DriftDetectionConfig(baselines={"windows": {"prior_period": 5}})

    # Invalid min_runs
    with pytest.raises(ValueError, match="min_runs must be at least 2"):
        DriftDetectionConfig(baselines={"windows": {"min_runs": 1}})


def test_baseline_config_custom_windows():
    """Test custom baseline window configuration."""
    from baselinr.config.schema import DriftDetectionConfig

    config = DriftDetectionConfig(
        baselines={
            "strategy": "moving_average",
            "windows": {
                "moving_average": 14,
                "prior_period": 30,
                "min_runs": 5,
            },
        }
    )

    assert config.baselines["strategy"] == "moving_average"
    assert config.baselines["windows"]["moving_average"] == 14
    assert config.baselines["windows"]["prior_period"] == 30
    assert config.baselines["windows"]["min_runs"] == 5
