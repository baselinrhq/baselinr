"""
Confidence scorer for column check recommendations.

Calculates confidence scores based on multiple signals
to determine the reliability of check recommendations.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..column_analysis.check_inferencer import ColumnRecommendation, InferredCheck
from ..column_analysis.metadata_analyzer import ColumnMetadata, InferredColumnType
from ..column_analysis.statistical_analyzer import ColumnStatistics

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceLevel:
    """Confidence level thresholds."""

    HIGH = 0.8
    MEDIUM = 0.5
    LOW = 0.3


class ConfidenceScorer:
    """
    Calculates and adjusts confidence scores for column recommendations.

    Combines multiple signals to produce reliable confidence scores that
    indicate how likely a recommendation is to be correct.
    """

    # Signal weights for confidence calculation
    DEFAULT_WEIGHTS = {
        "metadata_signals": 0.3,  # Name patterns, type info, key status
        "statistical_signals": 0.3,  # Profiling data quality and patterns
        "pattern_match_signals": 0.25,  # Pattern matcher confidence
        "consistency_signals": 0.15,  # Multiple agreeing signals
    }

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        min_confidence: float = 0.3,
        boost_primary_keys: bool = True,
        boost_foreign_keys: bool = True,
        penalize_missing_stats: bool = True,
    ):
        """
        Initialize confidence scorer.

        Args:
            weights: Custom signal weights (should sum to 1.0)
            min_confidence: Minimum confidence to return
            boost_primary_keys: Boost confidence for primary key columns
            boost_foreign_keys: Boost confidence for foreign key columns
            penalize_missing_stats: Reduce confidence when stats unavailable
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.min_confidence = min_confidence
        self.boost_primary_keys = boost_primary_keys
        self.boost_foreign_keys = boost_foreign_keys
        self.penalize_missing_stats = penalize_missing_stats

    def score_recommendation(
        self,
        recommendation: ColumnRecommendation,
    ) -> float:
        """
        Calculate overall confidence score for a column recommendation.

        Args:
            recommendation: Column recommendation to score

        Returns:
            Confidence score between 0 and 1
        """
        metadata = recommendation.metadata
        statistics = recommendation.statistics

        # Calculate component scores
        metadata_score = self._score_metadata_signals(metadata)
        statistical_score = self._score_statistical_signals(statistics)
        pattern_score = self._score_pattern_signals(recommendation)
        consistency_score = self._score_consistency(recommendation)

        # Weighted average
        weighted_score = (
            metadata_score * self.weights["metadata_signals"]
            + statistical_score * self.weights["statistical_signals"]
            + pattern_score * self.weights["pattern_match_signals"]
            + consistency_score * self.weights["consistency_signals"]
        )

        # Apply boosts
        if self.boost_primary_keys and metadata.is_primary_key:
            weighted_score *= 1.1

        if self.boost_foreign_keys and metadata.is_foreign_key:
            weighted_score *= 1.05

        # Apply penalty for missing stats
        if self.penalize_missing_stats and statistics is None:
            weighted_score *= 0.85

        # Clamp to valid range
        final_score = max(self.min_confidence, min(1.0, weighted_score))

        return round(final_score, 3)

    def score_check(
        self,
        check: InferredCheck,
        metadata: ColumnMetadata,
        statistics: Optional[ColumnStatistics] = None,
    ) -> float:
        """
        Calculate confidence score for a specific check.

        Args:
            check: Inferred check to score
            metadata: Column metadata
            statistics: Optional column statistics

        Returns:
            Confidence score between 0 and 1
        """
        base_confidence = check.confidence

        # Adjust based on signal strength
        signal_boost = 0.0

        # Multiple signals increase confidence
        num_signals = len(check.signals)
        if num_signals >= 3:
            signal_boost += 0.1
        elif num_signals >= 2:
            signal_boost += 0.05

        # Key status boosts certain checks
        if metadata.is_primary_key and check.check_type.value in (
            "uniqueness",
            "completeness",
        ):
            signal_boost += 0.1

        if metadata.is_foreign_key and check.check_type.value == "referential_integrity":
            signal_boost += 0.1

        # Statistical support boosts confidence
        if statistics:
            if check.check_type.value == "uniqueness" and statistics.unique_ratio >= 0.99:
                signal_boost += 0.05
            if check.check_type.value == "completeness" and statistics.null_percentage < 1:
                signal_boost += 0.05

        # Calculate final score
        final_score = min(1.0, base_confidence + signal_boost)

        return round(final_score, 3)

    def categorize_confidence(self, score: float) -> str:
        """
        Categorize a confidence score into high/medium/low.

        Args:
            score: Confidence score

        Returns:
            Category string: 'high', 'medium', or 'low'
        """
        if score >= ConfidenceLevel.HIGH:
            return "high"
        elif score >= ConfidenceLevel.MEDIUM:
            return "medium"
        else:
            return "low"

    def _score_metadata_signals(self, metadata: ColumnMetadata) -> float:
        """Score based on metadata quality and patterns."""
        score = 0.5  # Base score

        # Key status provides strong signals
        if metadata.is_primary_key:
            score += 0.3
        if metadata.is_foreign_key:
            score += 0.2

        # Name patterns provide signals
        if metadata.name_patterns:
            score += min(0.3, len(metadata.name_patterns) * 0.1)

        # Inferred type confidence
        if metadata.inferred_type != InferredColumnType.UNKNOWN:
            score += 0.1

        # Description available
        if metadata.description:
            score += 0.05

        return min(1.0, score)

    def _score_statistical_signals(
        self,
        statistics: Optional[ColumnStatistics],
    ) -> float:
        """Score based on statistical data quality."""
        if statistics is None:
            return 0.3  # Low score for missing stats

        score = 0.5  # Base score

        # Good sample size
        if statistics.row_count > 1000:
            score += 0.2
        elif statistics.row_count > 100:
            score += 0.1

        # Clear cardinality pattern
        if statistics.cardinality_type in ("unique", "binary", "low"):
            score += 0.1

        # Detected patterns
        if statistics.detected_patterns:
            score += min(0.2, len(statistics.detected_patterns) * 0.05)

        # Stability data available
        if statistics.volatility is not None:
            score += 0.05
            if statistics.is_stable:
                score += 0.05

        return min(1.0, score)

    def _score_pattern_signals(self, recommendation: ColumnRecommendation) -> float:
        """Score based on pattern matching results."""
        # Use average confidence of suggested checks from patterns
        pattern_checks = [
            c for c in recommendation.suggested_checks if any("Pattern" in s for s in c.signals)
        ]

        if not pattern_checks:
            return 0.5  # Neutral score

        avg_confidence = sum(c.confidence for c in pattern_checks) / len(pattern_checks)
        return avg_confidence

    def _score_consistency(self, recommendation: ColumnRecommendation) -> float:
        """Score based on consistency of multiple signals."""
        # Count unique signal sources
        signal_sources = set()

        for check in recommendation.suggested_checks:
            for signal in check.signals:
                if "Pattern" in signal:
                    signal_sources.add("pattern")
                elif "key" in signal.lower():
                    signal_sources.add("key")
                elif "uniqueness" in signal.lower() or "cardinality" in signal.lower():
                    signal_sources.add("statistics")
                else:
                    signal_sources.add("metadata")

        # More sources = higher consistency
        num_sources = len(signal_sources)
        if num_sources >= 3:
            return 1.0
        elif num_sources == 2:
            return 0.8
        elif num_sources == 1:
            return 0.6
        else:
            return 0.4


def calculate_overall_table_confidence(
    column_recommendations: List[ColumnRecommendation],
) -> float:
    """
    Calculate overall confidence for a table's column recommendations.

    Args:
        column_recommendations: List of column recommendations

    Returns:
        Overall confidence score
    """
    if not column_recommendations:
        return 0.0

    # Weight columns by their confidence and number of checks
    total_weight = 0.0
    weighted_sum = 0.0

    for rec in column_recommendations:
        weight = 1.0 + (len(rec.suggested_checks) * 0.1)
        weighted_sum += rec.overall_confidence * weight
        total_weight += weight

    if total_weight == 0:
        return 0.0

    return round(weighted_sum / total_weight, 3)
