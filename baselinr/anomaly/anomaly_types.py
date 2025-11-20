"""
Anomaly type definitions.

Defines the types of anomalies that can be detected in profiling metrics.
"""

from enum import Enum


class AnomalyType(str, Enum):
    """Types of anomalies that can be detected."""

    # Statistical deviations
    IQR_DEVIATION = "iqr_deviation"
    MAD_DEVIATION = "mad_deviation"
    EWMA_OUTLIER = "ewma_outlier"
    CONTROL_LIMIT_BREACH = "control_limit_breach"

    # Seasonal and trend anomalies
    SEASONAL_ANOMALY = "seasonal_anomaly"
    TREND_ANOMALY = "trend_anomaly"

    # Behavioral changes
    REGIME_SHIFT = "regime_shift"

    # Specific metric anomalies
    ROW_COUNT_SPIKE = "row_count_spike"
    ROW_COUNT_DIP = "row_count_dip"
    FRESHNESS_DELAY = "freshness_delay"
    CATEGORICAL_SHIFT = "categorical_shift"
    UNIQUENESS_DROP = "uniqueness_drop"
    NULL_SPIKE = "null_spike"
