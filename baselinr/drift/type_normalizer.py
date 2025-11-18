"""
Type normalization utility for Baselinr drift detection.

Maps database-specific column types to standardized categories
for type-specific threshold application.

This module provides functions to normalize database-specific column types
(e.g., "INTEGER", "VARCHAR(255)", "TIMESTAMP") to standardized categories
(numeric, categorical, timestamp, boolean) that are used for applying
type-specific drift detection thresholds.

Example:
    >>> normalize_column_type("INTEGER")
    'numeric'
    >>> normalize_column_type("VARCHAR(255)")
    'categorical'
    >>> normalize_column_type("TIMESTAMP")
    'timestamp'
"""

from typing import Dict, Set

# Type mappings: database type -> category
NUMERIC_TYPES: Set[str] = {
    "integer",
    "int",
    "bigint",
    "smallint",
    "tinyint",
    "numeric",
    "decimal",
    "float",
    "double",
    "real",
    "number",
    "money",
    "smallmoney",
    "real",
    "double precision",
}

CATEGORICAL_TYPES: Set[str] = {
    "varchar",
    "char",
    "text",
    "string",
    "nvarchar",
    "nchar",
    "ntext",
    "enum",
    "character",
    "character varying",
}

TIMESTAMP_TYPES: Set[str] = {
    "timestamp",
    "datetime",
    "date",
    "time",
    "datetime2",
    "smalldatetime",
    "datetimeoffset",
    "timestamp_ntz",
    "timestamp_ltz",
    "timestamp_tz",
}

BOOLEAN_TYPES: Set[str] = {
    "boolean",
    "bool",
    "bit",
}


def normalize_column_type(column_type: str) -> str:
    """
    Normalize database-specific column type to a category.

    Maps database types to one of: numeric, categorical, timestamp, boolean.
    If the type cannot be determined, returns "unknown".

    Args:
        column_type: Database-specific column type (e.g., "INTEGER", "VARCHAR(255)")

    Returns:
        Normalized type category: "numeric", "categorical", "timestamp", "boolean", or "unknown"

    Examples:
        >>> normalize_column_type("INTEGER")
        'numeric'
        >>> normalize_column_type("VARCHAR(255)")
        'categorical'
        >>> normalize_column_type("TIMESTAMP")
        'timestamp'
        >>> normalize_column_type("BOOLEAN")
        'boolean'
        >>> normalize_column_type("UNKNOWN_TYPE")
        'unknown'
    """
    if not column_type:
        return "unknown"

    # Normalize to lowercase and remove whitespace
    normalized = column_type.lower().strip()

    # Remove common type modifiers (e.g., "VARCHAR(255)" -> "varchar")
    # Remove parentheses and everything after
    if "(" in normalized:
        normalized = normalized.split("(")[0].strip()

    # Check each category
    if normalized in NUMERIC_TYPES or any(nt in normalized for nt in NUMERIC_TYPES):
        return "numeric"

    if normalized in CATEGORICAL_TYPES or any(ct in normalized for ct in CATEGORICAL_TYPES):
        return "categorical"

    if normalized in TIMESTAMP_TYPES or any(tt in normalized for tt in TIMESTAMP_TYPES):
        return "timestamp"

    if normalized in BOOLEAN_TYPES or any(bt in normalized for bt in BOOLEAN_TYPES):
        return "boolean"

    return "unknown"


def get_type_category(column_type: str) -> str:
    """
    Alias for normalize_column_type for convenience.

    Args:
        column_type: Database-specific column type

    Returns:
        Normalized type category
    """
    return normalize_column_type(column_type)


def get_type_mappings() -> Dict[str, Set[str]]:
    """
    Get the type mappings for reference.

    Returns:
        Dictionary mapping category names to sets of type strings
    """
    return {
        "numeric": NUMERIC_TYPES,
        "categorical": CATEGORICAL_TYPES,
        "timestamp": TIMESTAMP_TYPES,
        "boolean": BOOLEAN_TYPES,
    }
