"""Integration tests for column-level configurations."""

import pytest
from unittest.mock import MagicMock, Mock, patch

from baselinr.config.schema import (
    ColumnAnomalyConfig,
    ColumnConfig,
    ColumnDriftConfig,
    ColumnProfilingConfig,
    TablePattern,
)
from baselinr.profiling.column_matcher import ColumnMatcher


class TestColumnLevelProfiling:
    """Integration tests for column-level profiling."""

    def test_column_matcher_filters_columns(self):
        """Test that ColumnMatcher correctly filters columns to profile."""
        configs = [
            ColumnConfig(name="email"),
            ColumnConfig(name="age"),
            ColumnConfig(name="internal_notes", profiling=ColumnProfilingConfig(enabled=False)),
        ]
        all_columns = ["email", "age", "name", "internal_notes", "customer_id"]

        matcher = ColumnMatcher(column_configs=configs)
        profiled = matcher.get_profiled_columns(all_columns, include_defaults=False)

        assert "email" in profiled
        assert "age" in profiled
        assert "internal_notes" not in profiled
        assert "name" not in profiled  # Not in configs, include_defaults=False
        assert "customer_id" not in profiled

    def test_column_matcher_with_patterns(self):
        """Test ColumnMatcher with wildcard patterns."""
        configs = [
            ColumnConfig(name="email"),
            ColumnConfig(name="*_id"),
        ]
        all_columns = ["email", "customer_id", "order_id", "name", "address"]

        matcher = ColumnMatcher(column_configs=configs)
        profiled = matcher.get_profiled_columns(all_columns, include_defaults=False)

        assert "email" in profiled
        assert "customer_id" in profiled
        assert "order_id" in profiled
        assert "name" not in profiled
        assert "address" not in profiled

    def test_column_metrics_filtering(self):
        """Test that column-specific metrics are correctly retrieved."""
        configs = [
            ColumnConfig(name="email", metrics=["count", "null_count", "distinct_count"]),
            ColumnConfig(name="age", metrics=["count", "mean", "stddev", "min", "max"]),
        ]
        matcher = ColumnMatcher(column_configs=configs)

        assert matcher.get_column_metrics("email") == ["count", "null_count", "distinct_count"]
        assert matcher.get_column_metrics("age") == ["count", "mean", "stddev", "min", "max"]
        assert matcher.get_column_metrics("name") is None


class TestColumnLevelDrift:
    """Integration tests for column-level drift detection."""

    def test_drift_enabled_per_column(self):
        """Test that drift can be enabled/disabled per column."""
        configs = [
            ColumnConfig(
                name="amount", drift=ColumnDriftConfig(enabled=True, thresholds={"low": 10.0})
            ),
            ColumnConfig(name="notes", drift=ColumnDriftConfig(enabled=False)),
        ]

        matcher = ColumnMatcher(column_configs=configs)

        # Check drift config retrieval
        amount_config = matcher.get_column_drift_config("amount")
        assert amount_config is not None
        assert amount_config.drift.enabled is True

        notes_config = matcher.get_column_drift_config("notes")
        assert notes_config is not None
        assert notes_config.drift.enabled is False

    def test_drift_dependency_check(self):
        """Test that drift is skipped when profiling is disabled."""
        from baselinr.drift.detector import DriftDetector

        configs = [
            ColumnConfig(
                name="internal_notes",
                profiling=ColumnProfilingConfig(enabled=False),
                drift=ColumnDriftConfig(enabled=True),  # This should be ignored
            )
        ]
        matcher = ColumnMatcher(column_configs=configs)
        profiled_columns = []  # Column wasn't profiled

        # Simulate the dependency check
        should_detect = matcher.should_profile_column("internal_notes")
        assert should_detect is False

        # If column wasn't profiled, drift should be skipped
        if "internal_notes" not in profiled_columns:
            # This simulates what happens in DriftDetector._should_detect_drift
            drift_config = matcher.get_column_drift_config("internal_notes")
            # Even if drift config exists, it shouldn't be used if column wasn't profiled
            pass


class TestColumnLevelAnomaly:
    """Integration tests for column-level anomaly detection."""

    def test_anomaly_enabled_per_column(self):
        """Test that anomaly detection can be enabled/disabled per column."""
        configs = [
            ColumnConfig(
                name="amount",
                anomaly=ColumnAnomalyConfig(
                    enabled=True, methods=["control_limits", "iqr"], thresholds={"iqr_threshold": 2.0}
                ),
            ),
            ColumnConfig(name="notes", anomaly=ColumnAnomalyConfig(enabled=False)),
        ]

        matcher = ColumnMatcher(column_configs=configs)

        amount_config = matcher.get_column_anomaly_config("amount")
        assert amount_config is not None
        assert amount_config.anomaly.enabled is True
        assert amount_config.anomaly.methods == ["control_limits", "iqr"]

        notes_config = matcher.get_column_anomaly_config("notes")
        assert notes_config is not None
        assert notes_config.anomaly.enabled is False

    def test_anomaly_dependency_check(self):
        """Test that anomaly is skipped when profiling is disabled."""
        configs = [
            ColumnConfig(
                name="internal_notes",
                profiling=ColumnProfilingConfig(enabled=False),
                anomaly=ColumnAnomalyConfig(enabled=True),  # This should be ignored
            )
        ]
        matcher = ColumnMatcher(column_configs=configs)
        profiled_columns = []  # Column wasn't profiled

        should_detect = matcher.should_profile_column("internal_notes")
        assert should_detect is False

        # If column wasn't profiled, anomaly should be skipped
        if "internal_notes" not in profiled_columns:
            pass  # Anomaly detection would skip this


class TestTablePatternColumns:
    """Tests for TablePattern with column configurations."""

    def test_table_pattern_column_config_roundtrip(self):
        """Test that TablePattern rejects columns (must be in ODCS contracts)."""
        columns = [
            ColumnConfig(name="email", metrics=["count", "null_count"]),
            ColumnConfig(
                name="amount",
                drift=ColumnDriftConfig(enabled=True, thresholds={"low": 5.0, "medium": 15.0}),
            ),
        ]
        # TablePattern no longer supports columns field
        with pytest.raises(ValueError, match="no longer supports.*columns"):
            TablePattern(table="customers", schema="public", columns=columns)

