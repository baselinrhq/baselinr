"""Tests for profiling engine."""

import pytest
from unittest.mock import Mock, MagicMock

from profilemesh.profiling.metrics import MetricCalculator


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


# Note: Full integration tests would require a test database
# These are just basic unit tests for utility functions

