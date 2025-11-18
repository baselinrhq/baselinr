"""
Statistical tests for advanced drift detection in Baselinr.

Provides pluggable statistical tests that can be selected and combined
based on column type and metric characteristics.
"""

import json
import logging
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from scipy import stats

    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("scipy not available. Some statistical tests will use approximations.")


@dataclass
class StatisticalTestResult:  # Renamed from TestResult to avoid pytest collection
    """Result of a statistical test for drift detection."""

    test_name: str
    score: float  # Test statistic score
    p_value: Optional[float] = None
    drift_detected: bool = False
    severity: str = "none"  # "none", "low", "medium", "high"
    metadata: Dict[str, Any] = field(default_factory=dict)


class StatisticalTest(ABC):
    """Abstract base class for statistical drift detection tests."""

    @abstractmethod
    def prepare(
        self, baseline_data: Any, current_data: Any, column_type: str, metric_name: str
    ) -> Tuple[Any, Any]:
        """
        Prepare data for statistical testing.

        Args:
            baseline_data: Baseline data (could be metric value, histogram, distribution, etc.)
            current_data: Current data to compare
            column_type: Data type of the column
            metric_name: Name of the metric being tested

        Returns:
            Tuple of (prepared_baseline, prepared_current) data
        """
        pass

    @abstractmethod
    def compare(self, baseline_data: Any, current_data: Any) -> StatisticalTestResult:
        """
        Run the statistical comparison.

        Args:
            baseline_data: Prepared baseline data
            current_data: Prepared current data

        Returns:
            StatisticalTestResult with test statistic, p-value, and drift detection
        """
        pass

    @abstractmethod
    def score(self, test_result: StatisticalTestResult) -> float:
        """
        Return the test statistic score.

        Args:
            test_result: Result from compare() method

        Returns:
            Test statistic score (higher = more drift)
        """
        pass

    @abstractmethod
    def is_drift(
        self,
        test_result: StatisticalTestResult,
        threshold: Optional[float] = None,
        sensitivity: str = "medium",
    ) -> bool:
        """
        Determine if drift is detected based on test result.

        Args:
            test_result: Result from compare() method
            threshold: Optional custom threshold
            sensitivity: Sensitivity level ("low", "medium", "high")

        Returns:
            True if drift detected, False otherwise
        """
        pass

    @abstractmethod
    def get_test_name(self) -> str:
        """Return the identifier name of this test."""
        pass

    @abstractmethod
    def supports_column_type(self, column_type: str) -> bool:
        """
        Check if this test supports the given column type.

        Args:
            column_type: Column data type (e.g., "integer", "varchar", "text")

        Returns:
            True if test supports this column type
        """
        pass

    @abstractmethod
    def supports_metric(self, metric_name: str) -> bool:
        """
        Check if this test supports the given metric.

        Args:
            metric_name: Name of the metric (e.g., "mean", "distinct_count")

        Returns:
            True if test supports this metric
        """
        pass

    def _get_sensitivity_threshold(self, default_threshold: float, sensitivity: str) -> float:
        """
        Adjust threshold based on sensitivity level.

        Args:
            default_threshold: Default threshold value
            sensitivity: Sensitivity level ("low", "medium", "high")

        Returns:
            Adjusted threshold
        """
        if sensitivity == "low":
            return default_threshold * 1.5  # Less sensitive (higher threshold)
        elif sensitivity == "high":
            return default_threshold * 0.5  # More sensitive (lower threshold)
        else:  # medium
            return default_threshold


# ============================================================================
# Numeric Column Tests
# ============================================================================


class KolmogorovSmirnovTest(StatisticalTest):
    """
    Kolmogorov-Smirnov test for distribution comparison.

    Compares the distribution of baseline vs current data.
    Good for detecting shape changes (skew, multimodality, heavy tails).
    """

    def __init__(self, alpha: float = 0.05):
        """
        Initialize KS test.

        Args:
            alpha: Significance level (default: 0.05)
        """
        self.alpha = alpha

    def prepare(
        self, baseline_data: Any, current_data: Any, column_type: str, metric_name: str
    ) -> Tuple[Any, Any]:
        """Prepare data for KS test."""
        # If histogram data is available, use it
        if isinstance(baseline_data, dict) and "histogram" in baseline_data:
            baseline_hist = baseline_data.get("histogram")
            current_hist = current_data.get("histogram") if isinstance(current_data, dict) else None

            if baseline_hist and current_hist:
                # Convert histogram to distribution samples
                baseline_dist = self._histogram_to_samples(baseline_hist)
                current_dist = self._histogram_to_samples(current_hist)
                return (baseline_dist, current_dist)

        # Fallback: approximate from summary statistics
        # This is less accurate but allows the test to run
        if isinstance(baseline_data, (int, float)) and isinstance(current_data, (int, float)):
            # Create synthetic distributions from mean/stddev if available
            baseline_mean = baseline_data
            current_mean = current_data

            # Try to get stddev from metadata if available
            baseline_std = (
                baseline_data.get("stddev", baseline_mean * 0.1)
                if isinstance(baseline_data, dict)
                else baseline_mean * 0.1
            )
            current_std = (
                current_data.get("stddev", current_mean * 0.1)
                if isinstance(current_data, dict)
                else current_mean * 0.1
            )

            # Generate synthetic samples (approximation)
            baseline_samples = self._generate_normal_samples(baseline_mean, baseline_std, n=1000)
            current_samples = self._generate_normal_samples(current_mean, current_std, n=1000)
            return (baseline_samples, current_samples)

        return (None, None)

    def compare(self, baseline_data: Any, current_data: Any) -> StatisticalTestResult:
        """Run KS test comparison."""
        if baseline_data is None or current_data is None:
            return StatisticalTestResult(
                test_name=self.get_test_name(),
                score=0.0,
                drift_detected=False,
                severity="none",
                metadata={"error": "Insufficient data for KS test"},
            )

        try:
            if SCIPY_AVAILABLE:
                # Use scipy's KS test
                statistic, p_value = stats.ks_2samp(baseline_data, current_data)
            else:
                # Manual KS test implementation (simplified)
                statistic, p_value = self._manual_ks_test(baseline_data, current_data)

            drift_detected = p_value < self.alpha if p_value is not None else False

            # Determine severity based on statistic and p-value
            if drift_detected:
                if statistic > 0.3 or (p_value and p_value < 0.001):
                    severity = "high"
                elif statistic > 0.2 or (p_value and p_value < 0.01):
                    severity = "medium"
                else:
                    severity = "low"
            else:
                severity = "none"

            return StatisticalTestResult(
                test_name=self.get_test_name(),
                score=statistic,
                p_value=p_value,
                drift_detected=drift_detected,
                severity=severity,
                metadata={"alpha": self.alpha, "statistic": statistic, "p_value": p_value},
            )
        except Exception as e:
            logger.warning(f"KS test failed: {e}")
            return StatisticalTestResult(
                test_name=self.get_test_name(),
                score=0.0,
                drift_detected=False,
                severity="none",
                metadata={"error": str(e)},
            )

    def score(self, test_result: StatisticalTestResult) -> float:
        """Return KS statistic score."""
        return test_result.score

    def is_drift(
        self,
        test_result: StatisticalTestResult,
        threshold: Optional[float] = None,
        sensitivity: str = "medium",
    ) -> bool:
        """Determine if drift detected."""
        if threshold is None:
            threshold = 0.2  # Default KS statistic threshold
        threshold = self._get_sensitivity_threshold(threshold, sensitivity)
        return test_result.score > threshold or test_result.drift_detected

    def get_test_name(self) -> str:
        """Return test name."""
        return "ks_test"

    def supports_column_type(self, column_type: str) -> bool:
        """KS test supports numeric columns."""
        numeric_types = [
            "integer",
            "int",
            "bigint",
            "smallint",
            "numeric",
            "decimal",
            "float",
            "double",
            "real",
            "number",
        ]
        return any(nt in column_type.lower() for nt in numeric_types)

    def supports_metric(self, metric_name: str) -> bool:
        """KS test supports distribution-based metrics."""
        return metric_name in ["mean", "histogram", "distribution"]

    def _histogram_to_samples(self, histogram: Any) -> List[float]:
        """Convert histogram to sample distribution."""
        if isinstance(histogram, str):
            try:
                histogram = json.loads(histogram)
            except Exception:
                return []

        if not isinstance(histogram, (list, dict)):
            return []

        samples = []
        if isinstance(histogram, list):
            # Assume list of [bin_center, count] pairs
            for item in histogram:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    bin_center, count = item[0], int(item[1])
                    samples.extend([bin_center] * count)
        elif isinstance(histogram, dict):
            # Assume dict of {bin: count}
            for bin_val, count in histogram.items():
                try:
                    bin_float = float(bin_val)
                    count_int = int(count)
                    samples.extend([bin_float] * count_int)
                except Exception:
                    continue

        return samples

    def _generate_normal_samples(self, mean: float, std: float, n: int = 1000) -> List[float]:
        """Generate synthetic normal distribution samples."""
        if SCIPY_AVAILABLE:
            return stats.norm.rvs(mean, std, size=n).tolist()  # type: ignore[no-any-return]
        else:
            # Simple approximation using Box-Muller transform
            import random

            samples = []
            for _ in range(n):
                u1, u2 = random.random(), random.random()
                z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
                samples.append(mean + std * z)
            return samples

    def _manual_ks_test(
        self, data1: List[float], data2: List[float]
    ) -> Tuple[float, Optional[float]]:
        """Manual KS test implementation (simplified)."""
        if not data1 or not data2:
            return (0.0, None)

        # Sort both datasets
        sorted1 = sorted(data1)
        sorted2 = sorted(data2)

        # Calculate empirical CDFs
        n1, n2 = len(sorted1), len(sorted2)
        all_values = sorted(set(sorted1 + sorted2))

        max_diff = 0.0
        for val in all_values:
            cdf1 = sum(1 for x in sorted1 if x <= val) / n1
            cdf2 = sum(1 for x in sorted2 if x <= val) / n2
            diff = abs(cdf1 - cdf2)
            if diff > max_diff:
                max_diff = diff

        # Approximate p-value (simplified)
        # In production, use proper KS test p-value calculation
        p_value = None  # Would need proper calculation

        return (max_diff, p_value)


class PopulationStabilityIndexTest(StatisticalTest):
    """
    Population Stability Index (PSI) for bucket-based drift detection.

    Good for monitoring slow drifts over long periods.
    PSI score interpretation:
    - < 0.1: No significant drift
    - 0.1-0.2: Minor drift
    - 0.2-0.5: Moderate drift
    - > 0.5: Significant drift
    """

    def __init__(self, buckets: int = 10, threshold: float = 0.2):
        """
        Initialize PSI test.

        Args:
            buckets: Number of buckets for distribution (default: 10)
            threshold: PSI threshold for drift detection (default: 0.2)
        """
        self.buckets = buckets
        self.threshold = threshold

    def prepare(
        self, baseline_data: Any, current_data: Any, column_type: str, metric_name: str
    ) -> Tuple[Any, Any]:
        """Prepare data for PSI test."""
        # PSI requires histogram/bucket data
        if isinstance(baseline_data, dict) and "histogram" in baseline_data:
            baseline_hist = baseline_data.get("histogram")
            current_hist = current_data.get("histogram") if isinstance(current_data, dict) else None

            if baseline_hist and current_hist:
                return (baseline_hist, current_hist)

        # Try to create buckets from min/max/mean if available
        if isinstance(baseline_data, dict) and isinstance(current_data, dict):
            baseline_min = baseline_data.get("min")
            baseline_max = baseline_data.get("max")
            current_min = current_data.get("min")
            current_max = current_data.get("max")

            if all(x is not None for x in [baseline_min, baseline_max, current_min, current_max]):
                # Ensure all values are floats
                try:
                    baseline_min_f: float = float(baseline_min)  # type: ignore[arg-type]
                    baseline_max_f: float = float(baseline_max)  # type: ignore[arg-type]
                    current_min_f: float = float(current_min)  # type: ignore[arg-type]
                    current_max_f: float = float(current_max)  # type: ignore[arg-type]
                except (ValueError, TypeError):
                    return (None, None)
                # Create synthetic buckets
                overall_min: float = min(baseline_min_f, current_min_f)
                overall_max: float = max(baseline_max_f, current_max_f)
                baseline_buckets = self._create_buckets_from_range(
                    baseline_min_f, baseline_max_f, overall_min, overall_max
                )
                current_buckets = self._create_buckets_from_range(
                    current_min_f, current_max_f, overall_min, overall_max
                )
                return (baseline_buckets, current_buckets)

        return (None, None)

    def compare(self, baseline_data: Any, current_data: Any) -> StatisticalTestResult:
        """Calculate PSI score."""
        if baseline_data is None or current_data is None:
            return StatisticalTestResult(
                test_name=self.get_test_name(),
                score=0.0,
                drift_detected=False,
                severity="none",
                metadata={"error": "Insufficient data for PSI test"},
            )

        try:
            # Convert to bucket distributions
            baseline_buckets = self._to_bucket_distribution(baseline_data)
            current_buckets = self._to_bucket_distribution(current_data)

            # Calculate PSI
            psi_score = self._calculate_psi(baseline_buckets, current_buckets)

            # Determine drift and severity
            drift_detected = psi_score > self.threshold
            if drift_detected:
                if psi_score > 0.5:
                    severity = "high"
                elif psi_score > 0.3:
                    severity = "medium"
                else:
                    severity = "low"
            else:
                severity = "none"

            return StatisticalTestResult(
                test_name=self.get_test_name(),
                score=psi_score,
                drift_detected=drift_detected,
                severity=severity,
                metadata={
                    "buckets": self.buckets,
                    "threshold": self.threshold,
                    "psi_score": psi_score,
                },
            )
        except Exception as e:
            logger.warning(f"PSI test failed: {e}")
            return StatisticalTestResult(
                test_name=self.get_test_name(),
                score=0.0,
                drift_detected=False,
                severity="none",
                metadata={"error": str(e)},
            )

    def score(self, test_result: StatisticalTestResult) -> float:
        """Return PSI score."""
        return test_result.score

    def is_drift(
        self,
        test_result: StatisticalTestResult,
        threshold: Optional[float] = None,
        sensitivity: str = "medium",
    ) -> bool:
        """Determine if drift detected."""
        if threshold is None:
            threshold = self.threshold
        threshold = self._get_sensitivity_threshold(threshold, sensitivity)
        return test_result.score > threshold

    def get_test_name(self) -> str:
        """Return test name."""
        return "psi"

    def supports_column_type(self, column_type: str) -> bool:
        """PSI test supports numeric columns."""
        numeric_types = [
            "integer",
            "int",
            "bigint",
            "smallint",
            "numeric",
            "decimal",
            "float",
            "double",
            "real",
            "number",
        ]
        return any(nt in column_type.lower() for nt in numeric_types)

    def supports_metric(self, metric_name: str) -> bool:
        """PSI test supports distribution-based metrics."""
        return metric_name in ["mean", "histogram", "distribution", "min", "max"]

    def _to_bucket_distribution(self, data: Any) -> Dict[int, float]:
        """Convert data to bucket distribution."""
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                return {}

        if isinstance(data, dict):
            # Already in bucket format
            return {int(k): float(v) for k, v in data.items()}
        elif isinstance(data, list):
            # Convert histogram list to buckets
            buckets = {}
            for i, count in enumerate(data):
                buckets[i] = float(count)
            return buckets

        return {}

    def _create_buckets_from_range(
        self, min_val: float, max_val: float, overall_min: float, overall_max: float
    ) -> Dict[int, float]:
        """Create synthetic bucket distribution from range."""
        bucket_width = (overall_max - overall_min) / self.buckets
        buckets = {}

        # Distribute data across buckets
        for i in range(self.buckets):
            bucket_start = overall_min + i * bucket_width
            bucket_end = overall_min + (i + 1) * bucket_width

            # Count how much of the range falls in this bucket
            range_start = max(min_val, bucket_start)
            range_end = min(max_val, bucket_end)

            if range_start < range_end:
                count = (
                    (range_end - range_start) / (max_val - min_val)
                    if max_val > min_val
                    else 1.0 / self.buckets
                )
                buckets[i] = count
            else:
                buckets[i] = 0.0

        return buckets

    def _calculate_psi(
        self, baseline_buckets: Dict[int, float], current_buckets: Dict[int, float]
    ) -> float:
        """Calculate Population Stability Index."""
        # Normalize distributions
        baseline_total = sum(baseline_buckets.values()) or 1.0
        current_total = sum(current_buckets.values()) or 1.0

        baseline_probs = {k: v / baseline_total for k, v in baseline_buckets.items()}
        current_probs = {k: v / current_total for k, v in current_buckets.items()}

        # Get all bucket keys
        all_buckets = set(baseline_probs.keys()) | set(current_probs.keys())

        # Calculate PSI
        psi = 0.0
        for bucket in all_buckets:
            baseline_p = baseline_probs.get(bucket, 0.0001)  # Avoid division by zero
            current_p = current_probs.get(bucket, 0.0001)

            if baseline_p > 0:
                psi += (current_p - baseline_p) * math.log(current_p / baseline_p)

        return psi


class ZScoreVarianceTest(StatisticalTest):
    """
    Z-score test for mean/variance shifts.

    Uses mean and stddev metrics to detect shifts from baseline distribution.
    """

    def __init__(self, z_threshold: float = 2.0):
        """
        Initialize Z-score test.

        Args:
            z_threshold: Z-score threshold (default: 2.0, i.e., 2 standard deviations)
        """
        self.z_threshold = z_threshold

    def prepare(
        self, baseline_data: Any, current_data: Any, column_type: str, metric_name: str
    ) -> Tuple[Any, Any]:
        """Prepare data for Z-score test."""
        # Z-score needs mean and stddev
        if isinstance(baseline_data, dict) and isinstance(current_data, dict):
            baseline_mean = baseline_data.get("mean")
            baseline_std = baseline_data.get("stddev")
            current_mean = current_data.get("mean")
            current_std = current_data.get("stddev")

            if all(x is not None for x in [baseline_mean, baseline_std, current_mean]):
                return (
                    {"mean": baseline_mean, "stddev": baseline_std},
                    {"mean": current_mean, "stddev": current_std},
                )

        # Fallback: use raw values as means, estimate stddev
        if isinstance(baseline_data, (int, float)) and isinstance(current_data, (int, float)):
            baseline_std = abs(baseline_data) * 0.1 if baseline_data != 0 else 1.0
            current_std = abs(current_data) * 0.1 if current_data != 0 else 1.0
            return (
                {"mean": baseline_data, "stddev": baseline_std},
                {"mean": current_data, "stddev": current_std},
            )

        return (None, None)

    def compare(self, baseline_data: Any, current_data: Any) -> StatisticalTestResult:
        """Calculate Z-score."""
        if baseline_data is None or current_data is None:
            return StatisticalTestResult(
                test_name=self.get_test_name(),
                score=0.0,
                drift_detected=False,
                severity="none",
                metadata={"error": "Insufficient data for Z-score test"},
            )

        try:
            baseline_mean = baseline_data.get("mean")
            baseline_std = baseline_data.get("stddev", 1.0)
            current_mean = current_data.get("mean")

            if baseline_std == 0:
                baseline_std = 1.0  # Avoid division by zero

            # Calculate Z-score
            z_score = abs((current_mean - baseline_mean) / baseline_std)

            # Determine drift and severity
            drift_detected = z_score > self.z_threshold
            if drift_detected:
                if z_score > 3.0:
                    severity = "high"
                elif z_score > 2.5:
                    severity = "medium"
                else:
                    severity = "low"
            else:
                severity = "none"

            return StatisticalTestResult(
                test_name=self.get_test_name(),
                score=z_score,
                drift_detected=drift_detected,
                severity=severity,
                metadata={
                    "z_threshold": self.z_threshold,
                    "z_score": z_score,
                    "baseline_mean": baseline_mean,
                    "current_mean": current_mean,
                    "baseline_std": baseline_std,
                },
            )
        except Exception as e:
            logger.warning(f"Z-score test failed: {e}")
            return StatisticalTestResult(
                test_name=self.get_test_name(),
                score=0.0,
                drift_detected=False,
                severity="none",
                metadata={"error": str(e)},
            )

    def score(self, test_result: StatisticalTestResult) -> float:
        """Return Z-score."""
        return test_result.score

    def is_drift(
        self,
        test_result: StatisticalTestResult,
        threshold: Optional[float] = None,
        sensitivity: str = "medium",
    ) -> bool:
        """Determine if drift detected."""
        if threshold is None:
            threshold = self.z_threshold
        threshold = self._get_sensitivity_threshold(threshold, sensitivity)
        return test_result.score > threshold

    def get_test_name(self) -> str:
        """Return test name."""
        return "z_score"

    def supports_column_type(self, column_type: str) -> bool:
        """Z-score test supports numeric columns."""
        numeric_types = [
            "integer",
            "int",
            "bigint",
            "smallint",
            "numeric",
            "decimal",
            "float",
            "double",
            "real",
            "number",
        ]
        return any(nt in column_type.lower() for nt in numeric_types)

    def supports_metric(self, metric_name: str) -> bool:
        """Z-score test supports mean and stddev metrics."""
        return metric_name in ["mean", "stddev"]


# ============================================================================
# Categorical Column Tests
# ============================================================================


class ChiSquareTest(StatisticalTest):
    """
    Chi-square test for category distribution drift.

    Tests whether the distribution of categories has changed significantly.
    """

    def __init__(self, alpha: float = 0.05):
        """
        Initialize Chi-square test.

        Args:
            alpha: Significance level (default: 0.05)
        """
        self.alpha = alpha

    def prepare(
        self, baseline_data: Any, current_data: Any, column_type: str, metric_name: str
    ) -> Tuple[Any, Any]:
        """Prepare data for Chi-square test."""
        # Chi-square needs category frequency distributions
        if isinstance(baseline_data, dict) and "category_distribution" in baseline_data:
            baseline_dist = baseline_data.get("category_distribution")
            current_dist = (
                current_data.get("category_distribution")
                if isinstance(current_data, dict)
                else None
            )

            if baseline_dist and current_dist:
                return (baseline_dist, current_dist)

        # Try to use distinct_count and top values if available
        if isinstance(baseline_data, dict) and isinstance(current_data, dict):
            baseline_distinct = baseline_data.get("distinct_count")
            current_distinct = current_data.get("distinct_count")

            if baseline_distinct is not None and current_distinct is not None:
                # Create synthetic distributions
                baseline_dist = self._create_synthetic_distribution(baseline_distinct)
                current_dist = self._create_synthetic_distribution(current_distinct)
                return (baseline_dist, current_dist)

        return (None, None)

    def compare(self, baseline_data: Any, current_data: Any) -> StatisticalTestResult:
        """Run Chi-square test."""
        if baseline_data is None or current_data is None:
            return StatisticalTestResult(
                test_name=self.get_test_name(),
                score=0.0,
                drift_detected=False,
                severity="none",
                metadata={"error": "Insufficient data for Chi-square test"},
            )

        try:
            # Convert to frequency dictionaries
            baseline_freq = self._to_frequency_dict(baseline_data)
            current_freq = self._to_frequency_dict(current_data)

            # Get all categories
            all_categories = set(baseline_freq.keys()) | set(current_freq.keys())

            if not all_categories:
                return StatisticalTestResult(
                    test_name=self.get_test_name(),
                    score=0.0,
                    drift_detected=False,
                    severity="none",
                    metadata={"error": "No categories found"},
                )

            # Calculate total counts
            baseline_total = sum(baseline_freq.values()) or 1.0
            current_total = sum(current_freq.values()) or 1.0
            grand_total = baseline_total + current_total

            # Calculate Chi-square statistic
            chi_square = 0.0
            for category in all_categories:
                baseline_obs = baseline_freq.get(category, 0)
                current_obs = current_freq.get(category, 0)

                # Expected frequencies (assuming no change)
                baseline_exp = (baseline_obs + current_obs) * (baseline_total / grand_total)
                current_exp = (baseline_obs + current_obs) * (current_total / grand_total)

                # Avoid division by zero
                if baseline_exp > 0:
                    chi_square += ((baseline_obs - baseline_exp) ** 2) / baseline_exp
                if current_exp > 0:
                    chi_square += ((current_obs - current_exp) ** 2) / current_exp

            # Degrees of freedom
            df = len(all_categories) - 1

            # Calculate p-value if scipy available
            p_value = None
            if SCIPY_AVAILABLE:
                p_value = 1 - stats.chi2.cdf(chi_square, df)

            # Determine drift and severity
            drift_detected = (p_value is not None and p_value < self.alpha) or chi_square > (df * 2)

            if drift_detected:
                if chi_square > (df * 5) or (p_value and p_value < 0.001):
                    severity = "high"
                elif chi_square > (df * 3) or (p_value and p_value < 0.01):
                    severity = "medium"
                else:
                    severity = "low"
            else:
                severity = "none"

            return StatisticalTestResult(
                test_name=self.get_test_name(),
                score=chi_square,
                p_value=p_value,
                drift_detected=drift_detected,
                severity=severity,
                metadata={
                    "alpha": self.alpha,
                    "chi_square": chi_square,
                    "degrees_of_freedom": df,
                    "p_value": p_value,
                },
            )
        except Exception as e:
            logger.warning(f"Chi-square test failed: {e}")
            return StatisticalTestResult(
                test_name=self.get_test_name(),
                score=0.0,
                drift_detected=False,
                severity="none",
                metadata={"error": str(e)},
            )

    def score(self, test_result: StatisticalTestResult) -> float:
        """Return Chi-square statistic."""
        return test_result.score

    def is_drift(
        self,
        test_result: StatisticalTestResult,
        threshold: Optional[float] = None,
        sensitivity: str = "medium",
    ) -> bool:
        """Determine if drift detected."""
        if threshold is None:
            # Default threshold based on degrees of freedom
            threshold = test_result.metadata.get("degrees_of_freedom", 10) * 2
        threshold = self._get_sensitivity_threshold(threshold, sensitivity)
        return test_result.score > threshold or test_result.drift_detected

    def get_test_name(self) -> str:
        """Return test name."""
        return "chi_square"

    def supports_column_type(self, column_type: str) -> bool:
        """Chi-square test supports categorical columns."""
        categorical_types = ["varchar", "char", "text", "string", "enum", "category"]
        return any(ct in column_type.lower() for ct in categorical_types)

    def supports_metric(self, metric_name: str) -> bool:
        """Chi-square test supports categorical metrics."""
        return metric_name in ["distinct_count", "category_distribution", "top_values"]

    def _to_frequency_dict(self, data: Any) -> Dict[str, float]:
        """Convert data to frequency dictionary."""
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                return {}

        if isinstance(data, dict):
            return {str(k): float(v) for k, v in data.items()}
        elif isinstance(data, (int, float)):
            # Create synthetic distribution
            return self._create_synthetic_distribution(int(data))

        return {}

    def _create_synthetic_distribution(self, distinct_count: int) -> Dict[str, float]:
        """Create synthetic category distribution."""
        dist = {}
        for i in range(min(distinct_count, 100)):  # Cap at 100 categories
            dist[f"category_{i}"] = 1.0 / distinct_count
        return dist


class EntropyChangeTest(StatisticalTest):
    """
    Shannon entropy comparison for categorical data.

    Detects changes in the entropy (randomness/uniformity) of category distributions.
    """

    def __init__(self, entropy_threshold: float = 0.1):
        """
        Initialize Entropy test.

        Args:
            entropy_threshold: Threshold for entropy change (default: 0.1)
        """
        self.entropy_threshold = entropy_threshold

    def prepare(
        self, baseline_data: Any, current_data: Any, column_type: str, metric_name: str
    ) -> Tuple[Any, Any]:
        """Prepare data for Entropy test."""
        # Entropy needs category distributions
        if isinstance(baseline_data, dict) and "category_distribution" in baseline_data:
            baseline_dist = baseline_data.get("category_distribution")
            current_dist = (
                current_data.get("category_distribution")
                if isinstance(current_data, dict)
                else None
            )

            if baseline_dist and current_dist:
                return (baseline_dist, current_dist)

        # Try to use distinct_count
        if isinstance(baseline_data, dict) and isinstance(current_data, dict):
            baseline_distinct = baseline_data.get("distinct_count")
            current_distinct = current_data.get("distinct_count")

            if baseline_distinct is not None and current_distinct is not None:
                baseline_dist = self._create_synthetic_distribution(baseline_distinct)
                current_dist = self._create_synthetic_distribution(current_distinct)
                return (baseline_dist, current_dist)

        return (None, None)

    def compare(self, baseline_data: Any, current_data: Any) -> StatisticalTestResult:
        """Calculate entropy change."""
        if baseline_data is None or current_data is None:
            return StatisticalTestResult(
                test_name=self.get_test_name(),
                score=0.0,
                drift_detected=False,
                severity="none",
                metadata={"error": "Insufficient data for Entropy test"},
            )

        try:
            # Convert to frequency distributions
            baseline_freq = self._to_frequency_dict(baseline_data)
            current_freq = self._to_frequency_dict(current_data)

            # Calculate entropies
            baseline_entropy = self._calculate_entropy(baseline_freq)
            current_entropy = self._calculate_entropy(current_freq)

            # Calculate entropy change
            entropy_change = abs(current_entropy - baseline_entropy)

            # Determine drift and severity
            drift_detected = entropy_change > self.entropy_threshold
            if drift_detected:
                if entropy_change > 0.3:
                    severity = "high"
                elif entropy_change > 0.2:
                    severity = "medium"
                else:
                    severity = "low"
            else:
                severity = "none"

            return StatisticalTestResult(
                test_name=self.get_test_name(),
                score=entropy_change,
                drift_detected=drift_detected,
                severity=severity,
                metadata={
                    "entropy_threshold": self.entropy_threshold,
                    "baseline_entropy": baseline_entropy,
                    "current_entropy": current_entropy,
                    "entropy_change": entropy_change,
                },
            )
        except Exception as e:
            logger.warning(f"Entropy test failed: {e}")
            return StatisticalTestResult(
                test_name=self.get_test_name(),
                score=0.0,
                drift_detected=False,
                severity="none",
                metadata={"error": str(e)},
            )

    def score(self, test_result: StatisticalTestResult) -> float:
        """Return entropy change score."""
        return test_result.score

    def is_drift(
        self,
        test_result: StatisticalTestResult,
        threshold: Optional[float] = None,
        sensitivity: str = "medium",
    ) -> bool:
        """Determine if drift detected."""
        if threshold is None:
            threshold = self.entropy_threshold
        threshold = self._get_sensitivity_threshold(threshold, sensitivity)
        return test_result.score > threshold

    def get_test_name(self) -> str:
        """Return test name."""
        return "entropy"

    def supports_column_type(self, column_type: str) -> bool:
        """Entropy test supports categorical columns."""
        categorical_types = ["varchar", "char", "text", "string", "enum", "category"]
        return any(ct in column_type.lower() for ct in categorical_types)

    def supports_metric(self, metric_name: str) -> bool:
        """Entropy test supports categorical metrics."""
        return metric_name in ["distinct_count", "category_distribution", "top_values"]

    def _to_frequency_dict(self, data: Any) -> Dict[str, float]:
        """Convert data to frequency dictionary."""
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                return {}

        if isinstance(data, dict):
            # Check if it's already a frequency dict or if it contains category_distribution
            if "category_distribution" in data:
                data = data["category_distribution"]
            # Convert values to float, handling nested dicts
            result = {}
            for k, v in data.items():
                if isinstance(v, (int, float)):
                    result[str(k)] = float(v)
                elif isinstance(v, dict):
                    # If value is a dict, skip or handle appropriately
                    continue
            return result
        elif isinstance(data, (int, float)):
            return self._create_synthetic_distribution(int(data))

        return {}

    def _create_synthetic_distribution(self, distinct_count: int) -> Dict[str, float]:
        """Create synthetic category distribution."""
        dist = {}
        for i in range(min(distinct_count, 100)):
            dist[f"category_{i}"] = 1.0 / distinct_count
        return dist

    def _calculate_entropy(self, frequency_dict: Dict[str, float]) -> float:
        """Calculate Shannon entropy."""
        total = sum(frequency_dict.values()) or 1.0
        entropy = 0.0

        for count in frequency_dict.values():
            if count > 0:
                prob = count / total
                entropy -= prob * math.log(prob, 2)

        return entropy


class TopKStabilityTest(StatisticalTest):
    """
    Top-K category stability test.

    Tracks the top-K most frequent categories and detects changes.
    """

    def __init__(self, k: int = 10, similarity_threshold: float = 0.7):
        """
        Initialize Top-K stability test.

        Args:
            k: Number of top categories to track (default: 10)
            similarity_threshold: Similarity threshold for stability (default: 0.7)
        """
        self.k = k
        self.similarity_threshold = similarity_threshold

    def prepare(
        self, baseline_data: Any, current_data: Any, column_type: str, metric_name: str
    ) -> Tuple[Any, Any]:
        """Prepare data for Top-K test."""
        # Top-K needs category distributions or top values
        if isinstance(baseline_data, dict):
            baseline_top = baseline_data.get("top_values") or baseline_data.get(
                "category_distribution"
            )
            current_top = (
                current_data.get("top_values") or current_data.get("category_distribution")
                if isinstance(current_data, dict)
                else None
            )

            if baseline_top and current_top:
                return (baseline_top, current_top)

        return (None, None)

    def compare(self, baseline_data: Any, current_data: Any) -> StatisticalTestResult:
        """Calculate Top-K stability."""
        if baseline_data is None or current_data is None:
            return StatisticalTestResult(
                test_name=self.get_test_name(),
                score=0.0,
                drift_detected=False,
                severity="none",
                metadata={"error": "Insufficient data for Top-K test"},
            )

        try:
            # Get top-K categories
            baseline_top_k = self._get_top_k(baseline_data, self.k)
            current_top_k = self._get_top_k(current_data, self.k)

            # Calculate Jaccard similarity
            baseline_set = set(baseline_top_k.keys())
            current_set = set(current_top_k.keys())

            intersection = len(baseline_set & current_set)
            union = len(baseline_set | current_set)

            similarity = intersection / union if union > 0 else 0.0
            dissimilarity = 1.0 - similarity

            # Determine drift and severity
            drift_detected = similarity < self.similarity_threshold
            if drift_detected:
                if similarity < 0.3:
                    severity = "high"
                elif similarity < 0.5:
                    severity = "medium"
                else:
                    severity = "low"
            else:
                severity = "none"

            return StatisticalTestResult(
                test_name=self.get_test_name(),
                score=dissimilarity,
                drift_detected=drift_detected,
                severity=severity,
                metadata={
                    "k": self.k,
                    "similarity_threshold": self.similarity_threshold,
                    "similarity": similarity,
                    "baseline_top_k": list(baseline_top_k.keys()),
                    "current_top_k": list(current_top_k.keys()),
                },
            )
        except Exception as e:
            logger.warning(f"Top-K test failed: {e}")
            return StatisticalTestResult(
                test_name=self.get_test_name(),
                score=0.0,
                drift_detected=False,
                severity="none",
                metadata={"error": str(e)},
            )

    def score(self, test_result: StatisticalTestResult) -> float:
        """Return dissimilarity score."""
        return test_result.score

    def is_drift(
        self,
        test_result: StatisticalTestResult,
        threshold: Optional[float] = None,
        sensitivity: str = "medium",
    ) -> bool:
        """Determine if drift detected."""
        if threshold is None:
            threshold = 1.0 - self.similarity_threshold  # Convert similarity to dissimilarity
        threshold = self._get_sensitivity_threshold(threshold, sensitivity)
        return test_result.score > threshold

    def get_test_name(self) -> str:
        """Return test name."""
        return "top_k"

    def supports_column_type(self, column_type: str) -> bool:
        """Top-K test supports categorical columns."""
        categorical_types = ["varchar", "char", "text", "string", "enum", "category"]
        return any(ct in column_type.lower() for ct in categorical_types)

    def supports_metric(self, metric_name: str) -> bool:
        """Top-K test supports categorical metrics."""
        return metric_name in ["top_values", "category_distribution", "distinct_count"]

    def _get_top_k(self, data: Any, k: int) -> Dict[str, float]:
        """Extract top-K categories from data."""
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                return {}

        if isinstance(data, dict):
            # Check if it contains top_values or category_distribution
            if "top_values" in data:
                data = data["top_values"]
            elif "category_distribution" in data:
                data = data["category_distribution"]

            # Sort by frequency and get top-K
            # Handle both dict values and nested structures
            items = []
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    items.append((str(key), float(value)))
                elif isinstance(value, dict):
                    # Skip nested dicts
                    continue

            sorted_items = sorted(items, key=lambda x: x[1], reverse=True)
            return dict(sorted_items[:k])
        elif isinstance(data, list):
            # Assume list of [category, count] pairs
            sorted_items = sorted(
                data,
                key=lambda x: float(x[1]) if isinstance(x, (list, tuple)) and len(x) >= 2 else 0,
                reverse=True,
            )
            return {
                str(item[0]): float(item[1])
                for item in sorted_items[:k]
                if isinstance(item, (list, tuple)) and len(item) >= 2
            }

        return {}


# ============================================================================
# Test Registry and Factory
# ============================================================================

STATISTICAL_TESTS = {
    "ks_test": KolmogorovSmirnovTest,
    "psi": PopulationStabilityIndexTest,
    "z_score": ZScoreVarianceTest,
    "chi_square": ChiSquareTest,
    "entropy": EntropyChangeTest,
    "top_k": TopKStabilityTest,
}


def create_statistical_test(test_name: str, **params) -> StatisticalTest:
    """
    Factory function to create statistical test instances.

    Args:
        test_name: Name of the test to create
        **params: Parameters to pass to the test constructor

    Returns:
        Configured statistical test instance

    Raises:
        ValueError: If test name is not recognized

    Example:
        >>> test = create_statistical_test('ks_test', alpha=0.05)
        >>> test = create_statistical_test('psi', buckets=10, threshold=0.2)
    """
    if test_name not in STATISTICAL_TESTS:
        available = ", ".join(STATISTICAL_TESTS.keys())
        raise ValueError(f"Unknown statistical test: {test_name}. " f"Available tests: {available}")

    test_class = STATISTICAL_TESTS[test_name]
    return test_class(**params)  # type: ignore[no-any-return]
