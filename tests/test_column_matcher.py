"""Tests for column matcher utility."""

import pytest

from baselinr.config.schema import ColumnConfig
from baselinr.profiling.column_matcher import ColumnMatcher


class TestColumnMatcher:
    """Tests for ColumnMatcher."""

    def test_empty_configs(self):
        """Test matcher with no column configs (backward compatible)."""
        matcher = ColumnMatcher(column_configs=None)

        assert matcher.should_profile_column("email") is True
        assert matcher.should_profile_column("age") is True

    def test_exact_match(self):
        """Test exact column name matching."""
        configs = [ColumnConfig(name="email")]
        matcher = ColumnMatcher(column_configs=configs)

        assert matcher.matches("email", configs[0]) is True
        assert matcher.matches("age", configs[0]) is False

    def test_wildcard_match(self):
        """Test wildcard pattern matching."""
        configs = [ColumnConfig(name="*_id")]
        matcher = ColumnMatcher(column_configs=configs)

        assert matcher.matches("customer_id", configs[0]) is True
        assert matcher.matches("order_id", configs[0]) is True
        assert matcher.matches("email", configs[0]) is False
        assert matcher.matches("id_column", configs[0]) is False

    def test_regex_match(self):
        """Test regex pattern matching."""
        configs = [ColumnConfig(name="^email.*", pattern_type="regex")]
        matcher = ColumnMatcher(column_configs=configs)

        assert matcher.matches("email", configs[0]) is True
        assert matcher.matches("email_address", configs[0]) is True
        assert matcher.matches("user_email", configs[0]) is False  # Regex ^email requires start
        assert matcher.matches("age", configs[0]) is False

    def test_find_matching_config(self):
        """Test finding matching config for a column."""
        configs = [
            ColumnConfig(name="email"),
            ColumnConfig(name="*_id"),
            ColumnConfig(name="age"),
        ]
        matcher = ColumnMatcher(column_configs=configs)

        # Exact match
        match = matcher.find_matching_config("email")
        assert match is not None
        assert match.name == "email"

        # Pattern match
        match = matcher.find_matching_config("customer_id")
        assert match is not None
        assert match.name == "*_id"

        # No match
        match = matcher.find_matching_config("unknown")
        assert match is None

    def test_get_profiled_columns_all(self):
        """Test getting profiled columns when all should be profiled."""
        all_columns = ["email", "age", "name", "customer_id"]
        matcher = ColumnMatcher(column_configs=None)

        profiled = matcher.get_profiled_columns(all_columns, include_defaults=True)
        assert profiled == set(all_columns)

    def test_get_profiled_columns_filtered(self):
        """Test getting profiled columns with filtering."""
        configs = [
            ColumnConfig(name="email"),
            ColumnConfig(name="age"),
        ]
        all_columns = ["email", "age", "name", "customer_id"]
        matcher = ColumnMatcher(column_configs=configs)

        profiled = matcher.get_profiled_columns(all_columns, include_defaults=False)
        assert profiled == {"email", "age"}

    def test_get_profiled_columns_with_patterns(self):
        """Test getting profiled columns with patterns."""
        configs = [
            ColumnConfig(name="email"),
            ColumnConfig(name="*_id"),
        ]
        all_columns = ["email", "customer_id", "order_id", "name"]
        matcher = ColumnMatcher(column_configs=configs)

        profiled = matcher.get_profiled_columns(all_columns, include_defaults=False)
        assert profiled == {"email", "customer_id", "order_id"}

    def test_get_profiled_columns_profiling_disabled(self):
        """Test getting profiled columns when profiling is disabled for some."""
        from baselinr.config.schema import ColumnProfilingConfig

        configs = [
            ColumnConfig(name="email"),
            ColumnConfig(name="internal_notes", profiling=ColumnProfilingConfig(enabled=False)),
        ]
        all_columns = ["email", "internal_notes", "name"]
        matcher = ColumnMatcher(column_configs=configs)

        profiled = matcher.get_profiled_columns(all_columns, include_defaults=False)
        assert profiled == {"email"}

    def test_get_column_metrics(self):
        """Test getting column-specific metrics."""
        configs = [
            ColumnConfig(name="email", metrics=["count", "null_count", "distinct_count"]),
            ColumnConfig(name="age", metrics=["count", "mean", "stddev"]),
        ]
        matcher = ColumnMatcher(column_configs=configs)

        assert matcher.get_column_metrics("email") == ["count", "null_count", "distinct_count"]
        assert matcher.get_column_metrics("age") == ["count", "mean", "stddev"]
        assert matcher.get_column_metrics("unknown") is None

    def test_get_column_drift_config(self):
        """Test getting column drift config."""
        from baselinr.config.schema import ColumnDriftConfig

        drift_config = ColumnDriftConfig(enabled=True, thresholds={"low": 5.0, "medium": 10.0})
        configs = [ColumnConfig(name="amount", drift=drift_config)]
        matcher = ColumnMatcher(column_configs=configs)

        match = matcher.get_column_drift_config("amount")
        assert match is not None
        assert match.drift is not None
        assert match.drift.enabled is True

        assert matcher.get_column_drift_config("unknown") is None

    def test_get_column_anomaly_config(self):
        """Test getting column anomaly config."""
        from baselinr.config.schema import ColumnAnomalyConfig

        anomaly_config = ColumnAnomalyConfig(enabled=True, methods=["control_limits", "iqr"])
        configs = [ColumnConfig(name="value", anomaly=anomaly_config)]
        matcher = ColumnMatcher(column_configs=configs)

        match = matcher.get_column_anomaly_config("value")
        assert match is not None
        assert match.anomaly is not None
        assert match.anomaly.enabled is True

        assert matcher.get_column_anomaly_config("unknown") is None

    def test_should_profile_column(self):
        """Test should_profile_column method."""
        from baselinr.config.schema import ColumnProfilingConfig

        configs = [
            ColumnConfig(name="email"),
            ColumnConfig(name="internal_notes", profiling=ColumnProfilingConfig(enabled=False)),
        ]
        matcher = ColumnMatcher(column_configs=configs)

        assert matcher.should_profile_column("email") is True
        assert matcher.should_profile_column("internal_notes") is False
        assert matcher.should_profile_column("unknown") is True  # Default: enabled

    def test_multiple_pattern_matches(self):
        """Test when multiple patterns match a column."""
        configs = [
            ColumnConfig(name="*_id"),
            ColumnConfig(name="customer_*"),
            ColumnConfig(name="customer_id"),  # More specific
        ]
        matcher = ColumnMatcher(column_configs=configs)

        # Should find at least one match
        match = matcher.find_matching_config("customer_id")
        assert match is not None

        # Should find all matches
        all_matches = matcher.find_all_matching_configs("customer_id")
        assert len(all_matches) >= 1

    def test_get_column_metrics(self):
        """Test getting column-specific metrics."""
        configs = [
            ColumnConfig(name="email", metrics=["count", "null_count", "distinct_count"]),
            ColumnConfig(name="age", metrics=["count", "mean", "stddev"]),
        ]
        matcher = ColumnMatcher(column_configs=configs)

        assert matcher.get_column_metrics("email") == ["count", "null_count", "distinct_count"]
        assert matcher.get_column_metrics("age") == ["count", "mean", "stddev"]
        assert matcher.get_column_metrics("unknown") is None

