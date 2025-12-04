"""
Check type inferencer for column recommendations.

Maps column characteristics to appropriate data quality checks
based on metadata signals, statistical properties, and patterns.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .metadata_analyzer import ColumnMetadata, InferredColumnType
from .pattern_matcher import PatternMatch, PatternMatcher
from .statistical_analyzer import ColumnStatistics

logger = logging.getLogger(__name__)


class CheckType(str, Enum):
    """Types of data quality checks that can be recommended."""

    # Completeness checks
    COMPLETENESS = "completeness"
    NOT_NULL = "not_null"

    # Uniqueness checks
    UNIQUENESS = "uniqueness"
    DUPLICATE_DETECTION = "duplicate_detection"

    # Format checks
    FORMAT_EMAIL = "format_email"
    FORMAT_PHONE = "format_phone"
    FORMAT_URL = "format_url"
    FORMAT_UUID = "format_uuid"
    FORMAT_ZIPCODE = "format_zipcode"
    FORMAT_ISO_COUNTRY = "format_iso_country"
    FORMAT_CUSTOM = "format_custom"

    # Range/value checks
    RANGE = "range"
    NON_NEGATIVE = "non_negative"
    ALLOWED_VALUES = "allowed_values"
    VALID_DATE_RANGE = "valid_date_range"

    # Temporal checks
    FRESHNESS = "freshness"
    SEQUENTIAL_ORDERING = "sequential_ordering"

    # Distribution checks
    DISTRIBUTION = "distribution"
    OUTLIER_DETECTION = "outlier_detection"

    # Referential checks
    REFERENTIAL_INTEGRITY = "referential_integrity"

    # Structural checks
    VALID_JSON = "valid_json"
    SCHEMA_VALIDATION = "schema_validation"


@dataclass
class InferredCheck:
    """A recommended check for a column."""

    check_type: CheckType
    confidence: float
    signals: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    notes: Optional[str] = None
    priority: int = 50  # 0-100, higher = more important

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.check_type.value,
            "confidence": round(self.confidence, 2),
            "signals": self.signals,
            "config": self.config,
            "note": self.notes,
            "priority": self.priority,
        }


@dataclass
class ColumnRecommendation:
    """Complete recommendation for a column."""

    column_name: str
    data_type: str
    overall_confidence: float
    signals: List[str]
    suggested_checks: List[InferredCheck]
    metadata: ColumnMetadata
    statistics: Optional[ColumnStatistics] = None
    is_low_confidence: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML output."""
        return {
            "column": self.column_name,
            "data_type": self.data_type,
            "confidence": round(self.overall_confidence, 2),
            "signals": self.signals,
            "suggested_checks": [check.to_dict() for check in self.suggested_checks],
        }


class CheckInferencer:
    """
    Infers appropriate checks for columns based on their characteristics.

    Combines metadata signals, statistical properties, and naming patterns
    to recommend specific data quality checks.
    """

    # Check weights for priority calculation
    CHECK_PRIORITIES = {
        CheckType.COMPLETENESS: 80,
        CheckType.UNIQUENESS: 90,
        CheckType.FRESHNESS: 85,
        CheckType.NOT_NULL: 75,
        CheckType.FORMAT_EMAIL: 70,
        CheckType.FORMAT_UUID: 70,
        CheckType.REFERENTIAL_INTEGRITY: 75,
        CheckType.NON_NEGATIVE: 65,
        CheckType.RANGE: 60,
        CheckType.ALLOWED_VALUES: 65,
        CheckType.DISTRIBUTION: 50,
        CheckType.VALID_JSON: 55,
    }

    def __init__(
        self,
        pattern_matcher: Optional[PatternMatcher] = None,
        confidence_threshold: float = 0.5,
        max_checks_per_column: int = 5,
    ):
        """
        Initialize check inferencer.

        Args:
            pattern_matcher: Pattern matcher for name-based inference
            confidence_threshold: Minimum confidence to include a check
            max_checks_per_column: Maximum checks to recommend per column
        """
        self.pattern_matcher = pattern_matcher or PatternMatcher()
        self.confidence_threshold = confidence_threshold
        self.max_checks_per_column = max_checks_per_column

    def infer_checks(
        self,
        metadata: ColumnMetadata,
        statistics: Optional[ColumnStatistics] = None,
    ) -> ColumnRecommendation:
        """
        Infer appropriate checks for a column.

        Args:
            metadata: Column metadata
            statistics: Optional statistical properties from profiling

        Returns:
            ColumnRecommendation with suggested checks
        """
        checks: List[InferredCheck] = []
        signals: List[str] = []

        # Get pattern matches for the column name
        pattern_matches = self.pattern_matcher.match_column(
            column_name=metadata.name,
            column_type=metadata.data_type,
            data_type_base=metadata.data_type.lower().split("(")[0].strip(),
        )

        # Collect signals from patterns
        for match in pattern_matches:
            signals.append(f"Name matches pattern: {match.pattern_name}")

        # Add metadata signals
        if metadata.is_primary_key:
            signals.append("Column is a primary key")
        if metadata.is_foreign_key:
            signals.append(
                f"Column is a foreign key (references: {metadata.foreign_key_references})"
            )
        if not metadata.nullable:
            signals.append("Column is NOT NULL")

        # Infer checks based on semantic type
        type_checks = self._infer_by_type(metadata, statistics)
        checks.extend(type_checks)

        # Infer checks based on patterns
        pattern_checks = self._infer_from_patterns(pattern_matches, metadata, statistics)
        checks.extend(pattern_checks)

        # Infer checks based on key status
        key_checks = self._infer_key_checks(metadata, statistics)
        checks.extend(key_checks)

        # Infer checks based on statistics
        if statistics:
            stat_checks = self._infer_from_statistics(metadata, statistics)
            checks.extend(stat_checks)

            # Add statistics-based signals
            if statistics.cardinality_type:
                signals.append(f"Cardinality: {statistics.cardinality_type}")
            if statistics.null_percentage > 0:
                signals.append(f"Null percentage: {statistics.null_percentage:.1f}%")
            if statistics.unique_ratio >= 0.99:
                signals.append(f"High uniqueness: {statistics.unique_ratio:.1%}")

        # Deduplicate and prioritize checks
        checks = self._deduplicate_checks(checks)

        # Filter by confidence threshold
        checks = [c for c in checks if c.confidence >= self.confidence_threshold]

        # Sort by priority (descending) and confidence (descending)
        checks.sort(key=lambda x: (x.priority, x.confidence), reverse=True)

        # Limit number of checks
        checks = checks[: self.max_checks_per_column]

        # Calculate overall confidence
        if checks:
            overall_confidence = sum(c.confidence for c in checks) / len(checks)
        else:
            overall_confidence = 0.0

        return ColumnRecommendation(
            column_name=metadata.name,
            data_type=metadata.data_type,
            overall_confidence=overall_confidence,
            signals=signals,
            suggested_checks=checks,
            metadata=metadata,
            statistics=statistics,
            is_low_confidence=overall_confidence < 0.5,
        )

    def _infer_by_type(
        self,
        metadata: ColumnMetadata,
        statistics: Optional[ColumnStatistics],
    ) -> List[InferredCheck]:
        """Infer checks based on inferred semantic type."""
        checks = []

        if metadata.inferred_type == InferredColumnType.TIMESTAMP:
            checks.extend(self._infer_timestamp_checks(metadata, statistics))

        elif metadata.inferred_type == InferredColumnType.DATE:
            checks.extend(self._infer_date_checks(metadata, statistics))

        elif metadata.inferred_type == InferredColumnType.IDENTIFIER:
            checks.extend(self._infer_identifier_checks(metadata, statistics))

        elif metadata.inferred_type == InferredColumnType.NUMERIC:
            checks.extend(self._infer_numeric_checks(metadata, statistics))

        elif metadata.inferred_type == InferredColumnType.BOOLEAN:
            checks.extend(self._infer_boolean_checks(metadata, statistics))

        elif metadata.inferred_type == InferredColumnType.CATEGORICAL:
            checks.extend(self._infer_categorical_checks(metadata, statistics))

        elif metadata.inferred_type == InferredColumnType.JSON:
            checks.append(
                InferredCheck(
                    check_type=CheckType.VALID_JSON,
                    confidence=0.85,
                    signals=["JSON column detected"],
                    priority=self.CHECK_PRIORITIES.get(CheckType.VALID_JSON, 50),
                )
            )

        return checks

    def _infer_timestamp_checks(
        self,
        metadata: ColumnMetadata,
        statistics: Optional[ColumnStatistics],
    ) -> List[InferredCheck]:
        """Infer checks for timestamp columns."""
        checks = []

        # Freshness check for update timestamps
        is_update_ts = any(
            p in metadata.name.lower()
            for p in ["updated", "modified", "created", "loaded", "synced"]
        )

        if is_update_ts:
            config = {"max_age_hours": 24}  # Default, can be tuned
            if statistics and statistics.timestamp_freshness_hours:
                # Use observed pattern with buffer
                config["max_age_hours"] = int(statistics.timestamp_freshness_hours * 2) + 1

            checks.append(
                InferredCheck(
                    check_type=CheckType.FRESHNESS,
                    confidence=0.95,
                    signals=["Timestamp column name suggests freshness monitoring"],
                    config=config,
                    priority=self.CHECK_PRIORITIES[CheckType.FRESHNESS],
                )
            )

        # Completeness for important timestamps
        if not metadata.nullable:
            checks.append(
                InferredCheck(
                    check_type=CheckType.COMPLETENESS,
                    confidence=0.90,
                    signals=["NOT NULL timestamp column"],
                    config={"min_completeness": 1.0},
                    priority=self.CHECK_PRIORITIES[CheckType.COMPLETENESS],
                )
            )

        # Valid date range
        checks.append(
            InferredCheck(
                check_type=CheckType.VALID_DATE_RANGE,
                confidence=0.80,
                signals=["Timestamp should be within reasonable bounds"],
                config={
                    "min": "2000-01-01",
                    "max": "now + 1 day",
                    "note": "Verify bounds based on business requirements",
                },
                priority=self.CHECK_PRIORITIES.get(CheckType.VALID_DATE_RANGE, 55),
            )
        )

        return checks

    def _infer_date_checks(
        self,
        metadata: ColumnMetadata,
        statistics: Optional[ColumnStatistics],
    ) -> List[InferredCheck]:
        """Infer checks for date columns."""
        checks = []

        # Valid date range
        checks.append(
            InferredCheck(
                check_type=CheckType.VALID_DATE_RANGE,
                confidence=0.75,
                signals=["Date column should have reasonable bounds"],
                config={
                    "min": "2000-01-01",
                    "max": "now + 1 year",
                    "note": "Adjust bounds based on business requirements",
                },
                priority=55,
            )
        )

        return checks

    def _infer_identifier_checks(
        self,
        metadata: ColumnMetadata,
        statistics: Optional[ColumnStatistics],
    ) -> List[InferredCheck]:
        """Infer checks for identifier columns."""
        checks = []

        # Uniqueness for primary key-like columns
        if metadata.is_primary_key or (statistics and statistics.unique_ratio >= 0.99):
            checks.append(
                InferredCheck(
                    check_type=CheckType.UNIQUENESS,
                    confidence=0.98 if metadata.is_primary_key else 0.90,
                    signals=["Primary key" if metadata.is_primary_key else "High uniqueness ratio"],
                    config={"threshold": 1.0},
                    priority=self.CHECK_PRIORITIES[CheckType.UNIQUENESS],
                )
            )

        # Completeness for identifiers
        checks.append(
            InferredCheck(
                check_type=CheckType.COMPLETENESS,
                confidence=0.95 if not metadata.nullable else 0.85,
                signals=["Identifier columns should rarely be null"],
                config={"min_completeness": 0.99 if not metadata.nullable else 0.95},
                priority=self.CHECK_PRIORITIES[CheckType.COMPLETENESS],
            )
        )

        # UUID format if name suggests it
        if "uuid" in metadata.name.lower() or "guid" in metadata.name.lower():
            checks.append(
                InferredCheck(
                    check_type=CheckType.FORMAT_UUID,
                    confidence=0.90,
                    signals=["Column name suggests UUID format"],
                    config={"pattern": "uuid"},
                    priority=self.CHECK_PRIORITIES.get(CheckType.FORMAT_UUID, 60),
                )
            )

        return checks

    def _infer_numeric_checks(
        self,
        metadata: ColumnMetadata,
        statistics: Optional[ColumnStatistics],
    ) -> List[InferredCheck]:
        """Infer checks for numeric columns."""
        checks = []

        # Non-negative for counts, amounts, prices
        non_neg_patterns = ["amount", "price", "cost", "revenue", "count", "quantity", "qty"]
        if any(p in metadata.name.lower() for p in non_neg_patterns):
            checks.append(
                InferredCheck(
                    check_type=CheckType.NON_NEGATIVE,
                    confidence=0.90,
                    signals=["Column name suggests non-negative values"],
                    config={"allow_null": metadata.nullable},
                    priority=self.CHECK_PRIORITIES[CheckType.NON_NEGATIVE],
                )
            )

        # Range check with buffer from statistics
        if statistics and statistics.min_value is not None and statistics.max_value is not None:
            buffer = max(
                abs(statistics.max_value - statistics.min_value) * 0.2,
                abs(statistics.max_value) * 0.1,
            )
            checks.append(
                InferredCheck(
                    check_type=CheckType.RANGE,
                    confidence=0.70,
                    signals=[
                        (
                            f"Historical range: {statistics.min_value:.2f} to "
                            f"{statistics.max_value:.2f}"
                        )
                    ],
                    config={
                        "min": statistics.min_value - buffer,
                        "max": statistics.max_value + buffer,
                        "note": "Range based on historical data with buffer",
                    },
                    priority=self.CHECK_PRIORITIES[CheckType.RANGE],
                )
            )

        # Distribution monitoring for business metrics
        metric_patterns = ["revenue", "amount", "price", "cost", "sales", "profit"]
        if any(p in metadata.name.lower() for p in metric_patterns):
            checks.append(
                InferredCheck(
                    check_type=CheckType.DISTRIBUTION,
                    confidence=0.75,
                    signals=["Business metric column - monitor for distribution shifts"],
                    config={
                        "track_metrics": ["mean", "median", "p95", "p99"],
                        "alert_threshold": 0.3,
                    },
                    priority=self.CHECK_PRIORITIES[CheckType.DISTRIBUTION],
                )
            )

        return checks

    def _infer_boolean_checks(
        self,
        metadata: ColumnMetadata,
        statistics: Optional[ColumnStatistics],
    ) -> List[InferredCheck]:
        """Infer checks for boolean columns."""
        checks = []

        # Completeness for booleans
        checks.append(
            InferredCheck(
                check_type=CheckType.COMPLETENESS,
                confidence=0.85,
                signals=["Boolean columns should rarely be null"],
                config={"min_completeness": 0.99},
                priority=self.CHECK_PRIORITIES[CheckType.COMPLETENESS],
            )
        )

        # Distribution monitoring for flag columns
        if statistics and statistics.cardinality_type == "binary":
            checks.append(
                InferredCheck(
                    check_type=CheckType.DISTRIBUTION,
                    confidence=0.70,
                    signals=["Monitor for unexpected skew in boolean distribution"],
                    priority=self.CHECK_PRIORITIES[CheckType.DISTRIBUTION],
                )
            )

        return checks

    def _infer_categorical_checks(
        self,
        metadata: ColumnMetadata,
        statistics: Optional[ColumnStatistics],
    ) -> List[InferredCheck]:
        """Infer checks for categorical columns."""
        checks = []

        # Allowed values check if we know the distinct values
        if statistics and statistics.value_distribution:
            allowed_values = list(statistics.value_distribution.keys())
            if len(allowed_values) <= 50:  # Reasonable number of categories
                checks.append(
                    InferredCheck(
                        check_type=CheckType.ALLOWED_VALUES,
                        confidence=0.85,
                        signals=[f"Low cardinality: {len(allowed_values)} distinct values"],
                        config={
                            "values": allowed_values,
                            "note": "Based on current distinct values - update as needed",
                        },
                        priority=self.CHECK_PRIORITIES[CheckType.ALLOWED_VALUES],
                    )
                )

        # Completeness for status/type columns
        status_patterns = ["status", "type", "state", "category"]
        if any(p in metadata.name.lower() for p in status_patterns):
            checks.append(
                InferredCheck(
                    check_type=CheckType.COMPLETENESS,
                    confidence=0.80,
                    signals=["Status/type columns should typically be populated"],
                    config={"min_completeness": 0.95},
                    priority=self.CHECK_PRIORITIES[CheckType.COMPLETENESS],
                )
            )

        return checks

    def _infer_from_patterns(
        self,
        pattern_matches: List[PatternMatch],
        metadata: ColumnMetadata,
        statistics: Optional[ColumnStatistics],
    ) -> List[InferredCheck]:
        """Infer checks from pattern matches."""
        checks = []

        for match in pattern_matches:
            for check_name in match.suggested_checks:
                try:
                    check_type = CheckType(check_name)
                except ValueError:
                    # Handle special check names
                    if check_name.startswith("format_"):
                        check_type = CheckType.FORMAT_CUSTOM
                    elif check_name in ("range_0_100", "range_0_1"):
                        check_type = CheckType.RANGE
                    else:
                        continue

                config: Dict[str, Any] = {}

                # Add format-specific config
                if check_type == CheckType.FORMAT_EMAIL:
                    config["pattern"] = "email"
                elif check_type == CheckType.FORMAT_PHONE:
                    config["pattern"] = "phone"
                elif check_type == CheckType.FORMAT_URL:
                    config["pattern"] = "url"
                elif check_name == "range_0_100":
                    config = {
                        "min": 0,
                        "max": 100,
                        "note": "Percentage values (0-100)",
                    }
                elif check_name == "range_0_1":
                    config = {
                        "min": 0,
                        "max": 1,
                        "note": "Ratio values (0-1)",
                    }

                checks.append(
                    InferredCheck(
                        check_type=check_type,
                        confidence=match.confidence,
                        signals=[f"Pattern match: {match.pattern_name}"],
                        config=config,
                        priority=self.CHECK_PRIORITIES.get(check_type, 50),
                    )
                )

        return checks

    def _infer_key_checks(
        self,
        metadata: ColumnMetadata,
        statistics: Optional[ColumnStatistics],
    ) -> List[InferredCheck]:
        """Infer checks based on key status."""
        checks = []

        if metadata.is_primary_key:
            # Primary key: uniqueness and completeness
            checks.append(
                InferredCheck(
                    check_type=CheckType.UNIQUENESS,
                    confidence=0.99,
                    signals=["Primary key must be unique"],
                    config={"threshold": 1.0},
                    priority=100,
                )
            )
            checks.append(
                InferredCheck(
                    check_type=CheckType.COMPLETENESS,
                    confidence=0.99,
                    signals=["Primary key must not be null"],
                    config={"min_completeness": 1.0},
                    priority=100,
                )
            )

        if metadata.is_foreign_key and metadata.foreign_key_references:
            # Foreign key: referential integrity
            checks.append(
                InferredCheck(
                    check_type=CheckType.REFERENTIAL_INTEGRITY,
                    confidence=0.95,
                    signals=[f"Foreign key references: {metadata.foreign_key_references}"],
                    config={
                        "references": metadata.foreign_key_references,
                        "note": "Verify relationship before applying",
                    },
                    priority=self.CHECK_PRIORITIES[CheckType.REFERENTIAL_INTEGRITY],
                )
            )

        return checks

    def _infer_from_statistics(
        self,
        metadata: ColumnMetadata,
        statistics: ColumnStatistics,
    ) -> List[InferredCheck]:
        """Infer checks from statistical properties."""
        checks = []

        # High uniqueness suggests potential identifier
        if statistics.unique_ratio >= 0.99 and statistics.row_count > 100:
            if not metadata.is_primary_key:
                checks.append(
                    InferredCheck(
                        check_type=CheckType.UNIQUENESS,
                        confidence=0.85,
                        signals=[f"Very high uniqueness: {statistics.unique_ratio:.1%}"],
                        config={"threshold": 0.99},
                        priority=self.CHECK_PRIORITIES[CheckType.UNIQUENESS],
                    )
                )

        # Low null rate suggests completeness is important
        if statistics.null_percentage < 1.0 and statistics.row_count > 100:
            checks.append(
                InferredCheck(
                    check_type=CheckType.COMPLETENESS,
                    confidence=0.80,
                    signals=[f"Low null rate: {statistics.null_percentage:.1f}%"],
                    config={"min_completeness": 0.99},
                    priority=self.CHECK_PRIORITIES[CheckType.COMPLETENESS],
                )
            )

        # Low cardinality suggests categorical
        if statistics.cardinality_type in ("low", "binary"):
            if statistics.value_distribution and len(statistics.value_distribution) <= 20:
                checks.append(
                    InferredCheck(
                        check_type=CheckType.ALLOWED_VALUES,
                        confidence=0.80,
                        signals=[f"Low cardinality ({statistics.distinct_count} distinct values)"],
                        config={
                            "values": list(statistics.value_distribution.keys()),
                            "note": "Based on observed values",
                        },
                        priority=self.CHECK_PRIORITIES[CheckType.ALLOWED_VALUES],
                    )
                )

        return checks

    def _deduplicate_checks(self, checks: List[InferredCheck]) -> List[InferredCheck]:
        """Remove duplicate checks, keeping highest confidence."""
        seen: Dict[CheckType, InferredCheck] = {}

        for check in checks:
            if check.check_type not in seen:
                seen[check.check_type] = check
            elif check.confidence > seen[check.check_type].confidence:
                # Keep higher confidence version
                seen[check.check_type] = check

        return list(seen.values())
