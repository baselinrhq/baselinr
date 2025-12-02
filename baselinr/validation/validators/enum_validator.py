"""
Enum validator for Baselinr.

Validates that column values are in a list of allowed values.
"""

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ...integrations.validation.base import ValidationResult, ValidationRule

logger = logging.getLogger(__name__)


class EnumValidator:
    """Validates column values against a list of allowed values."""

    def __init__(self, engine: Engine):
        """
        Initialize enum validator.

        Args:
            engine: SQLAlchemy engine for database connection
        """
        self.engine = engine

    def validate(self, rule: ValidationRule, max_sample_failures: int = 10) -> ValidationResult:
        """
        Validate column values against allowed values list.

        Args:
            rule: ValidationRule with type='enum' and allowed_values in config
            max_sample_failures: Maximum number of sample failures to return

        Returns:
            ValidationResult with pass/fail status
        """
        if rule.rule_type != "enum":
            raise ValueError(
                f"EnumValidator can only validate 'enum' rules, got '{rule.rule_type}'"
            )

        if not rule.column:
            raise ValueError("Enum validation requires a column name")

        allowed_values = rule.config.get("allowed_values")
        if not allowed_values or not isinstance(allowed_values, list):
            raise ValueError("Enum validation requires 'allowed_values' list in config")

        schema_prefix = f'"{rule.schema}".' if rule.schema else ""
        table_name = f'{schema_prefix}"{rule.table}"'

        try:
            with self.engine.connect() as conn:
                # Count total rows
                total_query = text(f"SELECT COUNT(*) as cnt FROM {table_name}")
                total_result = conn.execute(total_query).fetchone()
                total_rows = total_result[0] if total_result else 0

                if total_rows == 0:
                    return ValidationResult(
                        rule=rule,
                        passed=True,
                        total_rows=0,
                        failed_rows=0,
                        failure_rate=0.0,
                    )

                # Build WHERE clause for enum validation
                # Use IN clause for allowed values
                placeholders = ", ".join([f":val_{i}" for i in range(len(allowed_values))])
                where_clause = (
                    f'"{rule.column}" IS NOT NULL AND "{rule.column}" NOT IN ({placeholders})'
                )

                params = {f"val_{i}": val for i, val in enumerate(allowed_values)}

                # Count failures
                count_query = text(f"SELECT COUNT(*) as cnt FROM {table_name} WHERE {where_clause}")
                count_result = conn.execute(count_query, params).fetchone()
                failed_rows = count_result[0] if count_result else 0

                # Get sample failures
                sample_failures = []
                if failed_rows > 0:
                    sample_query = text(
                        f'SELECT "{rule.column}" FROM {table_name} '
                        f"WHERE {where_clause} LIMIT :limit"
                    )
                    params["limit"] = max_sample_failures
                    rows = conn.execute(sample_query, params).fetchall()
                    sample_failures = [{rule.column: row[0]} for row in rows]

                failure_rate = (failed_rows / total_rows) * 100.0 if total_rows > 0 else 0.0
                passed = failed_rows == 0

                return ValidationResult(
                    rule=rule,
                    passed=passed,
                    failure_reason=(
                        f"{failed_rows} out of {total_rows} rows failed enum validation "
                        f"(allowed: {allowed_values})"
                        if not passed
                        else None
                    ),
                    total_rows=total_rows,
                    failed_rows=failed_rows,
                    failure_rate=failure_rate,
                    sample_failures=sample_failures,
                )

        except Exception as e:
            logger.error(f"Error executing enum validation: {e}", exc_info=True)
            return ValidationResult(
                rule=rule,
                passed=False,
                failure_reason=f"Validation error: {str(e)}",
                total_rows=0,
                failed_rows=0,
                failure_rate=0.0,
            )
