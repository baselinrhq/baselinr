"""
Pattern learner for column naming conventions.

Learns patterns from existing column configurations to improve
future check recommendations.
"""

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class LearnedPattern:
    """A pattern learned from existing configurations."""

    pattern: str  # Regex or wildcard pattern
    pattern_type: str  # 'suffix', 'prefix', 'contains', 'exact'
    suggested_checks: List[str]
    confidence: float
    source_columns: List[str] = field(default_factory=list)
    occurrence_count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern": self.pattern,
            "pattern_type": self.pattern_type,
            "checks": [{"type": c, "confidence": self.confidence} for c in self.suggested_checks],
            "confidence": round(self.confidence, 2),
            "occurrence_count": self.occurrence_count,
        }

    def to_config_format(self) -> Dict[str, Any]:
        """Convert to config file format."""
        return {
            "match": self.pattern,
            "checks": [
                {"type": c, "confidence": round(self.confidence, 2)} for c in self.suggested_checks
            ],
        }


class PatternLearner:
    """
    Learns column naming patterns from existing configurations.

    Analyzes user's existing column-level configs to identify patterns
    in their naming conventions and check preferences.
    """

    # Common suffixes that indicate patterns
    COMMON_SUFFIXES = [
        "_at",
        "_on",
        "_date",
        "_time",
        "_timestamp",
        "_id",
        "_key",
        "_uuid",
        "_guid",
        "_email",
        "_phone",
        "_url",
        "_status",
        "_type",
        "_flag",
        "_count",
        "_amount",
        "_price",
    ]

    # Common prefixes
    COMMON_PREFIXES = [
        "is_",
        "has_",
        "can_",
        "should_",
        "created_",
        "updated_",
        "deleted_",
        "num_",
        "total_",
    ]

    def __init__(
        self,
        min_occurrences: int = 2,
        min_confidence: float = 0.5,
    ):
        """
        Initialize pattern learner.

        Args:
            min_occurrences: Minimum occurrences to consider a pattern
            min_confidence: Minimum confidence for learned patterns
        """
        self.min_occurrences = min_occurrences
        self.min_confidence = min_confidence

        # Pattern tracking
        self._suffix_patterns: Dict[str, List[Tuple[str, List[str]]]] = defaultdict(list)
        self._prefix_patterns: Dict[str, List[Tuple[str, List[str]]]] = defaultdict(list)
        self._exact_patterns: Dict[str, List[str]] = defaultdict(list)
        self._check_by_type: Dict[str, Counter] = defaultdict(Counter)

    def learn_from_config(self, config: Dict[str, Any]) -> List[LearnedPattern]:
        """
        Learn patterns from a configuration dictionary.

        Args:
            config: Configuration dictionary with column configurations

        Returns:
            List of learned patterns
        """
        # Extract column configurations
        column_configs = self._extract_column_configs(config)

        # Learn from each column
        for col_name, checks in column_configs.items():
            self._learn_from_column(col_name, checks)

        # Generate patterns
        return self._generate_patterns()

    def learn_from_columns(
        self,
        columns: List[Dict[str, Any]],
    ) -> List[LearnedPattern]:
        """
        Learn patterns from a list of column configurations.

        Args:
            columns: List of column config dictionaries

        Returns:
            List of learned patterns
        """
        for col_config in columns:
            col_name = col_config.get("name", "")
            if not col_name:
                continue

            checks = self._extract_checks_from_column_config(col_config)
            if checks:
                self._learn_from_column(col_name, checks)

        return self._generate_patterns()

    def _extract_column_configs(
        self,
        config: Dict[str, Any],
    ) -> Dict[str, List[str]]:
        """Extract column name to check type mappings from config."""
        result = {}

        # Look for profiling.tables.columns structure
        profiling = config.get("profiling", {})
        tables = profiling.get("tables", [])

        for table in tables:
            if not isinstance(table, dict):
                continue

            columns = table.get("columns", [])
            for col in columns:
                if not isinstance(col, dict):
                    continue

                col_name = col.get("name", "")
                if not col_name or "*" in col_name:  # Skip patterns
                    continue

                checks = self._extract_checks_from_column_config(col)
                if checks:
                    result[col_name] = checks

        # Also check validation rules
        validation = config.get("validation", {})
        rules = validation.get("rules", [])

        for rule in rules:
            if not isinstance(rule, dict):
                continue

            col_name = rule.get("column", "")
            rule_type = rule.get("type", "")

            if col_name and rule_type:
                if col_name not in result:
                    result[col_name] = []
                result[col_name].append(rule_type)

        return result

    def _extract_checks_from_column_config(
        self,
        col_config: Dict[str, Any],
    ) -> List[str]:
        """Extract check types from a column configuration."""
        checks = []

        # Check for explicit checks
        if "checks" in col_config:
            for check in col_config["checks"]:
                if isinstance(check, dict):
                    check_type = check.get("type", "")
                    if check_type:
                        checks.append(check_type)
                elif isinstance(check, str):
                    checks.append(check)

        # Check for drift configuration
        drift = col_config.get("drift", {})
        if drift and drift.get("enabled", True):
            checks.append("distribution")

        # Check for anomaly configuration
        anomaly = col_config.get("anomaly", {})
        if anomaly and anomaly.get("enabled", True):
            checks.append("outlier_detection")

        return checks

    def _learn_from_column(self, col_name: str, checks: List[str]) -> None:
        """Learn from a single column configuration."""
        col_name_lower = col_name.lower()

        # Track by data type inferred from checks
        for check in checks:
            self._check_by_type[check][col_name] += 1

        # Learn suffix patterns
        for suffix in self.COMMON_SUFFIXES:
            if col_name_lower.endswith(suffix):
                self._suffix_patterns[suffix].append((col_name, checks))
                break

        # Learn prefix patterns
        for prefix in self.COMMON_PREFIXES:
            if col_name_lower.startswith(prefix):
                self._prefix_patterns[prefix].append((col_name, checks))
                break

        # Track exact names for common columns
        if col_name_lower in ("id", "uuid", "email", "status", "type", "created_at", "updated_at"):
            self._exact_patterns[col_name_lower].extend(checks)

    def _generate_patterns(self) -> List[LearnedPattern]:
        """Generate patterns from learned data."""
        patterns = []

        # Generate suffix patterns
        for suffix, occurrences in self._suffix_patterns.items():
            if len(occurrences) >= self.min_occurrences:
                pattern = self._create_suffix_pattern(suffix, occurrences)
                if pattern:
                    patterns.append(pattern)

        # Generate prefix patterns
        for prefix, occurrences in self._prefix_patterns.items():
            if len(occurrences) >= self.min_occurrences:
                pattern = self._create_prefix_pattern(prefix, occurrences)
                if pattern:
                    patterns.append(pattern)

        # Generate exact patterns
        for name, checks in self._exact_patterns.items():
            if len(checks) >= self.min_occurrences:
                pattern = self._create_exact_pattern(name, checks)
                if pattern:
                    patterns.append(pattern)

        # Sort by confidence
        patterns.sort(key=lambda p: p.confidence, reverse=True)

        return patterns

    def _create_suffix_pattern(
        self,
        suffix: str,
        occurrences: List[Tuple[str, List[str]]],
    ) -> Optional[LearnedPattern]:
        """Create a pattern from suffix occurrences."""
        # Count check type frequencies
        check_counts: Counter[str] = Counter()
        for _, checks in occurrences:
            for check in checks:
                check_counts[check] += 1

        # Get common checks (appear in majority of occurrences)
        total = len(occurrences)
        common_checks = [check for check, count in check_counts.items() if count / total >= 0.5]

        if not common_checks:
            return None

        # Calculate confidence based on consistency
        consistency = sum(check_counts[c] for c in common_checks) / (total * len(common_checks))
        confidence = min(0.95, 0.5 + (consistency * 0.45))

        if confidence < self.min_confidence:
            return None

        return LearnedPattern(
            pattern=f"*{suffix}",
            pattern_type="suffix",
            suggested_checks=common_checks,
            confidence=confidence,
            source_columns=[col for col, _ in occurrences],
            occurrence_count=total,
            metadata={"suffix": suffix},
        )

    def _create_prefix_pattern(
        self,
        prefix: str,
        occurrences: List[Tuple[str, List[str]]],
    ) -> Optional[LearnedPattern]:
        """Create a pattern from prefix occurrences."""
        check_counts: Counter[str] = Counter()
        for _, checks in occurrences:
            for check in checks:
                check_counts[check] += 1

        total = len(occurrences)
        common_checks = [check for check, count in check_counts.items() if count / total >= 0.5]

        if not common_checks:
            return None

        consistency = sum(check_counts[c] for c in common_checks) / (total * len(common_checks))
        confidence = min(0.95, 0.5 + (consistency * 0.45))

        if confidence < self.min_confidence:
            return None

        return LearnedPattern(
            pattern=f"{prefix}*",
            pattern_type="prefix",
            suggested_checks=common_checks,
            confidence=confidence,
            source_columns=[col for col, _ in occurrences],
            occurrence_count=total,
            metadata={"prefix": prefix},
        )

    def _create_exact_pattern(
        self,
        name: str,
        checks: List[str],
    ) -> Optional[LearnedPattern]:
        """Create a pattern from exact name occurrences."""
        check_counts = Counter(checks)
        total = len(checks)

        # Get the most common check
        most_common = check_counts.most_common(3)
        common_checks = [check for check, count in most_common if count / total >= 0.3]

        if not common_checks:
            return None

        confidence = min(0.95, 0.6 + (most_common[0][1] / total * 0.35))

        if confidence < self.min_confidence:
            return None

        return LearnedPattern(
            pattern=name,
            pattern_type="exact",
            suggested_checks=common_checks,
            confidence=confidence,
            source_columns=[name],
            occurrence_count=total,
            metadata={"exact_match": True},
        )

    def reset(self) -> None:
        """Reset learned patterns."""
        self._suffix_patterns.clear()
        self._prefix_patterns.clear()
        self._exact_patterns.clear()
        self._check_by_type.clear()

    def get_learning_summary(self) -> Dict[str, Any]:
        """Get a summary of learned patterns."""
        return {
            "suffix_patterns": len(self._suffix_patterns),
            "prefix_patterns": len(self._prefix_patterns),
            "exact_patterns": len(self._exact_patterns),
            "check_types_observed": list(self._check_by_type.keys()),
        }
