"""
Format validator for Baselinr.

Validates data against format patterns (email, URL, phone, regex).
"""

import logging
import re

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ...integrations.validation.base import ValidationResult, ValidationRule

logger = logging.getLogger(__name__)

# Common format patterns
FORMAT_PATTERNS = {
    "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    "url": r"^https?://[^\s/$.?#].[^\s]*$",
    "phone": r"^\+?[\d\s\-\(\)]{10,}$",
}


class FormatValidator:
    """Validates column values against format patterns."""

    def __init__(self, engine: Engine):
        """
        Initialize format validator.

        Args:
            engine: SQLAlchemy engine for database connection
        """
        self.engine = engine

    def validate(self, rule: ValidationRule, max_sample_failures: int = 10) -> ValidationResult:
        """
        Validate column values against a format pattern.

        Args:
            rule: ValidationRule with type='format' and pattern in config
            max_sample_failures: Maximum number of sample failures to return

        Returns:
            ValidationResult with pass/fail status
        """
        if rule.rule_type != "format":
            raise ValueError(
                f"FormatValidator can only validate 'format' rules, got '{rule.rule_type}'"
            )

        if not rule.column:
            raise ValueError("Format validation requires a column name")

        pattern = rule.config.get("pattern")
        if not pattern:
            raise ValueError("Format validation requires a 'pattern' in config")

        # Use predefined pattern if available, otherwise use provided pattern
        actual_pattern = FORMAT_PATTERNS.get(pattern.lower(), pattern)

        try:
            # Compile regex to validate it
            regex = re.compile(actual_pattern)
        except re.error as e:
            return ValidationResult(
                rule=rule,
                passed=False,
                failure_reason=f"Invalid regex pattern: {e}",
                total_rows=0,
                failed_rows=0,
                failure_rate=0.0,
            )

        schema_prefix = f'"{rule.schema}".' if rule.schema else ""
        table_name = f'{schema_prefix}"{rule.table}"'

        # Get database dialect to use appropriate regex function
        dialect = self.engine.dialect.name

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

                # Find rows that don't match the pattern
                if dialect == "postgresql":
                    # PostgreSQL uses ~ operator for regex
                    where_clause = f'"{rule.column}" IS NOT NULL AND "{rule.column}" !~ :pattern'
                elif dialect == "mysql":
                    # MySQL uses REGEXP
                    where_clause = (
                        f"`{rule.column}` IS NOT NULL AND `{rule.column}` NOT REGEXP :pattern"
                    )
                elif dialect == "snowflake":
                    # Snowflake uses REGEXP_LIKE
                    where_clause = (
                        f'"{rule.column}" IS NOT NULL AND '
                        f'NOT REGEXP_LIKE("{rule.column}", :pattern)'
                    )
                elif dialect == "sqlite":
                    # SQLite doesn't have native regex, use LIKE as fallback (limited)
                    # For proper regex, we'd need to use Python regex
                    where_clause = f'"{rule.column}" IS NOT NULL'
                else:
                    # Generic fallback - try PostgreSQL syntax
                    where_clause = f'"{rule.column}" IS NOT NULL AND "{rule.column}" !~ :pattern'

                # Count failures
                count_query = text(f"SELECT COUNT(*) as cnt FROM {table_name} WHERE {where_clause}")
                count_result = conn.execute(count_query, {"pattern": actual_pattern}).fetchone()
                failed_rows = count_result[0] if count_result else 0

                # Get sample failures
                sample_failures = []
                if failed_rows > 0:
                    if dialect == "sqlite":
                        # For SQLite, fetch all and filter in Python
                        sample_query = text(
                            f'SELECT "{rule.column}" FROM {table_name} '
                            f'WHERE "{rule.column}" IS NOT NULL LIMIT 1000'
                        )
                        rows = conn.execute(sample_query).fetchall()
                        for row in rows:
                            value = row[0]
                            if value and not regex.match(str(value)):
                                sample_failures.append({rule.column: value})
                                if len(sample_failures) >= max_sample_failures:
                                    break
                    else:
                        # For other databases, use SQL regex
                        sample_query = text(
                            f'SELECT "{rule.column}" FROM {table_name} '
                            f"WHERE {where_clause} LIMIT :limit"
                        )
                        rows = conn.execute(
                            sample_query, {"pattern": actual_pattern, "limit": max_sample_failures}
                        ).fetchall()
                        sample_failures = [{rule.column: row[0]} for row in rows]

                failure_rate = (failed_rows / total_rows) * 100.0 if total_rows > 0 else 0.0
                passed = failed_rows == 0

                return ValidationResult(
                    rule=rule,
                    passed=passed,
                    failure_reason=(
                        f"{failed_rows} out of {total_rows} rows failed format validation"
                        if not passed
                        else None
                    ),
                    total_rows=total_rows,
                    failed_rows=failed_rows,
                    failure_rate=failure_rate,
                    sample_failures=sample_failures,
                )

        except Exception as e:
            logger.error(f"Error executing format validation: {e}", exc_info=True)
            return ValidationResult(
                rule=rule,
                passed=False,
                failure_reason=f"Validation error: {str(e)}",
                total_rows=0,
                failed_rows=0,
                failure_rate=0.0,
            )
