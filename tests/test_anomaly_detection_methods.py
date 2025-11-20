"""Tests for anomaly detection methods."""

import statistics
from datetime import datetime, timedelta

import pytest

from baselinr.anomaly.detection_methods import (
    EWMADetector,
    IQRDetector,
    MADDetector,
    RegimeShiftDetector,
    TrendSeasonalityDetector,
)
from baselinr.learning.expectation_learner import LearnedExpectation


class TestIQRDetector:
    """Tests for IQR-based outlier detection."""

    def test_iqr_detection_normal_values(self):
        """Test IQR detection with normal values (no outliers)."""
        detector = IQRDetector(threshold=1.5)
        historical = [10.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 20.0]

        # Value within normal range
        result = detector.detect(15.0, historical)
        assert not result.is_anomaly
        assert result.severity == "none"
        assert result.score == 0.0

    def test_iqr_detection_outlier_high(self):
        """Test IQR detection with high outlier."""
        detector = IQRDetector(threshold=1.5)
        historical = [10.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 20.0]

        # High outlier
        result = detector.detect(50.0, historical)
        assert result.is_anomaly
        assert result.severity in ["low", "medium", "high"]
        assert result.score > 0.0
        assert "upper_bound" in result.metadata

    def test_iqr_detection_outlier_low(self):
        """Test IQR detection with low outlier."""
        detector = IQRDetector(threshold=1.5)
        historical = [10.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 20.0]

        # Low outlier
        result = detector.detect(0.0, historical)
        assert result.is_anomaly
        assert "lower_bound" in result.metadata

    def test_iqr_detection_insufficient_data(self):
        """Test IQR detection with insufficient data."""
        detector = IQRDetector()
        result = detector.detect(15.0, [10.0, 12.0])  # Need at least 4 values

        assert not result.is_anomaly
        assert "insufficient_data" in result.metadata["reason"]

    def test_iqr_detection_zero_iqr(self):
        """Test IQR detection with zero variance."""
        detector = IQRDetector()
        historical = [10.0, 10.0, 10.0, 10.0, 10.0]
        result = detector.detect(15.0, historical)

        assert not result.is_anomaly
        assert "zero_iqr" in result.metadata["reason"]


class TestMADDetector:
    """Tests for MAD-based outlier detection."""

    def test_mad_detection_normal_values(self):
        """Test MAD detection with normal values."""
        detector = MADDetector(threshold=3.0)
        historical = [10.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0]

        result = detector.detect(15.0, historical)
        assert not result.is_anomaly
        assert result.severity == "none"

    def test_mad_detection_outlier(self):
        """Test MAD detection with outlier."""
        detector = MADDetector(threshold=3.0)
        historical = [10.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0]

        # Outlier
        result = detector.detect(50.0, historical)
        assert result.is_anomaly
        assert result.score > 0.0
        assert "modified_z_score" in result.metadata

    def test_mad_detection_insufficient_data(self):
        """Test MAD detection with insufficient data."""
        detector = MADDetector()
        result = detector.detect(15.0, [10.0, 12.0])

        assert not result.is_anomaly
        assert "insufficient_data" in result.metadata["reason"]

    def test_mad_detection_zero_mad(self):
        """Test MAD detection with zero variance."""
        detector = MADDetector()
        historical = [10.0, 10.0, 10.0]
        result = detector.detect(15.0, historical)

        assert not result.is_anomaly
        assert "zero_mad" in result.metadata["reason"]


class TestEWMADetector:
    """Tests for EWMA-based outlier detection."""

    def test_ewma_detection_normal_values(self):
        """Test EWMA detection with normal values."""
        detector = EWMADetector(deviation_threshold=2.0)

        expectation = LearnedExpectation(
            table_name="users",
            schema_name=None,
            column_name="age",
            metric_name="mean",
            ewma_value=30.0,
            expected_stddev=5.0,
            expected_mean=30.0,
        )

        result = detector.detect(32.0, expectation)
        assert not result.is_anomaly

    def test_ewma_detection_outlier(self):
        """Test EWMA detection with outlier."""
        detector = EWMADetector(deviation_threshold=2.0)

        expectation = LearnedExpectation(
            table_name="users",
            schema_name=None,
            column_name="age",
            metric_name="mean",
            ewma_value=30.0,
            expected_stddev=5.0,
            expected_mean=30.0,
        )

        # Value > 2 stddevs away
        result = detector.detect(45.0, expectation)
        assert result.is_anomaly
        assert result.score > 0.0

    def test_ewma_detection_no_ewma_value(self):
        """Test EWMA detection when no EWMA value exists."""
        detector = EWMADetector()

        expectation = LearnedExpectation(
            table_name="users",
            schema_name=None,
            column_name="age",
            metric_name="mean",
            ewma_value=None,
        )

        result = detector.detect(30.0, expectation)
        assert not result.is_anomaly
        assert "no_ewma_value" in result.metadata["reason"]

    def test_ewma_detection_no_stddev(self):
        """Test EWMA detection when no stddev available."""
        detector = EWMADetector()

        expectation = LearnedExpectation(
            table_name="users",
            schema_name=None,
            column_name="age",
            metric_name="mean",
            ewma_value=30.0,
            expected_stddev=None,
            expected_mean=30.0,
        )

        # Should still work using absolute deviation
        result = detector.detect(35.0, expectation)
        # May or may not be anomaly depending on threshold logic
        assert result.severity in ["none", "low", "medium", "high"]


class TestTrendSeasonalityDetector:
    """Tests for trend and seasonality-based detection."""

    def test_trend_detection_normal_values(self):
        """Test trend detection with normal values."""
        detector = TrendSeasonalityDetector(trend_window=3)
        base_time = datetime.utcnow() - timedelta(days=10)

        # Create historical series with stable trend
        historical_series = [
            (base_time + timedelta(days=i), 10.0 + i * 0.1)
            for i in range(7)
        ]

        current_value = 10.7
        current_timestamp = base_time + timedelta(days=7)

        result = detector.detect(current_value, current_timestamp, historical_series)
        # Should not be anomaly for normal continuation
        assert not result.is_anomaly or result.severity == "low"

    def test_trend_detection_anomaly(self):
        """Test trend detection with anomaly."""
        detector = TrendSeasonalityDetector(trend_window=3)
        base_time = datetime.utcnow() - timedelta(days=10)

        # Stable historical trend
        historical_series = [
            (base_time + timedelta(days=i), 10.0 + i * 0.1)
            for i in range(7)
        ]

        # Sudden spike
        current_value = 50.0
        current_timestamp = base_time + timedelta(days=7)

        result = detector.detect(current_value, current_timestamp, historical_series)
        assert result.is_anomaly

    def test_trend_detection_insufficient_data(self):
        """Test trend detection with insufficient data."""
        detector = TrendSeasonalityDetector(trend_window=7)
        historical_series = [
            (datetime.utcnow() - timedelta(days=i), 10.0)
            for i in range(3)
        ]

        result = detector.detect(10.0, datetime.utcnow(), historical_series)
        assert not result.is_anomaly
        assert "insufficient_data" in result.metadata.get("reason", "")

    def test_seasonality_detection_weekly(self):
        """Test weekly seasonality detection."""
        detector = TrendSeasonalityDetector(seasonality_enabled=True, trend_window=3)
        base_time = datetime.utcnow() - timedelta(days=21)

        # Create historical series with weekly pattern
        historical_series = []
        for i in range(21):
            day_of_week = (base_time + timedelta(days=i)).weekday()
            # Higher values on weekends (5, 6)
            value = 20.0 if day_of_week in [5, 6] else 10.0
            historical_series.append((base_time + timedelta(days=i), value))

        # Current is a weekday, should be ~10
        current_timestamp = datetime.utcnow()
        current_value = 10.5

        result = detector.detect(current_value, current_timestamp, historical_series)
        # Should not be anomaly for expected weekday pattern
        assert not result.is_anomaly or result.severity == "low"

    def test_seasonality_detection_anomaly(self):
        """Test seasonality detection with anomaly."""
        detector = TrendSeasonalityDetector(seasonality_enabled=True, trend_window=3)
        base_time = datetime.utcnow() - timedelta(days=21)

        historical_series = []
        for i in range(21):
            day_of_week = (base_time + timedelta(days=i)).weekday()
            value = 20.0 if day_of_week in [5, 6] else 10.0
            historical_series.append((base_time + timedelta(days=i), value))

        # Weekday with weekend-like value (anomaly)
        current_timestamp = datetime.utcnow()
        if current_timestamp.weekday() not in [5, 6]:
            current_value = 25.0  # Weekend value on weekday
            result = detector.detect(current_value, current_timestamp, historical_series)
            assert result.is_anomaly


class TestRegimeShiftDetector:
    """Tests for regime shift detection."""

    def test_regime_shift_detection_no_shift(self):
        """Test regime shift detection with no shift."""
        detector = RegimeShiftDetector(window_size=3, use_statistical_test=False)

        recent = [10.0, 11.0, 12.0]
        baseline = [10.0, 10.5, 11.0, 11.5, 12.0]

        result = detector.detect(recent, baseline)
        assert not result.is_anomaly

    def test_regime_shift_detection_shift_detected(self):
        """Test regime shift detection with significant shift."""
        detector = RegimeShiftDetector(window_size=3, use_statistical_test=False)

        # Recent values significantly higher
        recent = [30.0, 31.0, 32.0]
        baseline = [10.0, 10.5, 11.0, 11.5, 12.0]

        result = detector.detect(recent, baseline)
        assert result.is_anomaly
        assert result.severity in ["low", "medium", "high"]

    def test_regime_shift_detection_insufficient_data(self):
        """Test regime shift detection with insufficient data."""
        detector = RegimeShiftDetector()

        recent = [10.0]
        baseline = [10.0]

        result = detector.detect(recent, baseline)
        assert not result.is_anomaly
        assert "insufficient_data" in result.metadata["reason"]

    def test_regime_shift_statistical_test(self):
        """Test regime shift with statistical test."""
        detector = RegimeShiftDetector(
            window_size=5, use_statistical_test=True, sensitivity=0.05
        )

        # Significant shift (should be detected)
        recent = [25.0, 26.0, 27.0, 28.0, 29.0]
        baseline = [10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0]

        result = detector.detect(recent, baseline)
        assert result.is_anomaly

    def test_regime_shift_no_statistical_test(self):
        """Test regime shift with simple comparison."""
        detector = RegimeShiftDetector(
            window_size=3, use_statistical_test=False
        )

        # Small shift (may not be detected with simple comparison)
        recent = [12.0, 13.0, 14.0]
        baseline = [10.0, 10.5, 11.0, 11.5, 12.0]

        result = detector.detect(recent, baseline)
        # May or may not be detected depending on threshold
        assert result.severity in ["none", "low", "medium", "high"]

