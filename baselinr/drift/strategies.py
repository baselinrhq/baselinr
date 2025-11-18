"""
Drift detection strategies for Baselinr.

Provides pluggable strategies for detecting drift in profiling metrics.
Each strategy implements a different algorithm for calculating drift severity.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .type_thresholds import TypeSpecificThresholds

logger = logging.getLogger(__name__)


@dataclass
class DriftResult:
    """Result of drift calculation for a single metric."""

    drift_detected: bool
    drift_severity: str  # "none", "low", "medium", "high"
    change_absolute: Optional[float] = None
    change_percent: Optional[float] = None
    score: Optional[float] = None  # Generic score for ML-based methods
    metadata: Optional[Dict[str, Any]] = None  # Additional method-specific data

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DriftDetectionStrategy(ABC):
    """Abstract base class for drift detection strategies."""

    @abstractmethod
    def calculate_drift(
        self, baseline_value: Any, current_value: Any, metric_name: str, column_name: str
    ) -> Optional[DriftResult]:
        """
        Calculate drift between baseline and current values.

        Args:
            baseline_value: Baseline metric value
            current_value: Current metric value
            metric_name: Name of the metric being compared
            column_name: Name of the column

        Returns:
            DriftResult or None if drift cannot be calculated
        """
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return the name of this strategy."""
        pass


class AbsoluteThresholdStrategy(DriftDetectionStrategy):
    """
    Absolute threshold-based drift detection.

    Calculates percentage change and classifies based on absolute thresholds.
    """

    def __init__(
        self,
        low_threshold: float = 5.0,
        medium_threshold: float = 15.0,
        high_threshold: float = 30.0,
        type_thresholds: Optional[TypeSpecificThresholds] = None,
    ):
        """
        Initialize absolute threshold strategy.

        Args:
            low_threshold: Threshold for low severity drift (% change)
            medium_threshold: Threshold for medium severity drift (% change)
            high_threshold: Threshold for high severity drift (% change)
            type_thresholds: Optional type-specific thresholds instance
        """
        self.low_threshold = low_threshold
        self.medium_threshold = medium_threshold
        self.high_threshold = high_threshold
        self.type_thresholds = type_thresholds

    def calculate_drift(
        self, baseline_value: Any, current_value: Any, metric_name: str, column_name: str, **kwargs
    ) -> Optional[DriftResult]:
        """Calculate drift using absolute threshold method."""
        # Extract column_type from kwargs if available
        column_type = kwargs.get("column_type")

        # Check if metric should be ignored for this type
        if self.type_thresholds and column_type:
            if self.type_thresholds.should_ignore_metric_for_type(column_type, metric_name):
                return None

        # Skip if either value is None
        if baseline_value is None or current_value is None:
            return None

        # Skip if not numeric
        if not isinstance(baseline_value, (int, float)) or not isinstance(
            current_value, (int, float)
        ):
            return None

        # Get type-specific thresholds if available
        low_threshold = self.low_threshold
        medium_threshold = self.medium_threshold
        high_threshold = self.high_threshold

        if self.type_thresholds and column_type:
            base_thresholds = {
                "low_threshold": self.low_threshold,
                "medium_threshold": self.medium_threshold,
                "high_threshold": self.high_threshold,
            }
            type_thresholds = self.type_thresholds.get_thresholds_for_type(
                column_type, metric_name, base_thresholds
            )
            low_threshold = type_thresholds["low_threshold"]
            medium_threshold = type_thresholds["medium_threshold"]
            high_threshold = type_thresholds["high_threshold"]

        # Calculate changes
        change_absolute = current_value - baseline_value

        if baseline_value != 0:
            change_percent = (change_absolute / abs(baseline_value)) * 100
        else:
            change_percent = None

        # Determine drift severity
        drift_detected = False
        drift_severity = "none"

        if change_percent is not None:
            abs_change_percent = abs(change_percent)

            if abs_change_percent >= high_threshold:
                drift_detected = True
                drift_severity = "high"
            elif abs_change_percent >= medium_threshold:
                drift_detected = True
                drift_severity = "medium"
            elif abs_change_percent >= low_threshold:
                drift_detected = True
                drift_severity = "low"

        return DriftResult(
            drift_detected=drift_detected,
            drift_severity=drift_severity,
            change_absolute=change_absolute,
            change_percent=change_percent,
            metadata={
                "method": "absolute_threshold",
                "thresholds": {
                    "low": low_threshold,
                    "medium": medium_threshold,
                    "high": high_threshold,
                },
                "column_type": column_type,
                "type_specific": self.type_thresholds is not None and column_type is not None,
            },
        )

    def get_strategy_name(self) -> str:
        """Return strategy name."""
        return "absolute_threshold"


class StandardDeviationStrategy(DriftDetectionStrategy):
    """
    Statistical drift detection using standard deviation.

    Requires historical data to calculate mean and standard deviation,
    then classifies drift based on number of standard deviations from baseline.
    """

    def __init__(
        self,
        low_threshold: float = 1.0,
        medium_threshold: float = 2.0,
        high_threshold: float = 3.0,
        type_thresholds: Optional[TypeSpecificThresholds] = None,
    ):
        """
        Initialize standard deviation strategy.

        Args:
            low_threshold: Number of std devs for low severity
            medium_threshold: Number of std devs for medium severity
            high_threshold: Number of std devs for high severity
            type_thresholds: Optional type-specific thresholds instance
        """
        self.low_threshold = low_threshold
        self.medium_threshold = medium_threshold
        self.high_threshold = high_threshold
        self.type_thresholds = type_thresholds

    def calculate_drift(
        self, baseline_value: Any, current_value: Any, metric_name: str, column_name: str, **kwargs
    ) -> Optional[DriftResult]:
        """Calculate drift using standard deviation method."""
        # Extract column_type from kwargs if available
        column_type = kwargs.get("column_type")

        # Check if metric should be ignored for this type
        if self.type_thresholds and column_type:
            if self.type_thresholds.should_ignore_metric_for_type(column_type, metric_name):
                return None

        # Note: This is a simplified version. In production, you'd want to
        # calculate mean and stddev from historical profiling runs.

        # Skip if either value is None
        if baseline_value is None or current_value is None:
            return None

        # Skip if not numeric
        if not isinstance(baseline_value, (int, float)) or not isinstance(
            current_value, (int, float)
        ):
            return None

        # Get type-specific thresholds if available
        low_threshold = self.low_threshold
        medium_threshold = self.medium_threshold
        high_threshold = self.high_threshold

        if self.type_thresholds and column_type:
            # For standard deviation strategy, we need to convert type-specific
            # percentage thresholds to std dev equivalents
            # Use a rough approximation: 10% change ≈ 1 std dev
            base_thresholds = {
                "low_threshold": self.low_threshold,
                "medium_threshold": self.medium_threshold,
                "high_threshold": self.high_threshold,
            }
            type_thresholds = self.type_thresholds.get_thresholds_for_type(
                column_type, metric_name, base_thresholds
            )
            # Convert percentage thresholds to std dev approximations
            # This is a heuristic - in production you'd use actual historical stddev
            low_threshold = type_thresholds["low_threshold"] / 10.0
            medium_threshold = type_thresholds["medium_threshold"] / 10.0
            high_threshold = type_thresholds["high_threshold"] / 10.0

        # For now, use a simple percentage as a proxy for std devs
        # In a full implementation, you'd query historical runs to get actual stddev
        change_absolute = current_value - baseline_value

        if baseline_value != 0:
            change_percent = (change_absolute / abs(baseline_value)) * 100
            # Rough approximation: 10% change ≈ 1 std dev
            std_devs = abs(change_percent) / 10.0
        else:
            return None

        # Determine drift severity based on std devs
        drift_detected = False
        drift_severity = "none"

        if std_devs >= high_threshold:
            drift_detected = True
            drift_severity = "high"
        elif std_devs >= medium_threshold:
            drift_detected = True
            drift_severity = "medium"
        elif std_devs >= low_threshold:
            drift_detected = True
            drift_severity = "low"

        return DriftResult(
            drift_detected=drift_detected,
            drift_severity=drift_severity,
            change_absolute=change_absolute,
            change_percent=change_percent,
            score=std_devs,
            metadata={
                "method": "standard_deviation",
                "std_devs": std_devs,
                "thresholds": {
                    "low": low_threshold,
                    "medium": medium_threshold,
                    "high": high_threshold,
                },
                "column_type": column_type,
                "type_specific": self.type_thresholds is not None and column_type is not None,
            },
        )

    def get_strategy_name(self) -> str:
        """Return strategy name."""
        return "standard_deviation"


class MLBasedStrategy(DriftDetectionStrategy):
    """
    Placeholder for ML-based drift detection.

    This strategy can be implemented to use machine learning models
    for anomaly detection, such as:
    - Isolation Forest
    - Autoencoder-based detection
    - LSTM for time-series drift
    - Statistical tests (KS test, Chi-squared, etc.)
    """

    def __init__(self, model_config: Optional[Dict[str, Any]] = None):
        """
        Initialize ML-based strategy.

        Args:
            model_config: Configuration for the ML model
        """
        self.model_config = model_config or {}
        logger.warning("MLBasedStrategy is not yet implemented. This is a placeholder.")

    def calculate_drift(
        self, baseline_value: Any, current_value: Any, metric_name: str, column_name: str
    ) -> Optional[DriftResult]:
        """Calculate drift using ML method."""
        # Placeholder implementation
        # In production, this would:
        # 1. Load a trained model
        # 2. Prepare features from historical data
        # 3. Score the current value
        # 4. Return drift based on anomaly score

        raise NotImplementedError(
            "ML-based drift detection is not yet implemented. "
            "This is a placeholder for future enhancement."
        )

    def get_strategy_name(self) -> str:
        """Return strategy name."""
        return "ml_based"


class StatisticalStrategy(DriftDetectionStrategy):
    """
    Statistical test-based drift detection strategy.

    Uses multiple statistical tests (KS test, PSI, chi-square, etc.)
    to detect drift based on column type and metric characteristics.
    """

    def __init__(
        self,
        tests: List[str],
        sensitivity: str = "medium",
        test_params: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        """
        Initialize statistical strategy.

        Args:
            tests: List of test names to use (e.g., ['ks_test', 'psi', 'chi_square'])
            sensitivity: Sensitivity level ("low", "medium", "high")
            test_params: Optional dict of test-specific parameters
                        e.g., {'ks_test': {'alpha': 0.05}, 'psi': {'buckets': 10}}
        """
        from .statistical_tests import StatisticalTest, create_statistical_test

        self.tests: List[str] = tests
        self.sensitivity = sensitivity
        self.test_params = test_params or {}
        self.test_instances: List[StatisticalTest] = []

        # Create test instances
        for test_name in tests:
            try:
                params = self.test_params.get(test_name, {})
                test_instance = create_statistical_test(test_name, **params)
                self.test_instances.append(test_instance)
            except Exception as e:
                logger.warning(f"Failed to create statistical test '{test_name}': {e}")

    def calculate_drift(
        self, baseline_value: Any, current_value: Any, metric_name: str, column_name: str, **kwargs
    ) -> Optional[DriftResult]:
        """
        Calculate drift using statistical tests.

        Args:
            baseline_value: Baseline metric value
            current_value: Current metric value
            metric_name: Name of the metric
            column_name: Name of the column
            **kwargs: Additional parameters:
                column_type: Optional column data type
                baseline_data: Optional dict with additional baseline data (histogram, etc.)
                current_data: Optional dict with additional current data (histogram, etc.)

        Returns:
            DriftResult with aggregated test results
        """
        if not self.test_instances:
            logger.warning("No statistical tests available")
            return None

        # Extract optional parameters
        column_type = kwargs.get("column_type")
        baseline_data = kwargs.get("baseline_data")
        current_data = kwargs.get("current_data")

        # Prepare data for tests
        if baseline_data is None:
            baseline_data = {"value": baseline_value}
        if current_data is None:
            current_data = {"value": current_value}

        # Infer column type if not provided
        if column_type is None:
            column_type = self._infer_column_type(baseline_value, current_value)

        # Run applicable tests
        test_results = []
        for test in self.test_instances:
            # Check if test supports this column type and metric
            if not test.supports_column_type(column_type):
                continue
            if not test.supports_metric(metric_name):
                continue

            try:
                # Prepare data
                prepared_baseline, prepared_current = test.prepare(
                    baseline_data, current_data, column_type, metric_name
                )

                # Run comparison
                result = test.compare(prepared_baseline, prepared_current)

                # Check if drift detected
                drift_detected = test.is_drift(result, sensitivity=self.sensitivity)
                result.drift_detected = drift_detected

                test_results.append(result)
            except Exception as e:
                logger.warning(f"Statistical test {test.get_test_name()} failed: {e}")
                continue

        if not test_results:
            # No tests could run, fallback to simple threshold
            logger.debug(f"No statistical tests could run for {column_name}.{metric_name}")
            return None

        # Aggregate results
        return self._aggregate_results(test_results, baseline_value, current_value, metric_name)

    def _aggregate_results(
        self, test_results: List[Any], baseline_value: Any, current_value: Any, metric_name: str
    ) -> DriftResult:
        """Aggregate multiple test results into a single DriftResult."""

        # Determine overall drift and severity
        any_drift = any(tr.drift_detected for tr in test_results)

        # Get max severity
        severity_levels = {"none": 0, "low": 1, "medium": 2, "high": 3}
        max_severity = max(
            (tr.severity for tr in test_results),
            key=lambda s: severity_levels.get(s, 0),
            default="none",
        )

        # Calculate average score
        scores = [tr.score for tr in test_results if tr.score is not None]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        # Calculate change percent if numeric
        change_percent = None
        change_absolute = None
        if isinstance(baseline_value, (int, float)) and isinstance(current_value, (int, float)):
            change_absolute = current_value - baseline_value
            if baseline_value != 0:
                change_percent = (change_absolute / abs(baseline_value)) * 100

        # Collect metadata from all tests
        metadata = {
            "strategy": "statistical",
            "tests_run": [tr.test_name for tr in test_results],
            "test_results": [
                {
                    "test": tr.test_name,
                    "score": tr.score,
                    "p_value": tr.p_value,
                    "drift_detected": tr.drift_detected,
                    "severity": tr.severity,
                    "metadata": tr.metadata,
                }
                for tr in test_results
            ],
            "aggregated_score": avg_score,
            "sensitivity": self.sensitivity,
        }

        return DriftResult(
            drift_detected=any_drift,
            drift_severity=max_severity,
            change_absolute=change_absolute,
            change_percent=change_percent,
            score=avg_score,
            metadata=metadata,
        )

    def _infer_column_type(self, baseline_value: Any, current_value: Any) -> str:
        """Infer column type from values."""
        if isinstance(baseline_value, (int, float)) and isinstance(current_value, (int, float)):
            return "numeric"
        elif isinstance(baseline_value, str) or isinstance(current_value, str):
            return "varchar"
        else:
            return "unknown"

    def get_strategy_name(self) -> str:
        """Return strategy name."""
        return "statistical"


# Strategy registry for easy lookup
DRIFT_STRATEGIES = {
    "absolute_threshold": AbsoluteThresholdStrategy,
    "standard_deviation": StandardDeviationStrategy,
    "ml_based": MLBasedStrategy,
    "statistical": StatisticalStrategy,
}


def create_drift_strategy(strategy_name: str, **kwargs) -> DriftDetectionStrategy:
    """
    Factory function to create drift detection strategies.

    Args:
        strategy_name: Name of the strategy to create
        **kwargs: Parameters to pass to the strategy constructor

    Returns:
        Configured drift detection strategy

    Raises:
        ValueError: If strategy name is not recognized

    Example:
        >>> strategy = create_drift_strategy('absolute_threshold',
        ...                                   low_threshold=5.0,
        ...                                   medium_threshold=15.0,
        ...                                   high_threshold=30.0)
    """
    if strategy_name not in DRIFT_STRATEGIES:
        available = ", ".join(DRIFT_STRATEGIES.keys())
        raise ValueError(
            f"Unknown drift strategy: {strategy_name}. " f"Available strategies: {available}"
        )

    strategy_class = DRIFT_STRATEGIES[strategy_name]
    return strategy_class(**kwargs)  # type: ignore[no-any-return]
