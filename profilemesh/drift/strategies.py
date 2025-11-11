"""
Drift detection strategies for ProfileMesh.

Provides pluggable strategies for detecting drift in profiling metrics.
Each strategy implements a different algorithm for calculating drift severity.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DriftResult:
    """Result of drift calculation for a single metric."""
    
    drift_detected: bool
    drift_severity: str  # "none", "low", "medium", "high"
    change_absolute: Optional[float] = None
    change_percent: Optional[float] = None
    score: Optional[float] = None  # Generic score for ML-based methods
    metadata: Dict[str, Any] = None  # Additional method-specific data
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DriftDetectionStrategy(ABC):
    """Abstract base class for drift detection strategies."""
    
    @abstractmethod
    def calculate_drift(
        self,
        baseline_value: Any,
        current_value: Any,
        metric_name: str,
        column_name: str
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
        high_threshold: float = 30.0
    ):
        """
        Initialize absolute threshold strategy.
        
        Args:
            low_threshold: Threshold for low severity drift (% change)
            medium_threshold: Threshold for medium severity drift (% change)
            high_threshold: Threshold for high severity drift (% change)
        """
        self.low_threshold = low_threshold
        self.medium_threshold = medium_threshold
        self.high_threshold = high_threshold
    
    def calculate_drift(
        self,
        baseline_value: Any,
        current_value: Any,
        metric_name: str,
        column_name: str
    ) -> Optional[DriftResult]:
        """Calculate drift using absolute threshold method."""
        # Skip if either value is None
        if baseline_value is None or current_value is None:
            return None
        
        # Skip if not numeric
        if not isinstance(baseline_value, (int, float)) or not isinstance(current_value, (int, float)):
            return None
        
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
            
            if abs_change_percent >= self.high_threshold:
                drift_detected = True
                drift_severity = "high"
            elif abs_change_percent >= self.medium_threshold:
                drift_detected = True
                drift_severity = "medium"
            elif abs_change_percent >= self.low_threshold:
                drift_detected = True
                drift_severity = "low"
        
        return DriftResult(
            drift_detected=drift_detected,
            drift_severity=drift_severity,
            change_absolute=change_absolute,
            change_percent=change_percent,
            metadata={
                'method': 'absolute_threshold',
                'thresholds': {
                    'low': self.low_threshold,
                    'medium': self.medium_threshold,
                    'high': self.high_threshold
                }
            }
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
        high_threshold: float = 3.0
    ):
        """
        Initialize standard deviation strategy.
        
        Args:
            low_threshold: Number of std devs for low severity
            medium_threshold: Number of std devs for medium severity
            high_threshold: Number of std devs for high severity
        """
        self.low_threshold = low_threshold
        self.medium_threshold = medium_threshold
        self.high_threshold = high_threshold
    
    def calculate_drift(
        self,
        baseline_value: Any,
        current_value: Any,
        metric_name: str,
        column_name: str
    ) -> Optional[DriftResult]:
        """Calculate drift using standard deviation method."""
        # Note: This is a simplified version. In production, you'd want to
        # calculate mean and stddev from historical profiling runs.
        
        # Skip if either value is None
        if baseline_value is None or current_value is None:
            return None
        
        # Skip if not numeric
        if not isinstance(baseline_value, (int, float)) or not isinstance(current_value, (int, float)):
            return None
        
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
        
        if std_devs >= self.high_threshold:
            drift_detected = True
            drift_severity = "high"
        elif std_devs >= self.medium_threshold:
            drift_detected = True
            drift_severity = "medium"
        elif std_devs >= self.low_threshold:
            drift_detected = True
            drift_severity = "low"
        
        return DriftResult(
            drift_detected=drift_detected,
            drift_severity=drift_severity,
            change_absolute=change_absolute,
            change_percent=change_percent,
            score=std_devs,
            metadata={
                'method': 'standard_deviation',
                'std_devs': std_devs,
                'thresholds': {
                    'low': self.low_threshold,
                    'medium': self.medium_threshold,
                    'high': self.high_threshold
                }
            }
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
        self,
        baseline_value: Any,
        current_value: Any,
        metric_name: str,
        column_name: str
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


# Strategy registry for easy lookup
DRIFT_STRATEGIES = {
    'absolute_threshold': AbsoluteThresholdStrategy,
    'standard_deviation': StandardDeviationStrategy,
    'ml_based': MLBasedStrategy,
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
        available = ', '.join(DRIFT_STRATEGIES.keys())
        raise ValueError(
            f"Unknown drift strategy: {strategy_name}. "
            f"Available strategies: {available}"
        )
    
    strategy_class = DRIFT_STRATEGIES[strategy_name]
    return strategy_class(**kwargs)

