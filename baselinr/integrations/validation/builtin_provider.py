"""
Built-in validation provider for Baselinr.

Implements common validators using the built-in validator modules.
"""

import logging

from sqlalchemy.engine import Engine

from ...validation.validators import (
    EnumValidator,
    FormatValidator,
    NullValidator,
    RangeValidator,
    ReferentialValidator,
    UniquenessValidator,
)
from .base import ValidationProvider, ValidationResult, ValidationRule

logger = logging.getLogger(__name__)


class BuiltinValidationProvider(ValidationProvider):
    """Built-in validation provider using common validators."""

    def __init__(self, engine: Engine):
        """
        Initialize built-in validation provider.

        Args:
            engine: SQLAlchemy engine for database connection
        """
        self.engine = engine
        self.format_validator = FormatValidator(engine)
        self.range_validator = RangeValidator(engine)
        self.enum_validator = EnumValidator(engine)
        self.null_validator = NullValidator(engine)
        self.uniqueness_validator = UniquenessValidator(engine)
        self.referential_validator = ReferentialValidator(engine)

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "builtin"

    def is_available(self) -> bool:
        """
        Check if built-in provider is available.

        Returns:
            True (built-in provider is always available)
        """
        return True

    def validate_rule(self, rule: ValidationRule) -> ValidationResult:
        """
        Execute a validation rule using the appropriate validator.

        Args:
            rule: ValidationRule to execute

        Returns:
            ValidationResult with pass/fail status
        """
        if not rule.enabled:
            logger.debug(f"Skipping disabled rule: {rule.rule_type} on {rule.table}.{rule.column}")
            return ValidationResult(
                rule=rule,
                passed=True,
                failure_reason=None,
                total_rows=0,
                failed_rows=0,
                failure_rate=0.0,
                metadata={"skipped": True, "reason": "rule disabled"},
            )

        try:
            if rule.rule_type == "format":
                return self.format_validator.validate(rule)
            elif rule.rule_type == "range":
                return self.range_validator.validate(rule)
            elif rule.rule_type == "enum":
                return self.enum_validator.validate(rule)
            elif rule.rule_type == "not_null":
                return self.null_validator.validate(rule)
            elif rule.rule_type == "unique":
                return self.uniqueness_validator.validate(rule)
            elif rule.rule_type == "referential":
                return self.referential_validator.validate(rule)
            else:
                return ValidationResult(
                    rule=rule,
                    passed=False,
                    failure_reason=f"Unknown rule type: {rule.rule_type}",
                    total_rows=0,
                    failed_rows=0,
                    failure_rate=0.0,
                )
        except Exception as e:
            logger.error(
                f"Error validating rule {rule.rule_type} on {rule.table}.{rule.column}: {e}",
                exc_info=True,
            )
            return ValidationResult(
                rule=rule,
                passed=False,
                failure_reason=f"Validation error: {str(e)}",
                total_rows=0,
                failed_rows=0,
                failure_rate=0.0,
            )
