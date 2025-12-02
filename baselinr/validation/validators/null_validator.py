"""
Null validator for Baselinr.

Validates that columns are not null (or are null, depending on rule).
"""

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ...integrations.validation.base import ValidationResult, ValidationRule

logger = logging.getLogger(__name__)


class NullValidator:
    """Validates null/not-null constraints on columns."""

    def __init__(self, engine: Engine):
        """
        Initialize null validator.

        Args:
            engine: SQLAlchemy engine for database connection
        """
        self.engine = engine

    def validate(self, rule: ValidationRule, max_sample_failures: int = 10) -> ValidationResult:
        """
        Validate null/not-null constraint.

        Args:
            rule: ValidationRule with type='not_null'
            max_sample_failures: Maximum number of sample failures to return

        Returns:
            ValidationResult with pass/fail status
        """
        if rule.rule_type != "not_null":
            raise ValueError(
                f"NullValidator can only validate 'not_null' rules, got '{rule.rule_type}'"
            )

        if not rule.column:
            raise ValueError("Not-null validation requires a column name")

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

                # Count null values
                where_clause = f'"{rule.column}" IS NULL'
                count_query = text(f"SELECT COUNT(*) as cnt FROM {table_name} WHERE {where_clause}")
                count_result = conn.execute(count_query).fetchone()
                failed_rows = count_result[0] if count_result else 0

                # Get sample failures (null values don't have samples,
                # but we can show row identifiers)
                sample_failures = []
                if failed_rows > 0:
                    # Try to get a primary key or row identifier
                    # For now, just return count
                    sample_failures = [{"null_count": failed_rows}]

                failure_rate = (failed_rows / total_rows) * 100.0 if total_rows > 0 else 0.0
                passed = failed_rows == 0

                return ValidationResult(
                    rule=rule,
                    passed=passed,
                    failure_reason=(
                        f"{failed_rows} out of {total_rows} rows have NULL values"
                        if not passed
                        else None
                    ),
                    total_rows=total_rows,
                    failed_rows=failed_rows,
                    failure_rate=failure_rate,
                    sample_failures=sample_failures,
                )

        except Exception as e:
            logger.error(f"Error executing null validation: {e}", exc_info=True)
            return ValidationResult(
                rule=rule,
                passed=False,
                failure_reason=f"Validation error: {str(e)}",
                total_rows=0,
                failed_rows=0,
                failure_rate=0.0,
            )
