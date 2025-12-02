"""
Base classes for validation providers.

Defines the abstract interface that all validation providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ValidationRule:
    """Represents a single validation rule."""

    rule_type: str  # format, range, enum, not_null, unique, referential
    table: str
    schema: Optional[str] = None
    column: Optional[str] = None  # None for table-level rules
    config: Dict[str, Any] = field(default_factory=dict)  # Rule-specific configuration
    severity: str = "medium"  # low, medium, high
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "rule_type": self.rule_type,
            "table": self.table,
            "schema": self.schema,
            "column": self.column,
            "config": self.config,
            "severity": self.severity,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationRule":
        """Create from dictionary."""
        return cls(
            rule_type=data["rule_type"],
            table=data["table"],
            schema=data.get("schema"),
            column=data.get("column"),
            config=data.get("config", {}),
            severity=data.get("severity", "medium"),
            enabled=data.get("enabled", True),
        )


@dataclass
class ValidationResult:
    """Result from a validation rule execution."""

    rule: ValidationRule
    passed: bool
    failure_reason: Optional[str] = None
    total_rows: int = 0
    failed_rows: int = 0
    failure_rate: float = 0.0
    sample_failures: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "rule": self.rule.to_dict(),
            "passed": self.passed,
            "failure_reason": self.failure_reason,
            "total_rows": self.total_rows,
            "failed_rows": self.failed_rows,
            "failure_rate": self.failure_rate,
            "sample_failures": self.sample_failures,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationResult":
        """Create from dictionary."""
        return cls(
            rule=ValidationRule.from_dict(data["rule"]),
            passed=data["passed"],
            failure_reason=data.get("failure_reason"),
            total_rows=data.get("total_rows", 0),
            failed_rows=data.get("failed_rows", 0),
            failure_rate=data.get("failure_rate", 0.0),
            sample_failures=data.get("sample_failures", []),
            metadata=data.get("metadata", {}),
        )


class ValidationProvider(ABC):
    """
    Abstract base class for validation providers.

    Each provider implements methods to execute validation rules from a specific source
    (built-in validators, Great Expectations, Soda, etc.). Providers are optional and
    should gracefully handle cases where they cannot be used.
    """

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of this provider.

        Returns:
            Provider name (e.g., 'builtin', 'great_expectations', 'soda')
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this provider can be used.

        Returns:
            True if provider is available and can execute validations, False otherwise
        """
        pass

    @abstractmethod
    def validate_rule(self, rule: ValidationRule) -> ValidationResult:
        """
        Execute a single validation rule.

        Args:
            rule: ValidationRule to execute

        Returns:
            ValidationResult with pass/fail status and details
        """
        pass

    def validate_rules(self, rules: List[ValidationRule]) -> List[ValidationResult]:
        """
        Execute multiple validation rules (bulk operation).

        This is optional - providers can implement this for efficiency
        when validating multiple rules.

        Args:
            rules: List of ValidationRule objects to execute

        Returns:
            List of ValidationResult objects
        """
        # Default implementation calls validate_rule for each rule
        return [self.validate_rule(rule) for rule in rules]
