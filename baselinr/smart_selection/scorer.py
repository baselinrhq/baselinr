"""
Table scoring and ranking logic for smart selection.

Implements scoring algorithms to rank tables based on usage patterns,
query frequency, recency, and other factors.
"""

import logging
import math
from dataclasses import dataclass
from typing import List, Optional

from .config import SmartSelectionCriteria
from .metadata_collector import TableMetadata

logger = logging.getLogger(__name__)


@dataclass
class TableScore:
    """Scoring result for a table."""

    metadata: TableMetadata
    total_score: float
    confidence: float

    # Component scores
    query_frequency_score: float
    query_recency_score: float
    write_activity_score: float
    table_size_score: float

    # Explanations
    reasons: List[str]
    warnings: List[str]

    def __lt__(self, other):
        """Enable sorting by total score (descending)."""
        return self.total_score > other.total_score


class TableScorer:
    """Scores and ranks tables based on metadata."""

    def __init__(self, criteria: SmartSelectionCriteria):
        """
        Initialize table scorer.

        Args:
            criteria: Smart selection criteria with scoring weights
        """
        self.criteria = criteria
        self.weights = criteria.weights

    def score_tables(self, tables: List[TableMetadata]) -> List[TableScore]:
        """
        Score a list of tables and return ranked results.

        Args:
            tables: List of table metadata to score

        Returns:
            List of TableScore objects, sorted by score (highest first)
        """
        scores = []

        for table in tables:
            score = self._score_table(table)
            if score:  # Only include tables that meet basic criteria
                scores.append(score)

        # Sort by total score (descending)
        scores.sort(reverse=True, key=lambda x: x.total_score)

        logger.info(
            f"Scored {len(scores)} tables out of {len(tables)} "
            f"(filtered {len(tables) - len(scores)})"
        )

        return scores

    def _score_table(self, table: TableMetadata) -> Optional[TableScore]:
        """
        Score a single table.

        Args:
            table: Table metadata

        Returns:
            TableScore if table meets criteria, None otherwise
        """
        # Apply filters first
        if not self._meets_criteria(table):
            return None

        # Calculate component scores
        query_freq_score = self._score_query_frequency(table)
        query_rec_score = self._score_query_recency(table)
        write_act_score = self._score_write_activity(table)
        size_score = self._score_table_size(table)

        # Calculate weighted total score
        total_score = (
            query_freq_score * self.weights.get("query_frequency", 0.4)
            + query_rec_score * self.weights.get("query_recency", 0.25)
            + write_act_score * self.weights.get("write_activity", 0.2)
            + size_score * self.weights.get("table_size", 0.15)
        )

        # Calculate confidence based on data completeness
        confidence = self._calculate_confidence(table)

        # Generate explanations
        reasons = self._generate_reasons(
            table,
            query_freq_score,
            query_rec_score,
            write_act_score,
            size_score,
        )
        warnings = self._generate_warnings(table)

        return TableScore(
            metadata=table,
            total_score=total_score,
            confidence=confidence,
            query_frequency_score=query_freq_score,
            query_recency_score=query_rec_score,
            write_activity_score=write_act_score,
            table_size_score=size_score,
            reasons=reasons,
            warnings=warnings,
        )

    def _meets_criteria(self, table: TableMetadata) -> bool:
        """
        Check if table meets basic selection criteria.

        Args:
            table: Table metadata

        Returns:
            True if table meets criteria, False otherwise
        """
        # Check minimum query count
        if table.query_count < self.criteria.min_query_count:
            return False

        # Check minimum queries per day
        if table.queries_per_day < self.criteria.min_queries_per_day:
            return False

        # Check row count thresholds
        if self.criteria.min_rows and table.row_count:
            if table.row_count < self.criteria.min_rows:
                return False

        if self.criteria.max_rows and table.row_count:
            if table.row_count > self.criteria.max_rows:
                return False

        # Check recency thresholds
        if self.criteria.max_days_since_query and table.days_since_last_query:
            if table.days_since_last_query > self.criteria.max_days_since_query:
                return False

        if self.criteria.max_days_since_modified and table.days_since_modified:
            if table.days_since_modified > self.criteria.max_days_since_modified:
                return False

        # Check exclude patterns
        for pattern in self.criteria.exclude_patterns:
            # Simple wildcard matching
            if self._matches_pattern(table.table, pattern):
                return False

        return True

    def _matches_pattern(self, table_name: str, pattern: str) -> bool:
        """
        Check if table name matches a wildcard pattern.

        Args:
            table_name: Table name to check
            pattern: Wildcard pattern (* and ? supported)

        Returns:
            True if matches, False otherwise
        """
        import fnmatch

        return fnmatch.fnmatch(table_name.lower(), pattern.lower())

    def _score_query_frequency(self, table: TableMetadata) -> float:
        """
        Score based on query frequency.

        Higher query counts get higher scores (0-100).
        Uses logarithmic scaling to prevent extreme outliers.

        Args:
            table: Table metadata

        Returns:
            Score from 0.0 to 100.0
        """
        if table.query_count == 0:
            return 0.0

        # Use log scale for query count (base 10)
        # 1 query = 0, 10 queries = 25, 100 queries = 50, 1000+ queries = 75-100
        log_count = math.log10(table.query_count)
        score = min(100.0, log_count * 33.33)  # Scale so 1000 queries = ~100

        return score

    def _score_query_recency(self, table: TableMetadata) -> float:
        """
        Score based on how recently the table was queried.

        More recent queries get higher scores (0-100).

        Args:
            table: Table metadata

        Returns:
            Score from 0.0 to 100.0
        """
        if not table.days_since_last_query and table.days_since_last_query != 0:
            # No data available
            return 50.0  # Neutral score

        days = table.days_since_last_query

        # Exponential decay: 100 for today, 90 for 1 day ago, 50 for 7 days, etc.
        # Using half-life of 7 days
        half_life = 7.0
        decay_factor = math.exp(-math.log(2) * days / half_life)
        score = 100.0 * decay_factor

        return score

    def _score_write_activity(self, table: TableMetadata) -> float:
        """
        Score based on write activity (how recently data was modified).

        Recently modified tables get higher scores (0-100).

        Args:
            table: Table metadata

        Returns:
            Score from 0.0 to 100.0
        """
        if not table.days_since_modified and table.days_since_modified != 0:
            # No data available
            return 50.0  # Neutral score

        days = table.days_since_modified

        # Similar to query recency but with longer half-life (14 days)
        # Since data updates might be less frequent than queries
        half_life = 14.0
        decay_factor = math.exp(-math.log(2) * days / half_life)
        score = 100.0 * decay_factor

        return score

    def _score_table_size(self, table: TableMetadata) -> float:
        """
        Score based on table size.

        Medium-sized tables get highest scores.
        Very small tables might be lookup/config tables.
        Very large tables might be expensive to profile.

        Args:
            table: Table metadata

        Returns:
            Score from 0.0 to 100.0
        """
        if not table.row_count:
            # No data available
            return 50.0  # Neutral score

        rows = table.row_count

        # Optimal range: 10K - 10M rows
        # Bell curve with peak at ~100K rows
        if rows < 100:
            # Very small tables (likely config/lookup)
            return 20.0
        elif rows < 1000:
            return 40.0
        elif rows < 10000:
            return 70.0
        elif rows < 100000:
            return 100.0  # Sweet spot
        elif rows < 1000000:
            return 95.0
        elif rows < 10000000:
            return 85.0
        elif rows < 100000000:
            return 70.0
        else:
            # Very large tables (might be expensive)
            return 50.0

    def _calculate_confidence(self, table: TableMetadata) -> float:
        """
        Calculate confidence score based on data completeness.

        Higher confidence when we have more complete metadata.

        Args:
            table: Table metadata

        Returns:
            Confidence from 0.0 to 1.0
        """
        confidence_factors = []

        # Query statistics available?
        if table.query_count > 0:
            confidence_factors.append(1.0)
        else:
            confidence_factors.append(0.3)

        # Recency data available?
        if table.last_query_time or table.last_modified_time:
            confidence_factors.append(1.0)
        else:
            confidence_factors.append(0.5)

        # Size data available?
        if table.row_count is not None:
            confidence_factors.append(1.0)
        else:
            confidence_factors.append(0.7)

        # Table metadata available?
        if table.table_type:
            confidence_factors.append(1.0)
        else:
            confidence_factors.append(0.8)

        # Average confidence
        avg_confidence = sum(confidence_factors) / len(confidence_factors)

        # Boost confidence if query count is high
        if table.query_count > 100:
            avg_confidence = min(1.0, avg_confidence * 1.1)

        return round(avg_confidence, 2)

    def _generate_reasons(
        self,
        table: TableMetadata,
        query_freq_score: float,
        query_rec_score: float,
        write_act_score: float,
        size_score: float,
    ) -> List[str]:
        """
        Generate human-readable reasons for selection.

        Args:
            table: Table metadata
            query_freq_score: Query frequency component score
            query_rec_score: Query recency component score
            write_act_score: Write activity component score
            size_score: Table size component score

        Returns:
            List of reason strings
        """
        reasons = []

        # Query frequency
        if table.query_count > 0:
            if table.queries_per_day >= 10:
                reasons.append(
                    f"Heavily used: {table.query_count:,} queries "
                    f"({table.queries_per_day:.1f} per day)"
                )
            elif table.queries_per_day >= 1:
                reasons.append(
                    f"Actively queried: {table.query_count:,} queries "
                    f"({table.queries_per_day:.1f} per day)"
                )
            else:
                reasons.append(f"Queried {table.query_count:,} times in lookback period")

        # Query recency
        if table.days_since_last_query is not None:
            if table.days_since_last_query == 0:
                reasons.append("Queried today")
            elif table.days_since_last_query <= 1:
                reasons.append(f"Last queried {table.days_since_last_query} day ago")
            elif table.days_since_last_query <= 7:
                reasons.append(f"Last queried {table.days_since_last_query} days ago")

        # Write activity
        if table.days_since_modified is not None:
            if table.days_since_modified <= 1:
                reasons.append("Updated recently (daily updates)")
            elif table.days_since_modified <= 7:
                reasons.append(f"Updated {table.days_since_modified} days ago")

        # Table size
        if table.row_count:
            if table.row_count >= 1000000:
                reasons.append(f"Large table with {table.row_count:,} rows")
            elif table.row_count >= 10000:
                reasons.append(f"Medium table with {table.row_count:,} rows")
            else:
                reasons.append(f"{table.row_count:,} rows")

        # If no specific reasons, add generic ones based on scores
        if not reasons:
            if query_freq_score > 50:
                reasons.append("Moderate query activity detected")
            if size_score > 50:
                reasons.append("Appropriate table size for monitoring")

        return reasons

    def _generate_warnings(self, table: TableMetadata) -> List[str]:
        """
        Generate warnings about potential issues.

        Args:
            table: Table metadata

        Returns:
            List of warning strings
        """
        warnings = []

        # Very large tables
        if table.row_count and table.row_count > 100000000:
            warnings.append("Very large table - consider sampling or partition-based profiling")

        # No recent queries despite being selected
        if table.days_since_last_query and table.days_since_last_query > 30:
            warnings.append(f"No queries in {table.days_since_last_query} days - may be stale")

        # No size information
        if not table.row_count:
            warnings.append("Row count unavailable - size-based scoring limited")

        # Views might have different characteristics
        if table.table_type and "VIEW" in table.table_type.upper():
            warnings.append("This is a view - consider monitoring underlying tables instead")

        return warnings
