"""
Anomaly detection for Baselinr.

Detects outliers and seasonal anomalies using learned expectations
as baselines, supporting multiple detection methods including IQR,
MAD, EWMA, trend/seasonality decomposition, and regime shift detection.
"""

from .anomaly_types import AnomalyType
from .detection_methods import (
    EWMADetector,
    IQRDetector,
    MADDetector,
    RegimeShiftDetector,
    TrendSeasonalityDetector,
)
from .detector import AnomalyDetector, AnomalyResult

__all__ = [
    "AnomalyDetector",
    "AnomalyResult",
    "AnomalyType",
    "IQRDetector",
    "MADDetector",
    "EWMADetector",
    "TrendSeasonalityDetector",
    "RegimeShiftDetector",
]
