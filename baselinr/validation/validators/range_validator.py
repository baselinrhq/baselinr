"""
Range validator for Baselinr.

Validates numeric values against min/max ranges and string lengths.
"""

import logging
from typing import Any, Dict

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ...integrations.validation.base import ValidationResult, ValidationRule

logger = logging.getLogger(__name__)


class RangeValidator:
    """Validates column values against numeric or length ranges."""

    def __init__(self, engine: Engine):
        """
        Initialize range validator.

        Args:
            engine: SQLAlchemy engine for database connection
        """
        self.engine = engine

    def validate(self, rule: ValidationRule, max_sample_failures: int = 10) -> ValidationResult:
        """
        Validate column values against a range (min/max).

        Args:
            rule: ValidationRule with type='range' and min_value/max_value in config
            max_sample_failures: Maximum number of sample failures to return

        Returns:
            ValidationResult with pass/fail status
        """
        if rule.rule_type != "range":
            raise ValueError(
                f"RangeValidator can only validate 'range' rules, got '{rule.rule_type}'"
            )

        if not rule.column:
            raise ValueError("Range validation requires a column name")

        min_value = rule.config.get("min_value")
        max_value = rule.config.get("max_value")

        if min_value is None and max_value is None:
            raise ValueError(
                "Range validation requires at least 'min_value' or 'max_value' in config"
            )

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

                # Build WHERE clause for range validation
                conditions = []
                params: Dict[str, Any] = {}

                if min_value is not None:
                    conditions.append(f'"{rule.column}" < :min_value')
                    params["min_value"] = min_value

                if max_value is not None:
                    conditions.append(f'"{rule.column}" > :max_value')
                    params["max_value"] = max_value

                # Only check non-null values
                where_clause = f'"{rule.column}" IS NOT NULL'
                if conditions:
                    where_clause += f" AND ({' OR '.join(conditions)})"

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

                range_desc = []
                if min_value is not None:
                    range_desc.append(f"min={min_value}")
                if max_value is not None:
                    range_desc.append(f"max={max_value}")

                return ValidationResult(
                    rule=rule,
                    passed=passed,
                    failure_reason=(
                        f"{failed_rows} out of {total_rows} rows failed range validation "
                        f"({', '.join(range_desc)})"
                        if not passed
                        else None
                    ),
                    total_rows=total_rows,
                    failed_rows=failed_rows,
                    failure_rate=failure_rate,
                    sample_failures=sample_failures,
                )

        except Exception as e:
            logger.error(f"Error executing range validation: {e}", exc_info=True)
            return ValidationResult(
                rule=rule,
                passed=False,
                failure_reason=f"Validation error: {str(e)}",
                total_rows=0,
                failed_rows=0,
                failure_rate=0.0,
            )
