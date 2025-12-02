"""
Uniqueness validator for Baselinr.

Validates that column values are unique.
"""

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ...integrations.validation.base import ValidationResult, ValidationRule

logger = logging.getLogger(__name__)


class UniquenessValidator:
    """Validates that column values are unique."""

    def __init__(self, engine: Engine):
        """
        Initialize uniqueness validator.

        Args:
            engine: SQLAlchemy engine for database connection
        """
        self.engine = engine

    def validate(self, rule: ValidationRule, max_sample_failures: int = 10) -> ValidationResult:
        """
        Validate that column values are unique.

        Args:
            rule: ValidationRule with type='unique'
            max_sample_failures: Maximum number of sample failures to return

        Returns:
            ValidationResult with pass/fail status
        """
        if rule.rule_type != "unique":
            raise ValueError(
                f"UniquenessValidator can only validate 'unique' rules, got '{rule.rule_type}'"
            )

        if not rule.column:
            raise ValueError("Uniqueness validation requires a column name")

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

                # Count distinct values
                distinct_query = text(
                    f'SELECT COUNT(DISTINCT "{rule.column}") as cnt FROM {table_name} '
                    f'WHERE "{rule.column}" IS NOT NULL'
                )
                distinct_result = conn.execute(distinct_query).fetchone()
                distinct_count = distinct_result[0] if distinct_result else 0

                # Count non-null rows
                non_null_query = text(
                    f'SELECT COUNT(*) as cnt FROM {table_name} WHERE "{rule.column}" IS NOT NULL'
                )
                non_null_result = conn.execute(non_null_query).fetchone()
                non_null_rows = non_null_result[0] if non_null_result else 0

                # Failed rows = non-null rows - distinct count
                failed_rows = non_null_rows - distinct_count

                # Get sample duplicate values
                sample_failures = []
                if failed_rows > 0:
                    duplicate_query = text(
                        f"""
                        SELECT "{rule.column}", COUNT(*) as cnt
                        FROM {table_name}
                        WHERE "{rule.column}" IS NOT NULL
                        GROUP BY "{rule.column}"
                        HAVING COUNT(*) > 1
                        LIMIT :limit
                        """
                    )
                    rows = conn.execute(duplicate_query, {"limit": max_sample_failures}).fetchall()
                    sample_failures = [{rule.column: row[0], "count": row[1]} for row in rows]

                failure_rate = (failed_rows / total_rows) * 100.0 if total_rows > 0 else 0.0
                passed = failed_rows == 0

                return ValidationResult(
                    rule=rule,
                    passed=passed,
                    failure_reason=(
                        f"{failed_rows} duplicate values found "
                        f"(expected {non_null_rows} distinct, found {distinct_count})"
                        if not passed
                        else None
                    ),
                    total_rows=total_rows,
                    failed_rows=failed_rows,
                    failure_rate=failure_rate,
                    sample_failures=sample_failures,
                )

        except Exception as e:
            logger.error(f"Error executing uniqueness validation: {e}", exc_info=True)
            return ValidationResult(
                rule=rule,
                passed=False,
                failure_reason=f"Validation error: {str(e)}",
                total_rows=0,
                failed_rows=0,
                failure_rate=0.0,
            )
