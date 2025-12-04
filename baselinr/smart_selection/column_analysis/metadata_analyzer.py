"""
Metadata analyzer for column signals.

Extracts metadata signals from columns including names, types,
nullability, and key status to inform check recommendations.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class InferredColumnType(str, Enum):
    """Inferred semantic type of a column."""

    TIMESTAMP = "timestamp"
    DATE = "date"
    IDENTIFIER = "identifier"
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"
    STRING = "string"
    JSON = "json"
    ARRAY = "array"
    BINARY = "binary"
    UNKNOWN = "unknown"


@dataclass
class ColumnMetadata:
    """Metadata about a column for check inference."""

    # Basic metadata
    name: str
    data_type: str
    nullable: bool = True
    position: int = 0

    # Key information
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_key_references: Optional[str] = None

    # Inferred semantic type
    inferred_type: InferredColumnType = InferredColumnType.UNKNOWN

    # Description/comment if available
    description: Optional[str] = None

    # Pattern signals from name analysis
    name_patterns: List[str] = field(default_factory=list)

    # Raw type info for detailed analysis
    type_length: Optional[int] = None
    type_precision: Optional[int] = None
    type_scale: Optional[int] = None

    # Default value if defined
    has_default: bool = False
    default_value: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "data_type": self.data_type,
            "nullable": self.nullable,
            "position": self.position,
            "is_primary_key": self.is_primary_key,
            "is_foreign_key": self.is_foreign_key,
            "foreign_key_references": self.foreign_key_references,
            "inferred_type": self.inferred_type.value,
            "description": self.description,
            "name_patterns": self.name_patterns,
        }


class MetadataAnalyzer:
    """Analyzes column metadata to extract signals for check inference."""

    # Name patterns for different column types
    TIMESTAMP_PATTERNS = [
        r".*_at$",
        r".*_date$",
        r".*_time$",
        r"^timestamp.*",
        r"^created.*",
        r"^updated.*",
        r"^modified.*",
        r"^deleted.*",
        r"^loaded.*",
        r"^extracted.*",
        r"^processed.*",
        r"^synced.*",
        r".*_timestamp$",
        r"^datetime.*",
        r".*_datetime$",
    ]

    IDENTIFIER_PATTERNS = [
        r".*_id$",
        r"^id$",
        r".*_key$",
        r"^uuid$",
        r"^guid$",
        r".*_uuid$",
        r".*_guid$",
        r"^pk_.*",
        r"^fk_.*",
        r".*_pk$",
        r".*_fk$",
        r"^ref_.*",
        r".*_ref$",
        r"^code$",
        r".*_code$",
    ]

    BOOLEAN_PATTERNS = [
        r"^is_.*",
        r"^has_.*",
        r"^can_.*",
        r"^should_.*",
        r"^was_.*",
        r"^will_.*",
        r"^did_.*",
        r".*_flag$",
        r"^active$",
        r"^enabled$",
        r"^disabled$",
        r"^deleted$",
        r"^verified$",
        r"^confirmed$",
        r"^approved$",
        r"^visible$",
        r"^hidden$",
        r"^public$",
        r"^private$",
    ]

    NUMERIC_PATTERNS = [
        r"^amount.*",
        r".*_amount$",
        r"^price.*",
        r".*_price$",
        r"^quantity.*",
        r".*_quantity$",
        r"^qty.*",
        r".*_qty$",
        r"^count.*",
        r".*_count$",
        r"^total.*",
        r".*_total$",
        r"^balance.*",
        r".*_balance$",
        r"^revenue.*",
        r".*_revenue$",
        r"^cost.*",
        r".*_cost$",
        r"^rate.*",
        r".*_rate$",
        r"^percent.*",
        r".*_percent$",
        r".*_pct$",
        r"^age$",
        r"^weight$",
        r"^height$",
        r"^score.*",
        r".*_score$",
    ]

    CATEGORICAL_PATTERNS = [
        r"^status$",
        r".*_status$",
        r"^type$",
        r".*_type$",
        r"^category.*",
        r".*_category$",
        r"^state$",
        r".*_state$",
        r"^tier$",
        r".*_tier$",
        r"^level$",
        r".*_level$",
        r"^role$",
        r".*_role$",
        r"^country.*",
        r".*_country$",
        r"^region.*",
        r".*_region$",
        r"^currency.*",
        r".*_currency$",
    ]

    STRING_FORMAT_PATTERNS = {
        "email": [r"^email.*", r".*_email$", r".*email.*address.*"],
        "phone": [r"^phone.*", r".*_phone$", r"^tel.*", r".*_tel$", r"^mobile.*", r".*_mobile$"],
        "url": [r"^url.*", r".*_url$", r"^link.*", r".*_link$", r"^website.*", r".*_website$"],
        "ip_address": [r"^ip.*", r".*_ip$", r".*_address$", r"^ip_address$"],
        "zip_code": [r"^zip.*", r".*_zip$", r"^postal.*", r".*_postal$"],
    }

    # Data type mappings
    TIMESTAMP_TYPES = {"timestamp", "datetime", "date", "time", "timestamptz", "timestamp_ntz"}
    NUMERIC_TYPES = {
        "integer",
        "int",
        "bigint",
        "smallint",
        "tinyint",
        "decimal",
        "numeric",
        "float",
        "double",
        "real",
        "number",
        "money",
    }
    BOOLEAN_TYPES = {"boolean", "bool", "bit"}
    STRING_TYPES = {"varchar", "char", "text", "string", "nvarchar", "nchar", "ntext"}
    JSON_TYPES = {"json", "jsonb", "variant", "object"}
    ARRAY_TYPES = {"array", "list"}
    BINARY_TYPES = {"binary", "varbinary", "blob", "bytea", "bytes"}

    def __init__(
        self,
        engine: Engine,
        database_type: Optional[str] = None,
    ):
        """
        Initialize metadata analyzer.

        Args:
            engine: SQLAlchemy engine for database access
            database_type: Type of database (postgres, snowflake, etc.)
        """
        self.engine = engine
        self.database_type = database_type or engine.dialect.name

    def analyze_table(
        self,
        table_name: str,
        schema: Optional[str] = None,
    ) -> List[ColumnMetadata]:
        """
        Analyze all columns in a table.

        Args:
            table_name: Name of the table to analyze
            schema: Optional schema name

        Returns:
            List of ColumnMetadata objects
        """
        columns = []

        try:
            inspector = inspect(self.engine)

            # Get columns
            column_list = inspector.get_columns(table_name, schema=schema)

            # Get primary keys
            pk_constraint = inspector.get_pk_constraint(table_name, schema=schema)
            pk_columns = set(pk_constraint.get("constrained_columns", []) if pk_constraint else [])

            # Get foreign keys
            fk_constraints = inspector.get_foreign_keys(table_name, schema=schema)
            fk_map = {}
            for fk in fk_constraints:
                for col in fk.get("constrained_columns", []):
                    ref_table = fk.get("referred_table", "")
                    ref_schema = fk.get("referred_schema", "")
                    ref_cols = fk.get("referred_columns", [])
                    ref_str = f"{ref_schema}.{ref_table}" if ref_schema else ref_table
                    if ref_cols:
                        ref_str += f".{ref_cols[0]}"
                    fk_map[col] = ref_str

            # Get comments if available
            comments = self._get_column_comments(table_name, schema)

            # Process each column
            for position, col_info in enumerate(column_list):
                col_name = col_info["name"]
                col_type = str(col_info.get("type", "unknown"))

                # Extract type details
                type_length = None
                type_precision = None
                type_scale = None

                col_type_obj = col_info.get("type")
                if col_type_obj is not None:
                    if hasattr(col_type_obj, "length"):
                        type_length = col_type_obj.length
                    if hasattr(col_type_obj, "precision"):
                        type_precision = col_type_obj.precision
                    if hasattr(col_type_obj, "scale"):
                        type_scale = col_type_obj.scale

                # Infer semantic type
                inferred_type = self._infer_semantic_type(col_name, col_type)

                # Match name patterns
                name_patterns = self._match_name_patterns(col_name)

                metadata = ColumnMetadata(
                    name=col_name,
                    data_type=col_type,
                    nullable=col_info.get("nullable", True),
                    position=position,
                    is_primary_key=col_name in pk_columns,
                    is_foreign_key=col_name in fk_map,
                    foreign_key_references=fk_map.get(col_name),
                    inferred_type=inferred_type,
                    description=comments.get(col_name),
                    name_patterns=name_patterns,
                    type_length=type_length,
                    type_precision=type_precision,
                    type_scale=type_scale,
                    has_default=col_info.get("default") is not None,
                    default_value=str(col_info.get("default")) if col_info.get("default") else None,
                )

                columns.append(metadata)

        except Exception as e:
            logger.error(f"Failed to analyze table {schema}.{table_name}: {e}")

        return columns

    def _infer_semantic_type(self, col_name: str, col_type: str) -> InferredColumnType:
        """
        Infer the semantic type of a column based on name and data type.

        Args:
            col_name: Column name
            col_type: Column data type string

        Returns:
            Inferred semantic type
        """
        col_name_lower = col_name.lower()
        col_type_lower = col_type.lower()

        # First check data type
        base_type = col_type_lower.split("(")[0].strip()

        if base_type in self.TIMESTAMP_TYPES or "timestamp" in col_type_lower:
            return InferredColumnType.TIMESTAMP

        if base_type == "date":
            return InferredColumnType.DATE

        if base_type in self.BOOLEAN_TYPES:
            return InferredColumnType.BOOLEAN

        if base_type in self.JSON_TYPES:
            return InferredColumnType.JSON

        if base_type in self.ARRAY_TYPES or "array" in col_type_lower:
            return InferredColumnType.ARRAY

        if base_type in self.BINARY_TYPES:
            return InferredColumnType.BINARY

        # Check name patterns for more specific inference
        for pattern in self.TIMESTAMP_PATTERNS:
            if re.match(pattern, col_name_lower):
                return InferredColumnType.TIMESTAMP

        for pattern in self.BOOLEAN_PATTERNS:
            if re.match(pattern, col_name_lower):
                return InferredColumnType.BOOLEAN

        for pattern in self.IDENTIFIER_PATTERNS:
            if re.match(pattern, col_name_lower):
                return InferredColumnType.IDENTIFIER

        # Numeric inference based on type or name
        if base_type in self.NUMERIC_TYPES:
            return InferredColumnType.NUMERIC

        for pattern in self.NUMERIC_PATTERNS:
            if re.match(pattern, col_name_lower):
                return InferredColumnType.NUMERIC

        # Categorical inference from name patterns
        for pattern in self.CATEGORICAL_PATTERNS:
            if re.match(pattern, col_name_lower):
                return InferredColumnType.CATEGORICAL

        # String types
        if base_type in self.STRING_TYPES or "char" in col_type_lower:
            return InferredColumnType.STRING

        return InferredColumnType.UNKNOWN

    def _match_name_patterns(self, col_name: str) -> List[str]:
        """
        Match column name against known patterns.

        Args:
            col_name: Column name

        Returns:
            List of matched pattern names
        """
        matched = []
        col_name_lower = col_name.lower()

        # Check timestamp patterns
        for pattern in self.TIMESTAMP_PATTERNS:
            if re.match(pattern, col_name_lower):
                matched.append("timestamp")
                break

        # Check identifier patterns
        for pattern in self.IDENTIFIER_PATTERNS:
            if re.match(pattern, col_name_lower):
                matched.append("identifier")
                break

        # Check boolean patterns
        for pattern in self.BOOLEAN_PATTERNS:
            if re.match(pattern, col_name_lower):
                matched.append("boolean")
                break

        # Check numeric patterns
        for pattern in self.NUMERIC_PATTERNS:
            if re.match(pattern, col_name_lower):
                matched.append("numeric")
                break

        # Check categorical patterns
        for pattern in self.CATEGORICAL_PATTERNS:
            if re.match(pattern, col_name_lower):
                matched.append("categorical")
                break

        # Check string format patterns
        for format_name, patterns in self.STRING_FORMAT_PATTERNS.items():
            for pattern in patterns:
                if re.match(pattern, col_name_lower):
                    matched.append(f"format:{format_name}")
                    break

        return matched

    def _get_column_comments(
        self,
        table_name: str,
        schema: Optional[str],
    ) -> Dict[str, str]:
        """
        Get column comments/descriptions if available.

        Args:
            table_name: Table name
            schema: Schema name

        Returns:
            Dictionary mapping column names to comments
        """
        comments = {}

        try:
            if self.database_type == "postgresql":
                query = text(
                    """
                    SELECT a.attname as column_name, d.description
                    FROM pg_catalog.pg_attribute a
                    JOIN pg_catalog.pg_class c ON a.attrelid = c.oid
                    JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
                    LEFT JOIN pg_catalog.pg_description d ON d.objoid = c.oid
                        AND d.objsubid = a.attnum
                    WHERE c.relname = :table_name
                    AND n.nspname = COALESCE(:schema, 'public')
                    AND a.attnum > 0
                    AND d.description IS NOT NULL
                """
                )
                with self.engine.connect() as conn:
                    result = conn.execute(query, {"table_name": table_name, "schema": schema})
                    for row in result:
                        comments[row.column_name] = row.description

            elif self.database_type == "snowflake":
                schema_prefix = f'"{schema}".' if schema else ""
                query = text(
                    f"""
                    DESCRIBE TABLE {schema_prefix}"{table_name}"
                """
                )
                with self.engine.connect() as conn:
                    result = conn.execute(query)
                    for row in result:
                        if hasattr(row, "comment") and row.comment:
                            comments[row.name] = row.comment

            # Add support for other databases as needed

        except Exception as e:
            logger.debug(f"Could not retrieve column comments: {e}")

        return comments

    def get_column_metadata(
        self,
        table_name: str,
        column_name: str,
        schema: Optional[str] = None,
    ) -> Optional[ColumnMetadata]:
        """
        Get metadata for a specific column.

        Args:
            table_name: Table name
            column_name: Column name
            schema: Optional schema name

        Returns:
            ColumnMetadata or None if not found
        """
        columns = self.analyze_table(table_name, schema)
        for col in columns:
            if col.name.lower() == column_name.lower():
                return col
        return None
