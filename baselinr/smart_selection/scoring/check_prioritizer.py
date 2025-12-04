"""
Check prioritizer for column recommendations.

Ranks and filters recommended checks to provide the most
valuable suggestions without overwhelming users.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..column_analysis.check_inferencer import CheckType, ColumnRecommendation, InferredCheck
from ..column_analysis.metadata_analyzer import ColumnMetadata
from ..column_analysis.statistical_analyzer import ColumnStatistics

logger = logging.getLogger(__name__)


@dataclass
class PrioritizationConfig:
    """Configuration for check prioritization."""

    # Maximum checks to recommend per column
    max_checks_per_column: int = 5

    # Maximum total checks per table
    max_checks_per_table: int = 50

    # Minimum confidence to include
    min_confidence: float = 0.5

    # Preferred check types (will be ranked higher)
    preferred_checks: List[str] = None  # type: ignore

    # Avoided check types (will be ranked lower or excluded)
    avoided_checks: List[str] = None  # type: ignore

    # Column importance factors
    prioritize_primary_keys: bool = True
    prioritize_foreign_keys: bool = True
    prioritize_timestamps: bool = True

    # De-prioritize columns that might be noisy
    deprioritize_high_cardinality_strings: bool = True

    def __post_init__(self):
        if self.preferred_checks is None:
            self.preferred_checks = ["completeness", "freshness", "uniqueness"]
        if self.avoided_checks is None:
            self.avoided_checks = []


class CheckPrioritizer:
    """
    Prioritizes and filters check recommendations.

    Ensures users receive the most valuable recommendations without
    overwhelming them with low-value checks.
    """

    # Default priority scores by check type (0-100)
    DEFAULT_CHECK_PRIORITIES = {
        CheckType.UNIQUENESS: 95,
        CheckType.COMPLETENESS: 90,
        CheckType.FRESHNESS: 88,
        CheckType.NOT_NULL: 85,
        CheckType.REFERENTIAL_INTEGRITY: 80,
        CheckType.FORMAT_EMAIL: 75,
        CheckType.FORMAT_UUID: 75,
        CheckType.NON_NEGATIVE: 70,
        CheckType.ALLOWED_VALUES: 68,
        CheckType.RANGE: 65,
        CheckType.VALID_DATE_RANGE: 65,
        CheckType.FORMAT_PHONE: 60,
        CheckType.FORMAT_URL: 60,
        CheckType.DISTRIBUTION: 55,
        CheckType.VALID_JSON: 50,
        CheckType.SEQUENTIAL_ORDERING: 45,
        CheckType.OUTLIER_DETECTION: 40,
        CheckType.SCHEMA_VALIDATION: 35,
        CheckType.DUPLICATE_DETECTION: 30,
        CheckType.FORMAT_ZIPCODE: 30,
        CheckType.FORMAT_ISO_COUNTRY: 30,
        CheckType.FORMAT_CUSTOM: 25,
    }

    # Column importance weights by characteristic
    COLUMN_IMPORTANCE_WEIGHTS = {
        "primary_key": 1.5,
        "foreign_key": 1.3,
        "timestamp": 1.2,
        "identifier": 1.15,
        "business_metric": 1.1,
        "default": 1.0,
    }

    def __init__(self, config: Optional[PrioritizationConfig] = None):
        """
        Initialize check prioritizer.

        Args:
            config: Prioritization configuration
        """
        self.config = config or PrioritizationConfig()

    def prioritize_table_recommendations(
        self,
        column_recommendations: List[ColumnRecommendation],
    ) -> List[ColumnRecommendation]:
        """
        Prioritize recommendations for an entire table.

        Args:
            column_recommendations: List of column recommendations

        Returns:
            Prioritized and filtered list of recommendations
        """
        # First, prioritize each column's checks
        prioritized = []
        for rec in column_recommendations:
            prioritized_rec = self.prioritize_column_checks(rec)
            if prioritized_rec.suggested_checks:  # Only include if has checks
                prioritized.append(prioritized_rec)

        # Sort columns by importance
        prioritized.sort(key=lambda r: self._calculate_column_importance(r), reverse=True)

        # Apply table-level limits
        total_checks = 0
        limited_recommendations = []

        for rec in prioritized:
            remaining_budget = self.config.max_checks_per_table - total_checks
            if remaining_budget <= 0:
                break

            # Limit checks for this column if needed
            if len(rec.suggested_checks) > remaining_budget:
                rec.suggested_checks = rec.suggested_checks[:remaining_budget]

            total_checks += len(rec.suggested_checks)
            limited_recommendations.append(rec)

        return limited_recommendations

    def prioritize_column_checks(
        self,
        recommendation: ColumnRecommendation,
    ) -> ColumnRecommendation:
        """
        Prioritize checks for a single column.

        Args:
            recommendation: Column recommendation

        Returns:
            Recommendation with prioritized and filtered checks
        """
        checks = recommendation.suggested_checks.copy()

        # Filter by confidence
        checks = [c for c in checks if c.confidence >= self.config.min_confidence]

        # Filter avoided check types
        if self.config.avoided_checks:
            avoided_set = set(self.config.avoided_checks)
            checks = [c for c in checks if c.check_type.value not in avoided_set]

        # Score each check
        scored_checks = []
        for check in checks:
            score = self._calculate_check_score(
                check,
                recommendation.metadata,
                recommendation.statistics,
            )
            scored_checks.append((score, check))

        # Sort by score (descending)
        scored_checks.sort(key=lambda x: x[0], reverse=True)

        # Apply per-column limit
        prioritized_checks = [
            check for _, check in scored_checks[: self.config.max_checks_per_column]
        ]

        # Update recommendation
        recommendation.suggested_checks = prioritized_checks

        return recommendation

    def filter_low_value_checks(
        self,
        checks: List[InferredCheck],
        metadata: ColumnMetadata,
    ) -> List[InferredCheck]:
        """
        Filter out low-value checks.

        Args:
            checks: List of checks to filter
            metadata: Column metadata

        Returns:
            Filtered list of checks
        """
        filtered: List[InferredCheck] = []

        for check in checks:
            # Skip low confidence
            if check.confidence < self.config.min_confidence:
                continue

            # Skip avoided types
            if check.check_type.value in self.config.avoided_checks:
                continue

            # Skip redundant checks
            if self._is_redundant_check(check, filtered):
                continue

            filtered.append(check)

        return filtered

    def _calculate_check_score(
        self,
        check: InferredCheck,
        metadata: ColumnMetadata,
        statistics: Optional[ColumnStatistics],
    ) -> float:
        """Calculate priority score for a check."""
        # Base priority from check type
        base_priority = self.DEFAULT_CHECK_PRIORITIES.get(check.check_type, 50)

        # Confidence factor
        confidence_factor = check.confidence

        # Preferred check boost
        preferred_boost = 1.2 if check.check_type.value in self.config.preferred_checks else 1.0

        # Column importance factor
        column_factor = self._get_column_importance_factor(metadata)

        # Statistical support factor
        stat_factor = self._get_statistical_support_factor(check, statistics)

        # Calculate final score
        score = base_priority * confidence_factor * preferred_boost * column_factor * stat_factor

        return score

    def _calculate_column_importance(self, recommendation: ColumnRecommendation) -> float:
        """Calculate importance score for a column."""
        importance = 1.0
        metadata = recommendation.metadata

        # Key status
        if metadata.is_primary_key:
            importance *= self.COLUMN_IMPORTANCE_WEIGHTS["primary_key"]
        if metadata.is_foreign_key:
            importance *= self.COLUMN_IMPORTANCE_WEIGHTS["foreign_key"]

        # Position (earlier columns often more important)
        position_factor = max(0.8, 1.0 - (metadata.position * 0.01))
        importance *= position_factor

        # Confidence of recommendations
        importance *= recommendation.overall_confidence

        # Number of high-confidence checks
        high_conf_checks = sum(1 for c in recommendation.suggested_checks if c.confidence >= 0.8)
        importance *= 1.0 + (high_conf_checks * 0.1)

        return importance

    def _get_column_importance_factor(self, metadata: ColumnMetadata) -> float:
        """Get importance factor for a column."""
        factors = []

        if metadata.is_primary_key and self.config.prioritize_primary_keys:
            factors.append(self.COLUMN_IMPORTANCE_WEIGHTS["primary_key"])

        if metadata.is_foreign_key and self.config.prioritize_foreign_keys:
            factors.append(self.COLUMN_IMPORTANCE_WEIGHTS["foreign_key"])

        if "timestamp" in metadata.name_patterns and self.config.prioritize_timestamps:
            factors.append(self.COLUMN_IMPORTANCE_WEIGHTS["timestamp"])

        if not factors:
            return self.COLUMN_IMPORTANCE_WEIGHTS["default"]

        return max(factors)

    def _get_statistical_support_factor(
        self,
        check: InferredCheck,
        statistics: Optional[ColumnStatistics],
    ) -> float:
        """Get factor based on statistical support for a check."""
        if statistics is None:
            return 0.9  # Slight penalty for no stats

        factor = 1.0

        # Uniqueness check with high uniqueness stats
        if check.check_type == CheckType.UNIQUENESS:
            if statistics.unique_ratio >= 0.99:
                factor = 1.2
            elif statistics.unique_ratio < 0.9:
                factor = 0.7

        # Completeness check with low null rate
        if check.check_type == CheckType.COMPLETENESS:
            if statistics.null_percentage < 1:
                factor = 1.1
            elif statistics.null_percentage > 50:
                factor = 0.8

        # Allowed values with clear cardinality
        if check.check_type == CheckType.ALLOWED_VALUES:
            if statistics.cardinality_type in ("low", "binary"):
                factor = 1.15
            elif statistics.cardinality_type == "unique":
                factor = 0.5  # Probably not categorical

        return factor

    def _is_redundant_check(
        self,
        check: InferredCheck,
        existing_checks: List[InferredCheck],
    ) -> bool:
        """Check if a check is redundant given existing checks."""
        for existing in existing_checks:
            # NOT_NULL is redundant with COMPLETENESS
            if (
                check.check_type == CheckType.NOT_NULL
                and existing.check_type == CheckType.COMPLETENESS
            ):
                return True

            # Same check type is redundant
            if check.check_type == existing.check_type:
                return True

        return False

    def get_prioritization_summary(
        self,
        column_recommendations: List[ColumnRecommendation],
    ) -> Dict[str, Any]:
        """
        Get a summary of prioritization results.

        Args:
            column_recommendations: Prioritized recommendations

        Returns:
            Summary dictionary
        """
        total_checks = sum(len(r.suggested_checks) for r in column_recommendations)
        high_conf_checks = sum(
            1 for r in column_recommendations for c in r.suggested_checks if c.confidence >= 0.8
        )
        medium_conf_checks = sum(
            1
            for r in column_recommendations
            for c in r.suggested_checks
            if 0.5 <= c.confidence < 0.8
        )

        check_type_counts: Dict[str, int] = {}
        for rec in column_recommendations:
            for check in rec.suggested_checks:
                check_type_counts[check.check_type.value] = (
                    check_type_counts.get(check.check_type.value, 0) + 1
                )

        return {
            "total_columns_with_recommendations": len(column_recommendations),
            "total_checks": total_checks,
            "high_confidence_checks": high_conf_checks,
            "medium_confidence_checks": medium_conf_checks,
            "check_type_distribution": check_type_counts,
        }
