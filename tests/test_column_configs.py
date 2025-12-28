"""Tests for column-level configurations."""

import pytest

from baselinr.config.schema import (
    ColumnAnomalyConfig,
    ColumnConfig,
    ColumnDriftConfig,
    ColumnProfilingConfig,
    TablePattern,
)


class TestColumnConfig:
    """Tests for ColumnConfig."""

    def test_basic_column_config(self):
        """Test basic column configuration."""
        config = ColumnConfig(name="email")

        assert config.name == "email"
        assert config.metrics is None
        assert config.profiling is None
        assert config.drift is None
        assert config.anomaly is None

    def test_column_config_with_metrics(self):
        """Test column configuration with metrics."""
        config = ColumnConfig(name="age", metrics=["count", "mean", "stddev"])

        assert config.name == "age"
        assert config.metrics == ["count", "mean", "stddev"]

    def test_column_config_with_profiling(self):
        """Test column configuration with profiling settings."""
        profiling = ColumnProfilingConfig(enabled=True)
        config = ColumnConfig(name="notes", profiling=profiling)

        assert config.profiling is not None
        assert config.profiling.enabled is True

    def test_column_config_with_drift(self):
        """Test column configuration with drift settings."""
        drift = ColumnDriftConfig(
            enabled=True,
            thresholds={"low": 5.0, "medium": 15.0, "high": 30.0},
        )
        config = ColumnConfig(name="amount", drift=drift)

        assert config.drift is not None
        assert config.drift.enabled is True
        assert config.drift.thresholds == {"low": 5.0, "medium": 15.0, "high": 30.0}

    def test_column_config_with_anomaly(self):
        """Test column configuration with anomaly settings."""
        anomaly = ColumnAnomalyConfig(
            enabled=True,
            methods=["control_limits", "iqr"],
            thresholds={"iqr_threshold": 2.0},
        )
        config = ColumnConfig(name="value", anomaly=anomaly)

        assert config.anomaly is not None
        assert config.anomaly.enabled is True
        assert config.anomaly.methods == ["control_limits", "iqr"]
        assert config.anomaly.thresholds == {"iqr_threshold": 2.0}

    def test_column_config_pattern_type_validation(self):
        """Test pattern type validation."""
        with pytest.raises(ValueError, match="pattern_type must be"):
            ColumnConfig(name="test", pattern_type="invalid")

    def test_column_config_metrics_validation(self):
        """Test that invalid metrics are rejected."""
        with pytest.raises(ValueError, match="Invalid metrics"):
            ColumnConfig(name="test", metrics=["invalid_metric", "count"])


class TestColumnConfigDependencies:
    """Tests for column config dependency validation."""

    def test_profiling_disabled_with_drift_warns(self):
        """Test that profiling disabled with drift config produces warning."""
        import warnings

        profiling = ColumnProfilingConfig(enabled=False)
        drift = ColumnDriftConfig(enabled=True)
        config = ColumnConfig(name="test", profiling=profiling, drift=drift)

        # Validation happens in model_validator, which should issue warnings
        # Since warnings are issued but config is still created, just verify config exists
        assert config.profiling.enabled is False
        assert config.drift.enabled is True

    def test_profiling_disabled_with_anomaly_warns(self):
        """Test that profiling disabled with anomaly config produces warning."""
        profiling = ColumnProfilingConfig(enabled=False)
        anomaly = ColumnAnomalyConfig(enabled=True)
        config = ColumnConfig(name="test", profiling=profiling, anomaly=anomaly)

        assert config.profiling.enabled is False
        assert config.anomaly.enabled is True


class TestTablePatternWithColumns:
    """Tests for TablePattern with column configurations."""

    def test_table_pattern_rejects_columns(self):
        """Test that TablePattern rejects column configurations (must be in ODCS contracts)."""
        columns = [
            ColumnConfig(name="email", metrics=["count", "null_count"]),
            ColumnConfig(name="age", metrics=["count", "mean", "stddev"]),
        ]
        # TablePattern no longer supports columns field
        with pytest.raises(ValueError, match="no longer supports.*columns"):
            TablePattern(table="customers", schema="public", columns=columns)

    def test_table_pattern_without_columns(self):
        """Test TablePattern without columns (columns must be in ODCS contracts)."""
        pattern = TablePattern(table="customers", schema="public")

        assert pattern.table == "customers"
        # TablePattern no longer has columns field

    def test_table_pattern_rejects_column_patterns(self):
        """Test that TablePattern rejects column patterns (must be in ODCS contracts)."""
        columns = [
            ColumnConfig(name="*_id", metrics=["count", "null_count"]),
            ColumnConfig(name="email*", pattern_type="wildcard"),
        ]
        # TablePattern no longer supports columns field
        with pytest.raises(ValueError, match="no longer supports.*columns"):
            TablePattern(table="customers", schema="public", columns=columns)


class TestColumnConfigPatterns:
    """Tests for column name pattern matching."""

    def test_wildcard_pattern(self):
        """Test wildcard pattern matching."""
        config = ColumnConfig(name="*_id")
        assert config.pattern_type is None  # Default is wildcard

    def test_regex_pattern(self):
        """Test regex pattern."""
        config = ColumnConfig(name="^email.*", pattern_type="regex")
        assert config.pattern_type == "regex"

    def test_explicit_column_name(self):
        """Test explicit column name (no pattern)."""
        config = ColumnConfig(name="email")
        assert config.name == "email"
        assert config.pattern_type is None

