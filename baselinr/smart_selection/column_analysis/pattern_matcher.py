"""
Pattern matcher for column naming conventions.

Identifies column naming patterns and matches them against
known conventions for check inference.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PatternMatch:
    """Result of pattern matching on a column."""

    pattern_name: str
    pattern_type: str  # 'name', 'type', 'format', 'semantic'
    confidence: float = 0.0
    matched_rule: Optional[str] = None
    suggested_checks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_name": self.pattern_name,
            "pattern_type": self.pattern_type,
            "confidence": self.confidence,
            "matched_rule": self.matched_rule,
            "suggested_checks": self.suggested_checks,
            "metadata": self.metadata,
        }


@dataclass
class PatternRule:
    """A pattern matching rule."""

    name: str
    patterns: List[str]  # Regex patterns to match
    pattern_type: str  # 'name', 'type', 'format'
    suggested_checks: List[str]
    confidence: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)


class PatternMatcher:
    """Matches columns against known naming patterns."""

    # Built-in pattern rules
    DEFAULT_RULES: List[PatternRule] = [
        # Timestamp patterns
        PatternRule(
            name="timestamp_created",
            patterns=[r"^created_?at$", r"^created_?on$", r"^created_?time$", r"^creation_?date$"],
            pattern_type="name",
            suggested_checks=["freshness", "completeness", "valid_date_range"],
            confidence=0.95,
            metadata={"semantic_type": "timestamp", "category": "audit"},
        ),
        PatternRule(
            name="timestamp_updated",
            patterns=[
                r"^updated_?at$",
                r"^updated_?on$",
                r"^modified_?at$",
                r"^modified_?on$",
                r"^last_?modified",
            ],
            pattern_type="name",
            suggested_checks=["freshness", "completeness"],
            confidence=0.95,
            metadata={"semantic_type": "timestamp", "category": "audit"},
        ),
        PatternRule(
            name="timestamp_deleted",
            patterns=[r"^deleted_?at$", r"^deleted_?on$", r"^deletion_?date$"],
            pattern_type="name",
            suggested_checks=["valid_date_range"],
            confidence=0.90,
            metadata={"semantic_type": "timestamp", "category": "audit", "soft_delete": True},
        ),
        PatternRule(
            name="timestamp_generic",
            patterns=[r".*_at$", r".*_time$", r".*_date$", r".*_timestamp$", r"^timestamp.*"],
            pattern_type="name",
            suggested_checks=["freshness", "valid_date_range"],
            confidence=0.85,
            metadata={"semantic_type": "timestamp"},
        ),
        # Identifier patterns
        PatternRule(
            name="primary_key",
            patterns=[r"^id$", r"^pk_.*", r".*_pk$"],
            pattern_type="name",
            suggested_checks=["uniqueness", "completeness"],
            confidence=0.95,
            metadata={"semantic_type": "identifier", "key_type": "primary"},
        ),
        PatternRule(
            name="foreign_key",
            patterns=[r".*_id$", r"^fk_.*", r".*_fk$"],
            pattern_type="name",
            suggested_checks=["completeness", "referential_integrity"],
            confidence=0.85,
            metadata={"semantic_type": "identifier", "key_type": "foreign"},
        ),
        PatternRule(
            name="uuid_column",
            patterns=[r"^uuid$", r".*_uuid$", r"^guid$", r".*_guid$"],
            pattern_type="name",
            suggested_checks=["uniqueness", "completeness", "format_uuid"],
            confidence=0.95,
            metadata={"semantic_type": "identifier", "format": "uuid"},
        ),
        # Email patterns
        PatternRule(
            name="email",
            patterns=[r"^email$", r".*_email$", r"^email_?address$", r".*_email_?address$"],
            pattern_type="name",
            suggested_checks=["format_email", "completeness"],
            confidence=0.95,
            metadata={"semantic_type": "string", "format": "email"},
        ),
        # Phone patterns
        PatternRule(
            name="phone",
            patterns=[
                r"^phone$",
                r".*_phone$",
                r"^phone_?number$",
                r".*_phone_?number$",
                r"^tel$",
                r".*_tel$",
                r"^mobile$",
                r".*_mobile$",
            ],
            pattern_type="name",
            suggested_checks=["format_phone"],
            confidence=0.90,
            metadata={"semantic_type": "string", "format": "phone"},
        ),
        # URL patterns
        PatternRule(
            name="url",
            patterns=[
                r"^url$",
                r".*_url$",
                r"^link$",
                r".*_link$",
                r"^website$",
                r".*_website$",
                r"^href$",
            ],
            pattern_type="name",
            suggested_checks=["format_url"],
            confidence=0.90,
            metadata={"semantic_type": "string", "format": "url"},
        ),
        # Monetary patterns
        PatternRule(
            name="monetary",
            patterns=[
                r"^amount$",
                r".*_amount$",
                r"^price$",
                r".*_price$",
                r"^cost$",
                r".*_cost$",
                r"^revenue$",
                r".*_revenue$",
                r"^balance$",
                r".*_balance$",
                r"^fee$",
                r".*_fee$",
                r"^total$",
                r".*_total$",
            ],
            pattern_type="name",
            suggested_checks=["non_negative", "range", "distribution"],
            confidence=0.90,
            metadata={"semantic_type": "numeric", "category": "monetary"},
        ),
        # Count patterns
        PatternRule(
            name="count",
            patterns=[
                r"^count$",
                r".*_count$",
                r"^quantity$",
                r".*_quantity$",
                r"^qty$",
                r".*_qty$",
                r"^num_.*",
                r".*_num$",
            ],
            pattern_type="name",
            suggested_checks=["non_negative", "range"],
            confidence=0.90,
            metadata={"semantic_type": "numeric", "category": "count"},
        ),
        # Percentage/rate patterns
        PatternRule(
            name="percentage",
            patterns=[
                r"^percent$",
                r".*_percent$",
                r"^pct$",
                r".*_pct$",
                r"^rate$",
                r".*_rate$",
                r"^ratio$",
                r".*_ratio$",
            ],
            pattern_type="name",
            suggested_checks=["range_0_100", "range_0_1"],
            confidence=0.85,
            metadata={"semantic_type": "numeric", "category": "percentage"},
        ),
        # Status/type patterns
        PatternRule(
            name="status",
            patterns=[r"^status$", r".*_status$", r"^state$", r".*_state$"],
            pattern_type="name",
            suggested_checks=["allowed_values", "completeness"],
            confidence=0.90,
            metadata={"semantic_type": "categorical", "category": "status"},
        ),
        PatternRule(
            name="type_category",
            patterns=[
                r"^type$",
                r".*_type$",
                r"^category$",
                r".*_category$",
                r"^kind$",
                r".*_kind$",
                r"^class$",
                r".*_class$",
            ],
            pattern_type="name",
            suggested_checks=["allowed_values"],
            confidence=0.85,
            metadata={"semantic_type": "categorical"},
        ),
        # Boolean patterns
        PatternRule(
            name="boolean_is",
            patterns=[r"^is_.*", r"^has_.*", r"^can_.*", r"^should_.*", r"^was_.*", r"^will_.*"],
            pattern_type="name",
            suggested_checks=["completeness", "boolean_values"],
            confidence=0.95,
            metadata={"semantic_type": "boolean"},
        ),
        PatternRule(
            name="boolean_flag",
            patterns=[
                r".*_flag$",
                r"^active$",
                r"^enabled$",
                r"^disabled$",
                r"^deleted$",
                r"^verified$",
                r"^visible$",
                r"^hidden$",
            ],
            pattern_type="name",
            suggested_checks=["completeness", "boolean_values"],
            confidence=0.90,
            metadata={"semantic_type": "boolean"},
        ),
        # Geographic patterns
        PatternRule(
            name="country",
            patterns=[r"^country$", r".*_country$", r"^country_?code$", r".*_country_?code$"],
            pattern_type="name",
            suggested_checks=["allowed_values", "format_iso_country"],
            confidence=0.85,
            metadata={"semantic_type": "geographic", "category": "country"},
        ),
        PatternRule(
            name="zipcode",
            patterns=[
                r"^zip$",
                r".*_zip$",
                r"^zip_?code$",
                r".*_zip_?code$",
                r"^postal$",
                r".*_postal$",
                r"^postal_?code$",
            ],
            pattern_type="name",
            suggested_checks=["format_zipcode"],
            confidence=0.85,
            metadata={"semantic_type": "geographic", "category": "postal"},
        ),
        # JSON patterns
        PatternRule(
            name="json_column",
            patterns=[r".*_json$", r"^json_.*", r"^metadata$", r".*_metadata$", r"^config$"],
            pattern_type="name",
            suggested_checks=["valid_json"],
            confidence=0.80,
            metadata={"semantic_type": "json"},
        ),
    ]

    def __init__(
        self,
        custom_rules: Optional[List[PatternRule]] = None,
        include_defaults: bool = True,
    ):
        """
        Initialize pattern matcher.

        Args:
            custom_rules: Optional custom pattern rules to add
            include_defaults: Whether to include default rules
        """
        self.rules: List[PatternRule] = []

        if include_defaults:
            self.rules.extend(self.DEFAULT_RULES)

        if custom_rules:
            self.rules.extend(custom_rules)

        # Compile regex patterns
        self._compiled_rules: List[tuple] = []
        for rule in self.rules:
            compiled_patterns = [re.compile(p, re.IGNORECASE) for p in rule.patterns]
            self._compiled_rules.append((rule, compiled_patterns))

    def match_column(
        self,
        column_name: str,
        column_type: Optional[str] = None,
        data_type_base: Optional[str] = None,
    ) -> List[PatternMatch]:
        """
        Match a column against all patterns.

        Args:
            column_name: Column name to match
            column_type: Full column type string (e.g., 'VARCHAR(255)')
            data_type_base: Base data type (e.g., 'varchar')

        Returns:
            List of PatternMatch objects, sorted by confidence (descending)
        """
        matches = []

        for rule, compiled_patterns in self._compiled_rules:
            if rule.pattern_type == "name":
                # Match against column name
                for pattern in compiled_patterns:
                    if pattern.match(column_name):
                        match = PatternMatch(
                            pattern_name=rule.name,
                            pattern_type=rule.pattern_type,
                            confidence=rule.confidence,
                            matched_rule=pattern.pattern,
                            suggested_checks=rule.suggested_checks.copy(),
                            metadata=rule.metadata.copy(),
                        )
                        matches.append(match)
                        break  # Only one match per rule

            elif rule.pattern_type == "type" and data_type_base:
                # Match against data type
                for pattern in compiled_patterns:
                    if pattern.match(data_type_base):
                        match = PatternMatch(
                            pattern_name=rule.name,
                            pattern_type=rule.pattern_type,
                            confidence=rule.confidence,
                            matched_rule=pattern.pattern,
                            suggested_checks=rule.suggested_checks.copy(),
                            metadata=rule.metadata.copy(),
                        )
                        matches.append(match)
                        break

        # Sort by confidence (descending)
        matches.sort(key=lambda x: x.confidence, reverse=True)

        return matches

    def add_rule(self, rule: PatternRule) -> None:
        """
        Add a custom pattern rule.

        Args:
            rule: PatternRule to add
        """
        self.rules.append(rule)
        compiled_patterns = [re.compile(p, re.IGNORECASE) for p in rule.patterns]
        self._compiled_rules.append((rule, compiled_patterns))

    def get_all_rules(self) -> List[PatternRule]:
        """Get all registered pattern rules."""
        return self.rules.copy()

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "PatternMatcher":
        """
        Create PatternMatcher from configuration.

        Args:
            config: Configuration dictionary with 'patterns' key

        Returns:
            PatternMatcher instance
        """
        custom_rules = []
        patterns_config = config.get("patterns", [])

        for pattern_cfg in patterns_config:
            if not isinstance(pattern_cfg, dict):
                continue

            match_pattern = pattern_cfg.get("match", "")
            if not match_pattern:
                continue

            # Convert simple match to regex
            if "*" in match_pattern or "?" in match_pattern:
                # Wildcard pattern - convert to regex
                regex_pattern = (
                    match_pattern.replace(".", r"\.").replace("*", ".*").replace("?", ".")
                )
                regex_pattern = f"^{regex_pattern}$"
            else:
                regex_pattern = f"^{re.escape(match_pattern)}$"

            checks = []
            for check_cfg in pattern_cfg.get("checks", []):
                if isinstance(check_cfg, dict):
                    checks.append(check_cfg.get("type", ""))
                elif isinstance(check_cfg, str):
                    checks.append(check_cfg)

            rule = PatternRule(
                name=f"custom_{match_pattern}",
                patterns=[regex_pattern],
                pattern_type="name",
                suggested_checks=checks,
                confidence=float(pattern_cfg.get("confidence", 0.9)),
                metadata=pattern_cfg.get("metadata", {}),
            )
            custom_rules.append(rule)

        return cls(custom_rules=custom_rules, include_defaults=True)
