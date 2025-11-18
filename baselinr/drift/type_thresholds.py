"""
Type-specific threshold rules for drift detection.

Applies different sensitivity thresholds based on column data type
to reduce false positives and improve drift detection accuracy.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Set

from .type_normalizer import normalize_column_type

logger = logging.getLogger(__name__)


@dataclass
class TypeSpecificThresholds:
    """Manages type-specific threshold configuration and application."""

    config: Dict[str, Dict[str, Any]]
    enabled: bool = True
    _ignored_metrics: Optional[Dict[str, Set[str]]] = None

    def __post_init__(self):
        """Initialize ignored metrics mapping."""
        if self._ignored_metrics is None:
            self._ignored_metrics = {
                "categorical": {"mean", "stddev", "min", "max"},
                "boolean": {"mean", "stddev", "min", "max", "histogram"},
                "timestamp": set(),  # All metrics are relevant for timestamps
                "numeric": set(),  # All metrics are relevant for numeric
                "unknown": set(),  # Don't ignore anything for unknown types
            }

    @property
    def IGNORED_METRICS(self) -> Dict[str, Set[str]]:
        """Get ignored metrics mapping."""
        if self._ignored_metrics is None:
            self._ignored_metrics = {
                "categorical": {"mean", "stddev", "min", "max"},
                "boolean": {"mean", "stddev", "min", "max", "histogram"},
                "timestamp": set(),  # All metrics are relevant for timestamps
                "numeric": set(),  # All metrics are relevant for numeric
                "unknown": set(),  # Don't ignore anything for unknown types
            }
        return self._ignored_metrics

    def get_thresholds_for_type(
        self, column_type: str, metric_name: str, base_thresholds: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Get type-specific thresholds for a column type and metric.

        Args:
            column_type: Normalized column type (numeric, categorical, timestamp, boolean)
            metric_name: Name of the metric (e.g., "mean", "stddev", "distinct_count")
            base_thresholds: Base thresholds dict with keys:
                low_threshold, medium_threshold, high_threshold

        Returns:
            Dictionary with adjusted thresholds: {low_threshold, medium_threshold, high_threshold}
        """
        if not self.enabled:
            return base_thresholds

        # Check if already normalized, otherwise normalize
        normalized_types = {"numeric", "categorical", "timestamp", "boolean", "unknown"}
        if column_type.lower() in normalized_types:
            normalized_type = column_type.lower()
        else:
            normalized_type = normalize_column_type(column_type)

        # Get type-specific config
        type_config = self.config.get(normalized_type, {})

        # Try to get metric-specific thresholds first
        metric_config = type_config.get(metric_name, {})

        # If metric-specific config exists, use it
        if metric_config and isinstance(metric_config, dict):
            thresholds = {
                "low_threshold": metric_config.get(
                    "low", base_thresholds.get("low_threshold", 5.0)
                ),
                "medium_threshold": metric_config.get(
                    "medium", base_thresholds.get("medium_threshold", 15.0)
                ),
                "high_threshold": metric_config.get(
                    "high", base_thresholds.get("high_threshold", 30.0)
                ),
            }
            return thresholds

        # Fall back to default thresholds for this type
        default_config = type_config.get("default", {})
        if default_config and isinstance(default_config, dict):
            thresholds = {
                "low_threshold": default_config.get(
                    "low", base_thresholds.get("low_threshold", 5.0)
                ),
                "medium_threshold": default_config.get(
                    "medium", base_thresholds.get("medium_threshold", 15.0)
                ),
                "high_threshold": default_config.get(
                    "high", base_thresholds.get("high_threshold", 30.0)
                ),
            }
            return thresholds

        # No type-specific config, use base thresholds
        return base_thresholds

    def should_ignore_metric_for_type(self, column_type: str, metric_name: str) -> bool:
        """
        Check if a metric should be ignored for a given column type.

        Some metrics don't make sense for certain types (e.g., mean for categorical).

        Args:
            column_type: Normalized column type
            metric_name: Name of the metric

        Returns:
            True if metric should be ignored, False otherwise
        """
        if not self.enabled:
            return False

        # Check if already normalized, otherwise normalize
        normalized_types = {"numeric", "categorical", "timestamp", "boolean", "unknown"}
        if column_type.lower() in normalized_types:
            normalized_type = column_type.lower()
        else:
            normalized_type = normalize_column_type(column_type)
        ignored = self.IGNORED_METRICS.get(normalized_type, set())
        return metric_name in ignored

    def get_type_category(self, column_type: str) -> str:
        """
        Get the normalized type category for a column type.

        Args:
            column_type: Database-specific column type

        Returns:
            Normalized type category
        """
        return normalize_column_type(column_type)


def create_type_thresholds(
    config: Optional[Dict[str, Dict[str, Any]]] = None, enabled: bool = True
) -> TypeSpecificThresholds:
    """
    Factory function to create TypeSpecificThresholds instance.

    Args:
        config: Type-specific threshold configuration dictionary
        enabled: Whether type-specific thresholds are enabled

    Returns:
        TypeSpecificThresholds instance
    """
    if config is None:
        # Default configuration
        config = {
            "numeric": {
                "mean": {"low": 10.0, "medium": 25.0, "high": 50.0},
                "stddev": {"low": 3.0, "medium": 8.0, "high": 15.0},
                "default": {"low": 5.0, "medium": 15.0, "high": 30.0},
            },
            "categorical": {
                "distinct_count": {"low": 2.0, "medium": 5.0, "high": 10.0},
                "unique_ratio": {"low": 0.02, "medium": 0.05, "high": 0.10},
                "default": {"low": 5.0, "medium": 15.0, "high": 30.0},
            },
            "timestamp": {
                "default": {"low": 5.0, "medium": 15.0, "high": 30.0},
            },
            "boolean": {
                "default": {"low": 2.0, "medium": 5.0, "high": 10.0},
            },
        }

    return TypeSpecificThresholds(config=config, enabled=enabled)
