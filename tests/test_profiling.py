"""Tests for profiling engine."""

from unittest.mock import MagicMock, Mock

import pytest

from baselinr.profiling.metrics import MetricCalculator


def test_is_numeric_type():
    """Test numeric type detection."""
    assert MetricCalculator._is_numeric_type("INTEGER")
    assert MetricCalculator._is_numeric_type("FLOAT")
    assert MetricCalculator._is_numeric_type("NUMERIC")
    assert MetricCalculator._is_numeric_type("DECIMAL(10,2)")
    assert not MetricCalculator._is_numeric_type("VARCHAR")
    assert not MetricCalculator._is_numeric_type("TEXT")


def test_is_string_type():
    """Test string type detection."""
    assert MetricCalculator._is_string_type("VARCHAR")
    assert MetricCalculator._is_string_type("TEXT")
    assert MetricCalculator._is_string_type("CHAR(10)")
    assert not MetricCalculator._is_string_type("INTEGER")
    assert not MetricCalculator._is_string_type("FLOAT")


def test_metric_filtering():
    """Test that enabled_metrics filters which metrics are computed."""
    engine = Mock()

    # Test with specific metrics enabled
    calculator = MetricCalculator(engine=engine, enabled_metrics=["count", "null_count", "mean"])

    assert calculator._should_compute_metric("count")
    assert calculator._should_compute_metric("mean")
    assert not calculator._should_compute_metric("stddev")
    assert not calculator._should_compute_metric("histogram")

    # Test with None (all metrics enabled)
    calculator_all = MetricCalculator(engine=engine, enabled_metrics=None)
    assert calculator_all._should_compute_metric("count")
    assert calculator_all._should_compute_metric("stddev")
    assert calculator_all._should_compute_metric("histogram")


def test_metric_group_filtering():
    """Test metric group filtering."""
    engine = Mock()

    # Only count metrics
    calculator = MetricCalculator(engine=engine, enabled_metrics=["count", "null_count"])

    # Should compute counts group (has count and null_count)
    assert calculator._should_compute_metric_group(["count", "null_count", "distinct_count"])

    # Should not compute numeric group
    assert not calculator._should_compute_metric_group(["min", "max", "mean", "stddev"])


# Note: Full integration tests would require a test database
# These are just basic unit tests for utility functions
