"""
Anomaly detection methods.

Implements various statistical methods for detecting anomalies in metric values:
- IQR (Interquartile Range)
- MAD (Median Absolute Deviation)
- EWMA (Exponentially Weighted Moving Average)
- Trend/Seasonality decomposition
- Regime shift detection
"""

import logging
import math
import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple

from ..learning.expectation_learner import LearnedExpectation

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    """Result from a detection method."""

    is_anomaly: bool
    severity: str  # "low", "medium", "high"
    score: float  # Anomaly score (0-1 or deviation in stddevs)
    metadata: dict  # Additional context


class IQRDetector:
    """Detect anomalies using Interquartile Range (IQR) method."""

    def __init__(self, threshold: float = 1.5):
        """
        Initialize IQR detector.

        Args:
            threshold: IQR multiplier (default 1.5 for standard IQR)
        """
        self.threshold = threshold

    def detect(
        self,
        current_value: float,
        historical_values: List[float],
    ) -> DetectionResult:
        """
        Detect if current value is an outlier using IQR.

        Args:
            current_value: Current metric value to check
            historical_values: Historical values for comparison

        Returns:
            DetectionResult with anomaly status
        """
        if len(historical_values) < 4:
            # Need at least 4 values for Q1/Q3 calculation
            return DetectionResult(
                is_anomaly=False,
                severity="none",
                score=0.0,
                metadata={"reason": "insufficient_data"},
            )

        try:
            sorted_values = sorted(historical_values)
            n = len(sorted_values)

            # Calculate Q1 (25th percentile) and Q3 (75th percentile)
            q1_idx = (n - 1) * 0.25
            q3_idx = (n - 1) * 0.75

            # Handle fractional indices
            if q1_idx == int(q1_idx):
                q1 = sorted_values[int(q1_idx)]
            else:
                lower = sorted_values[int(q1_idx)]
                upper = sorted_values[int(q1_idx) + 1]
                q1 = lower + (upper - lower) * (q1_idx - int(q1_idx))

            if q3_idx == int(q3_idx):
                q3 = sorted_values[int(q3_idx)]
            else:
                lower = sorted_values[int(q3_idx)]
                upper = sorted_values[int(q3_idx) + 1]
                q3 = lower + (upper - lower) * (q3_idx - int(q3_idx))

            iqr = q3 - q1

            if iqr == 0:
                # No variance, can't detect outliers
                return DetectionResult(
                    is_anomaly=False,
                    severity="none",
                    score=0.0,
                    metadata={"reason": "zero_iqr", "q1": q1, "q3": q3},
                )

            lower_bound = q1 - self.threshold * iqr
            upper_bound = q3 + self.threshold * iqr

            is_outlier = current_value < lower_bound or current_value > upper_bound

            # Calculate severity based on distance from bounds
            if is_outlier:
                if current_value < lower_bound:
                    deviation = (lower_bound - current_value) / iqr if iqr > 0 else 0
                else:
                    deviation = (current_value - upper_bound) / iqr if iqr > 0 else 0

                # Normalize to 0-1 range for score
                score = min(deviation / self.threshold, 1.0)

                # Determine severity
                if deviation > 3 * self.threshold:
                    severity = "high"
                elif deviation > 2 * self.threshold:
                    severity = "medium"
                else:
                    severity = "low"
            else:
                score = 0.0
                severity = "none"

            return DetectionResult(
                is_anomaly=is_outlier,
                severity=severity,
                score=score,
                metadata={
                    "q1": q1,
                    "q3": q3,
                    "iqr": iqr,
                    "lower_bound": lower_bound,
                    "upper_bound": upper_bound,
                    "current_value": current_value,
                },
            )

        except Exception as e:
            logger.warning(f"IQR detection failed: {e}")
            return DetectionResult(
                is_anomaly=False,
                severity="none",
                score=0.0,
                metadata={"error": str(e)},
            )


class MADDetector:
    """Detect anomalies using Median Absolute Deviation (MAD) method."""

    def __init__(self, threshold: float = 3.0):
        """
        Initialize MAD detector.

        Args:
            threshold: Modified z-score threshold (default 3.0)
        """
        self.threshold = threshold

    def detect(
        self,
        current_value: float,
        historical_values: List[float],
    ) -> DetectionResult:
        """
        Detect if current value is an outlier using MAD.

        Args:
            current_value: Current metric value to check
            historical_values: Historical values for comparison

        Returns:
            DetectionResult with anomaly status
        """
        if len(historical_values) < 3:
            return DetectionResult(
                is_anomaly=False,
                severity="none",
                score=0.0,
                metadata={"reason": "insufficient_data"},
            )

        try:
            median = statistics.median(historical_values)

            # Calculate MAD = median(|x_i - median|)
            deviations = [abs(x - median) for x in historical_values]
            mad = statistics.median(deviations)

            if mad == 0:
                # No variance, can't detect outliers
                return DetectionResult(
                    is_anomaly=False,
                    severity="none",
                    score=0.0,
                    metadata={"reason": "zero_mad", "median": median},
                )

            # Modified z-score = 0.6745 * (value - median) / MAD
            # 0.6745 is a constant that makes MAD comparable to stddev for normal distributions
            modified_z_score = 0.6745 * (current_value - median) / mad
            abs_z_score = abs(modified_z_score)

            is_outlier = abs_z_score > self.threshold

            if is_outlier:
                # Normalize score to 0-1 range
                score = min(abs_z_score / self.threshold, 1.0)

                # Determine severity
                if abs_z_score > 3 * self.threshold:
                    severity = "high"
                elif abs_z_score > 2 * self.threshold:
                    severity = "medium"
                else:
                    severity = "low"
            else:
                score = 0.0
                severity = "none"

            return DetectionResult(
                is_anomaly=is_outlier,
                severity=severity,
                score=score,
                metadata={
                    "median": median,
                    "mad": mad,
                    "modified_z_score": modified_z_score,
                    "current_value": current_value,
                },
            )

        except Exception as e:
            logger.warning(f"MAD detection failed: {e}")
            return DetectionResult(
                is_anomaly=False,
                severity="none",
                score=0.0,
                metadata={"error": str(e)},
            )


class EWMADetector:
    """Detect anomalies using EWMA from learned expectations."""

    def __init__(self, deviation_threshold: float = 2.0):
        """
        Initialize EWMA detector.

        Args:
            deviation_threshold: Number of standard deviations for threshold
        """
        self.deviation_threshold = deviation_threshold

    def detect(
        self,
        current_value: float,
        expectation: LearnedExpectation,
    ) -> DetectionResult:
        """
        Detect if current value is an outlier using EWMA.

        Args:
            current_value: Current metric value to check
            expectation: LearnedExpectation with EWMA values

        Returns:
            DetectionResult with anomaly status
        """
        if expectation.ewma_value is None:
            return DetectionResult(
                is_anomaly=False,
                severity="none",
                score=0.0,
                metadata={"reason": "no_ewma_value"},
            )

        if expectation.expected_stddev is None or expectation.expected_stddev == 0:
            # Use a simple absolute deviation if no stddev available
            deviation = abs(current_value - expectation.ewma_value)
            mean_value = expectation.expected_mean or expectation.ewma_value

            # Use 5% of mean as threshold if no stddev
            threshold = abs(mean_value) * 0.05 if mean_value != 0 else 0.01

            is_outlier = deviation > threshold
            severity_score = deviation / threshold if threshold > 0 else 0

        else:
            # Calculate deviation in standard deviations
            deviation = current_value - expectation.ewma_value
            deviation_stddevs = abs(deviation) / expectation.expected_stddev

            is_outlier = deviation_stddevs > self.deviation_threshold
            severity_score = deviation_stddevs / self.deviation_threshold

        if is_outlier:
            # Normalize score to 0-1 range
            score = min(severity_score / self.deviation_threshold, 1.0)

            # Determine severity
            if severity_score > 3 * self.deviation_threshold:
                severity = "high"
            elif severity_score > 2 * self.deviation_threshold:
                severity = "medium"
            else:
                severity = "low"
        else:
            score = 0.0
            severity = "none"

        return DetectionResult(
            is_anomaly=is_outlier,
            severity=severity,
            score=score,
            metadata={
                "ewma_value": expectation.ewma_value,
                "expected_stddev": expectation.expected_stddev,
                "deviation": deviation if expectation.expected_stddev else abs(deviation),
                "current_value": current_value,
            },
        )


class TrendSeasonalityDetector:
    """Lightweight Prophet-style trend and seasonality detection."""

    def __init__(
        self,
        trend_window: int = 7,
        seasonality_enabled: bool = True,
        deviation_threshold: float = 2.0,
    ):
        """
        Initialize trend/seasonality detector.

        Args:
            trend_window: Window size for moving average trend extraction
            seasonality_enabled: Whether to detect seasonal patterns
            deviation_threshold: Number of stddevs for anomaly threshold
        """
        self.trend_window = trend_window
        self.seasonality_enabled = seasonality_enabled
        self.deviation_threshold = deviation_threshold

    def detect(
        self,
        current_value: float,
        current_timestamp: datetime,
        historical_series: List[Tuple[datetime, float]],
    ) -> DetectionResult:
        """
        Detect anomalies using trend and seasonality decomposition.

        Args:
            current_value: Current metric value to check
            current_timestamp: Timestamp of current value
            historical_series: List of (timestamp, value) tuples

        Returns:
            DetectionResult with anomaly status
        """
        if len(historical_series) < self.trend_window:
            return DetectionResult(
                is_anomaly=False,
                severity="none",
                score=0.0,
                metadata={"reason": "insufficient_data"},
            )

        try:
            # Sort by timestamp
            sorted_series = sorted(historical_series, key=lambda x: x[0])
            values = [v for _, v in sorted_series]
            timestamps = [t for t, _ in sorted_series]

            # Extract trend using simple moving average
            trend_values = self._extract_trend(values)

            # Calculate residuals (detrended values)
            residuals = [values[i] - trend_values[i] for i in range(len(values))]

            # Detect seasonality if enabled
            if self.seasonality_enabled:
                expected_residual = self._get_seasonal_expectation(
                    current_timestamp, timestamps, residuals
                )
            else:
                # Use mean of residuals as baseline
                expected_residual = statistics.mean(residuals)

            # Calculate residual stddev for threshold
            if len(residuals) > 1:
                residual_stddev = statistics.stdev(residuals)
            else:
                residual_stddev = abs(residuals[0]) if residuals else 0.01

            # Current residual (detrended value)
            current_trend = trend_values[-1] if trend_values else statistics.mean(values)
            current_residual = current_value - current_trend

            # Compare against seasonally-adjusted expected
            deviation = current_residual - expected_residual
            deviation_stddevs = abs(deviation) / residual_stddev if residual_stddev > 0 else 0

            is_anomaly = deviation_stddevs > self.deviation_threshold

            if is_anomaly:
                score = min(deviation_stddevs / self.deviation_threshold, 1.0)

                if deviation_stddevs > 3 * self.deviation_threshold:
                    severity = "high"
                elif deviation_stddevs > 2 * self.deviation_threshold:
                    severity = "medium"
                else:
                    severity = "low"
            else:
                score = 0.0
                severity = "none"

            return DetectionResult(
                is_anomaly=is_anomaly,
                severity=severity,
                score=score,
                metadata={
                    "current_trend": current_trend,
                    "current_residual": current_residual,
                    "expected_residual": expected_residual,
                    "deviation_stddevs": deviation_stddevs,
                    "trend_window": self.trend_window,
                },
            )

        except Exception as e:
            logger.warning(f"Trend/seasonality detection failed: {e}")
            return DetectionResult(
                is_anomaly=False,
                severity="none",
                score=0.0,
                metadata={"error": str(e)},
            )

    def _extract_trend(self, values: List[float]) -> List[float]:
        """Extract trend using simple moving average."""
        trend = []
        window = min(self.trend_window, len(values))

        for i in range(len(values)):
            start_idx = max(0, i - window + 1)
            window_values = values[start_idx : i + 1]
            trend.append(statistics.mean(window_values))

        return trend

    def _get_seasonal_expectation(
        self,
        current_timestamp: datetime,
        historical_timestamps: List[datetime],
        residuals: List[float],
    ) -> float:
        """Get expected residual based on seasonal patterns."""
        # Extract day of week for weekly seasonality
        current_dow = current_timestamp.weekday()

        # Find historical values for same day of week
        same_dow_values = []
        for i, ts in enumerate(historical_timestamps):
            if ts.weekday() == current_dow:
                same_dow_values.append(residuals[i])

        if len(same_dow_values) >= 3:
            # Use mean of same day-of-week residuals
            return statistics.mean(same_dow_values)

        # Fallback to overall mean
        return statistics.mean(residuals) if residuals else 0.0


class RegimeShiftDetector:
    """Detect sudden behavioral changes (regime shifts)."""

    def __init__(
        self,
        window_size: int = 3,
        sensitivity: float = 0.05,
        use_statistical_test: bool = True,
    ):
        """
        Initialize regime shift detector.

        Args:
            window_size: Number of recent runs to compare
            sensitivity: P-value threshold for statistical test
            use_statistical_test: Whether to use statistical test vs simple comparison
        """
        self.window_size = window_size
        self.sensitivity = sensitivity
        self.use_statistical_test = use_statistical_test

    def detect(
        self,
        recent_values: List[float],
        baseline_values: List[float],
    ) -> DetectionResult:
        """
        Detect regime shift by comparing recent vs baseline values.

        Args:
            recent_values: Recent metric values (last N runs)
            baseline_values: Historical baseline values

        Returns:
            DetectionResult with anomaly status
        """
        if len(recent_values) < 2 or len(baseline_values) < 2:
            return DetectionResult(
                is_anomaly=False,
                severity="none",
                score=0.0,
                metadata={"reason": "insufficient_data"},
            )

        try:
            recent_mean = statistics.mean(recent_values)
            baseline_mean = statistics.mean(baseline_values)

            if self.use_statistical_test:
                # Use two-sample t-test approximation
                # Simplified: compare means with pooled variance
                shift_detected = self._detect_statistical_shift(recent_values, baseline_values)
            else:
                # Simple comparison: check if mean shift > threshold * stddev
                baseline_stddev = (
                    statistics.stdev(baseline_values)
                    if len(baseline_values) > 1
                    else abs(baseline_mean) * 0.1
                )

                mean_shift = abs(recent_mean - baseline_mean)
                threshold = 2.0 * baseline_stddev  # 2 stddev threshold

                shift_detected = mean_shift > threshold

            if shift_detected:
                # Calculate shift magnitude
                baseline_stddev = (
                    statistics.stdev(baseline_values)
                    if len(baseline_values) > 1
                    else abs(baseline_mean) * 0.1
                )

                if baseline_stddev > 0:
                    shift_magnitude = abs(recent_mean - baseline_mean) / baseline_stddev
                else:
                    shift_magnitude = abs(recent_mean - baseline_mean) / (
                        abs(baseline_mean) + 1e-10
                    )

                score = min(shift_magnitude / 3.0, 1.0)  # Normalize to 0-1

                if shift_magnitude > 3.0:
                    severity = "high"
                elif shift_magnitude > 2.0:
                    severity = "medium"
                else:
                    severity = "low"
            else:
                score = 0.0
                severity = "none"

            return DetectionResult(
                is_anomaly=shift_detected,
                severity=severity,
                score=score,
                metadata={
                    "recent_mean": recent_mean,
                    "baseline_mean": baseline_mean,
                    "mean_shift": abs(recent_mean - baseline_mean),
                    "window_size": self.window_size,
                },
            )

        except Exception as e:
            logger.warning(f"Regime shift detection failed: {e}")
            return DetectionResult(
                is_anomaly=False,
                severity="none",
                score=0.0,
                metadata={"error": str(e)},
            )

    def _detect_statistical_shift(
        self, recent_values: List[float], baseline_values: List[float]
    ) -> bool:
        """Detect shift using simplified statistical test."""
        # Simplified two-sample t-test
        # For small samples, use Welch's t-test approximation

        recent_mean = statistics.mean(recent_values)
        baseline_mean = statistics.mean(baseline_values)

        recent_var = statistics.variance(recent_values) if len(recent_values) > 1 else 0
        baseline_var = statistics.variance(baseline_values) if len(baseline_values) > 1 else 0

        # Pooled standard error
        n1, n2 = len(recent_values), len(baseline_values)
        pooled_se = math.sqrt(recent_var / n1 + baseline_var / n2)

        if pooled_se == 0:
            # No variance, check absolute difference
            return abs(recent_mean - baseline_mean) > 0.01

        # t-statistic
        t_stat = abs(recent_mean - baseline_mean) / pooled_se

        # Approximate p-value (simplified, using normal approximation for large df)
        # For small samples, this is approximate
        # Critical t-value for significance level (sensitivity)
        # Using normal approximation: z = 1.96 for 0.05, 2.58 for 0.01
        if self.sensitivity == 0.05:
            critical_t = 1.96
        elif self.sensitivity == 0.01:
            critical_t = 2.58
        else:
            # Linear interpolation (rough approximation)
            critical_t = 1.96 + (2.58 - 1.96) * (0.05 - self.sensitivity) / 0.04

        # Simple heuristic: if t-stat > critical, significant shift
        return t_stat > critical_t
