"""
Referential integrity validator for Baselinr.

Validates foreign key relationships between tables.
"""

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ...integrations.validation.base import ValidationResult, ValidationRule

logger = logging.getLogger(__name__)


class ReferentialValidator:
    """Validates referential integrity (foreign key relationships)."""

    def __init__(self, engine: Engine):
        """
        Initialize referential validator.

        Args:
            engine: SQLAlchemy engine for database connection
        """
        self.engine = engine

    def validate(self, rule: ValidationRule, max_sample_failures: int = 10) -> ValidationResult:
        """
        Validate referential integrity (foreign key).

        Args:
            rule: ValidationRule with type='referential' and references in config
            max_sample_failures: Maximum number of sample failures to return

        Returns:
            ValidationResult with pass/fail status
        """
        if rule.rule_type != "referential":
            raise ValueError(
                f"ReferentialValidator can only validate 'referential' rules, "
                f"got '{rule.rule_type}'"
            )

        if not rule.column:
            raise ValueError("Referential validation requires a column name")

        references = rule.config.get("references")
        if not references or not isinstance(references, dict):
            raise ValueError(
                "Referential validation requires 'references' dict in config "
                "with 'table' and 'column' keys"
            )

        ref_table = references.get("table")
        ref_column = references.get("column")

        if not ref_table or not ref_column:
            raise ValueError("References must contain 'table' and 'column' keys")

        ref_schema = references.get("schema", rule.schema)

        schema_prefix = f'"{rule.schema}".' if rule.schema else ""
        table_name = f'{schema_prefix}"{rule.table}"'

        ref_schema_prefix = f'"{ref_schema}".' if ref_schema else ""
        ref_table_name = f'{ref_schema_prefix}"{ref_table}"'

        try:
            with self.engine.connect() as conn:
                # Count total rows in source table
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

                # Check if referenced table exists and get valid values
                # Find rows in source table that don't have matching values
                # in referenced table
                where_clause = (
                    f'"{rule.column}" IS NOT NULL AND "{rule.column}" NOT IN '
                    f'(SELECT "{ref_column}" FROM {ref_table_name} '
                    f'WHERE "{ref_column}" IS NOT NULL)'
                )

                # Count failures
                count_query = text(f"SELECT COUNT(*) as cnt FROM {table_name} WHERE {where_clause}")
                count_result = conn.execute(count_query).fetchone()
                failed_rows = count_result[0] if count_result else 0

                # Get sample failures
                sample_failures = []
                if failed_rows > 0:
                    sample_query = text(
                        f'SELECT "{rule.column}" FROM {table_name} '
                        f"WHERE {where_clause} LIMIT :limit"
                    )
                    rows = conn.execute(sample_query, {"limit": max_sample_failures}).fetchall()
                    sample_failures = [{rule.column: row[0]} for row in rows]

                failure_rate = (failed_rows / total_rows) * 100.0 if total_rows > 0 else 0.0
                passed = failed_rows == 0

                return ValidationResult(
                    rule=rule,
                    passed=passed,
                    failure_reason=(
                        f"{failed_rows} out of {total_rows} rows have invalid "
                        f"foreign key references to {ref_table}.{ref_column}"
                        if not passed
                        else None
                    ),
                    total_rows=total_rows,
                    failed_rows=failed_rows,
                    failure_rate=failure_rate,
                    sample_failures=sample_failures,
                )

        except Exception as e:
            logger.error(f"Error executing referential validation: {e}", exc_info=True)
            return ValidationResult(
                rule=rule,
                passed=False,
                failure_reason=f"Validation error: {str(e)}",
                total_rows=0,
                failed_rows=0,
                failure_rate=0.0,
            )
