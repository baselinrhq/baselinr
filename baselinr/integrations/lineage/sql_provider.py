"""
SQL lineage provider for Baselinr.

Extracts lineage by parsing SQL statements using SQLGlot.
"""

import logging
from typing import List, Optional, Tuple, Union

import sqlglot
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlglot import exp

from .base import ColumnLineageEdge, LineageEdge, LineageProvider

logger = logging.getLogger(__name__)


class SQLLineageProvider(LineageProvider):
    """Lineage provider that extracts dependencies by parsing SQL statements."""

    def __init__(self, engine: Optional[Engine] = None):
        """
        Initialize SQL lineage provider.

        Args:
            engine: Optional SQLAlchemy engine for fetching view definitions
        """
        self.engine = engine

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "sql_parser"

    def is_available(self) -> bool:
        """
        Check if SQL provider is available.

        Returns:
            Always True (SQLGlot is always available)
        """
        return True

    def extract_table_references(
        self,
        sql: str,
        default_database: Optional[str] = None,
        default_schema: Optional[str] = None,
    ) -> List[Tuple[str, str, Optional[str]]]:
        """
        Extract table references from SQL.

        Args:
            sql: SQL statement
            default_database: Optional default database name from connection context
            default_schema: Optional default schema name for unqualified table names

        Returns:
            List of (schema, table, database) tuples
        """
        try:
            # Parse SQL with SQLGlot
            # Try to parse with multiple dialects if needed
            parsed = None
            for dialect in ["postgres", "snowflake", "mysql", "bigquery", None]:
                try:
                    parsed = sqlglot.parse_one(sql, dialect=dialect)
                    break
                except Exception:
                    continue

            if parsed is None:
                logger.debug(f"Could not parse SQL: {sql[:100]}...")
                return []

            # Extract all table references
            tables = []
            for table_expr in parsed.find_all(exp.Table):
                # In SQLGlot, structure varies by dialect:
                # PostgreSQL: catalog=database, db=schema, name=table
                # Snowflake: catalog=database, db=schema, name=table
                # For most dialects: db attribute is the schema
                schema = table_expr.db if table_expr.db else (default_schema or "")
                table = table_expr.name if table_expr.name else ""

                # Database/catalog extraction
                # catalog attribute is typically the database
                database = table_expr.catalog if table_expr.catalog else default_database

                if table:  # Only add if we have a table name
                    tables.append((schema, table, database))

            return tables

        except Exception as e:
            logger.debug(f"Error parsing SQL for table references: {e}")
            return []

    def extract_lineage_from_sql(
        self,
        sql: str,
        output_table: Tuple[str, str],
        output_database: Optional[str] = None,
        default_database: Optional[str] = None,
        default_schema: Optional[str] = None,
    ) -> List[LineageEdge]:
        """
        Extract lineage from SQL statement.

        Args:
            sql: SQL statement
            output_table: (schema, table) tuple for the output table
            output_database: Optional database name for the output table
            default_database: Optional default database name from connection context
            default_schema: Optional default schema name for unqualified table names

        Returns:
            List of LineageEdge objects
        """
        input_tables = self.extract_table_references(
            sql, default_database=default_database, default_schema=default_schema
        )
        output_schema, output_table_name = output_table

        edges = []
        for input_schema, input_table, input_database in input_tables:
            # Skip if input table is the same as output (self-reference)
            if (
                input_schema == output_schema
                and input_table == output_table_name
                and input_database == output_database
            ):
                continue

            edge = LineageEdge(
                downstream_schema=output_schema,
                downstream_table=output_table_name,
                upstream_schema=input_schema,
                upstream_table=input_table,
                downstream_database=output_database,
                upstream_database=input_database,
                lineage_type="sql_parsed",
                provider="sql_parser",
                confidence_score=0.9,  # Slightly lower confidence for parsed SQL
                metadata={"sql_preview": sql[:200] if len(sql) > 200 else sql},
            )
            edges.append(edge)

        return edges

    def extract_lineage(
        self,
        table_name: str,
        schema: Optional[str] = None,
    ) -> List[LineageEdge]:
        """
        Extract lineage for a specific table by fetching view definitions.

        Args:
            table_name: Name of the table/view
            schema: Optional schema name

        Returns:
            List of LineageEdge objects if view definition can be fetched and parsed
        """
        # Use the engine passed to __init__
        engine = self.engine

        if not engine:
            logger.debug(
                f"SQLLineageProvider.extract_lineage for {schema}.{table_name} "
                "requires database engine to fetch view definitions."
            )
            return []

        # Get database name and default schema from engine URL
        database = None
        default_schema = None
        try:
            if hasattr(engine, "url") and engine.url:
                database = engine.url.database
                # For PostgreSQL, default schema is usually 'public'
                if "postgres" in str(engine.url).lower():
                    default_schema = schema or "public"
                else:
                    default_schema = schema
        except Exception:
            pass

        # Try to fetch view definition
        try:
            view_sql = self._get_view_definition(engine, table_name, schema)
            if view_sql:
                output_table = (schema or default_schema or "", table_name)
                # Pass default_schema to help with unqualified table names
                return self.extract_lineage_from_sql(
                    view_sql,
                    output_table,
                    output_database=database,
                    default_database=database,
                    default_schema=default_schema,
                )
        except Exception as e:
            logger.debug(
                f"Could not extract lineage from view definition for {schema}.{table_name}: {e}"
            )

        return []

    def _get_view_definition(
        self, engine: Engine, table_name: str, schema: Optional[str] = None
    ) -> Optional[str]:
        """
        Get view definition from database.

        Args:
            engine: SQLAlchemy engine
            table_name: Name of the view
            schema: Optional schema name

        Returns:
            View definition SQL or None if not a view or not found
        """
        try:
            # Check if it's a view and get its definition
            # PostgreSQL-specific query
            if "postgres" in str(engine.url).lower():
                if schema:
                    query = text(
                        """
                        SELECT definition
                        FROM pg_views
                        WHERE viewname = :view_name
                        AND schemaname = :schema_name
                        LIMIT 1
                        """
                    )
                    params = {"view_name": table_name, "schema_name": schema}
                else:
                    query = text(
                        """
                        SELECT definition
                        FROM pg_views
                        WHERE viewname = :view_name
                        LIMIT 1
                        """
                    )
                    params = {"view_name": table_name}

                with engine.connect() as conn:
                    result = conn.execute(query, params).fetchone()
                    if result:
                        return str(result[0])

            # Generic approach: try INFORMATION_SCHEMA
            if schema:
                query = text(
                    """
                    SELECT view_definition
                    FROM information_schema.views
                    WHERE table_name = :table_name
                    AND table_schema = :schema_name
                    LIMIT 1
                    """
                )
                params = {"table_name": table_name, "schema_name": schema}
            else:
                query = text(
                    """
                    SELECT view_definition
                    FROM information_schema.views
                    WHERE table_name = :table_name
                    LIMIT 1
                    """
                )
                params = {"table_name": table_name}

            with engine.connect() as conn:
                result = conn.execute(query, params).fetchone()
                if result:
                    return str(result[0])

        except Exception as e:
            logger.debug(f"Error fetching view definition for {schema}.{table_name}: {e}")

        return None

    def extract_column_references(
        self,
        sql: str,
        default_database: Optional[str] = None,
        default_schema: Optional[str] = None,
    ) -> List[Tuple[str, str, str, Optional[str]]]:
        """
        Extract column references from SQL SELECT statements.

        Args:
            sql: SQL SELECT statement
            default_database: Optional default database name from connection context
            default_schema: Optional default schema name for unqualified table names

        Returns:
            List of (schema, table, column, database) tuples
        """
        try:
            # Parse SQL with SQLGlot
            parsed = None
            for dialect in ["postgres", "snowflake", "mysql", "bigquery", None]:
                try:
                    parsed = sqlglot.parse_one(sql, dialect=dialect)
                    break
                except Exception:
                    continue

            if parsed is None:
                logger.debug(f"Could not parse SQL for column references: {sql[:100]}...")
                return []

            column_refs = []
            # Find all column references in the SQL
            for column_expr in parsed.find_all(exp.Column):
                # Get table reference for this column
                # column_expr.table can be either a string or a Table object
                table_expr: Union[str, exp.Table, None] = (
                    column_expr.table  # type: ignore[assignment]
                )
                if table_expr:
                    # Handle both string table names and Table expression objects
                    if isinstance(table_expr, str):
                        schema = default_schema or ""
                        table = table_expr
                        database = default_database
                    elif isinstance(table_expr, exp.Table):
                        schema = table_expr.db if table_expr.db else (default_schema or "")
                        table = table_expr.name if table_expr.name else ""
                        database = table_expr.catalog if table_expr.catalog else default_database
                    else:
                        # Unknown type, skip
                        continue
                    column = column_expr.name if column_expr.name else ""

                    if table and column:
                        column_refs.append((schema, table, column, database))

            return column_refs

        except Exception as e:
            logger.debug(f"Error parsing SQL for column references: {e}")
            return []

    def extract_column_lineage_from_sql(
        self,
        sql: str,
        output_table: Tuple[str, str],
        output_database: Optional[str] = None,
        default_database: Optional[str] = None,
        default_schema: Optional[str] = None,
    ) -> List[ColumnLineageEdge]:
        """
        Extract column-level lineage from SQL SELECT statement.

        Maps output columns to source columns by parsing SELECT expressions.

        Args:
            sql: SQL SELECT statement
            output_table: (schema, table) tuple for the output table
            output_database: Optional database name for the output table
            default_database: Optional default database name from connection context
            default_schema: Optional default schema name for unqualified table names

        Returns:
            List of ColumnLineageEdge objects
        """
        try:
            # Parse SQL with SQLGlot
            parsed = None
            for dialect in ["postgres", "snowflake", "mysql", "bigquery", None]:
                try:
                    parsed = sqlglot.parse_one(sql, dialect=dialect)
                    break
                except Exception:
                    continue

            if parsed is None:
                logger.debug(f"Could not parse SQL for column lineage: {sql[:100]}...")
                return []

            output_schema, output_table_name = output_table
            column_edges = []

            # Find SELECT statement
            select_expr = parsed if isinstance(parsed, exp.Select) else None
            if not select_expr:
                # Try to find SELECT in the parsed tree
                select_expr = parsed.find(exp.Select)
                if not select_expr:
                    return []

            # Get SELECT expressions (output columns)
            select_expressions = select_expr.expressions if select_expr else []

            # Get source tables from FROM clause
            from_tables = []
            for table_expr in select_expr.find_all(exp.Table):
                schema = table_expr.db if table_expr.db else (default_schema or "")
                table = table_expr.name if table_expr.name else ""
                database = table_expr.catalog if table_expr.catalog else default_database

                if table:
                    from_tables.append((schema, table, database))

            # Process each SELECT expression
            for select_item in select_expressions:
                # Get output column name (alias or column name)
                output_column = None
                if isinstance(select_item, exp.Alias):
                    output_column = select_item.alias
                    expr = select_item.this
                elif isinstance(select_item, exp.Column):
                    output_column = select_item.name
                    expr = select_item
                else:
                    # Complex expression - try to extract alias or use expression as name
                    if hasattr(select_item, "alias"):
                        output_column = select_item.alias
                    else:
                        # Use a simplified version of the expression as the column name
                        output_column = str(select_item)[:50]  # Truncate long expressions
                    expr = select_item

                if not output_column:
                    continue

                # Extract source columns from the expression
                source_columns = []
                transformation = None

                if isinstance(expr, exp.Column):
                    # Direct column reference
                    # expr.table can be either a string or a Table object
                    col_table_expr: Union[str, exp.Table, None] = (
                        expr.table  # type: ignore[assignment]
                    )
                    if col_table_expr:
                        # Handle both string table names and Table expression objects
                        if isinstance(col_table_expr, str):
                            schema = default_schema or ""
                            table = col_table_expr
                            database = default_database
                        elif isinstance(col_table_expr, exp.Table):
                            schema = (
                                col_table_expr.db if col_table_expr.db else (default_schema or "")
                            )
                            table = col_table_expr.name if col_table_expr.name else ""
                            database = (
                                col_table_expr.catalog
                                if col_table_expr.catalog
                                else default_database
                            )
                        else:
                            # Unknown type, skip
                            continue
                        column = expr.name if expr.name else ""
                        if table and column:
                            source_columns.append((schema, table, column, database))
                else:
                    # Complex expression - find all column references within it
                    for col_expr in expr.find_all(exp.Column):
                        # col_expr.table can be either a string or a Table object
                        nested_table_expr: Union[str, exp.Table, None] = (
                            col_expr.table  # type: ignore[assignment]
                        )
                        if nested_table_expr:
                            # Handle both string table names and Table expression objects
                            if isinstance(nested_table_expr, str):
                                schema = default_schema or ""
                                table = nested_table_expr
                                database = default_database
                            elif isinstance(nested_table_expr, exp.Table):
                                schema = (
                                    nested_table_expr.db
                                    if nested_table_expr.db
                                    else (default_schema or "")
                                )
                                table = nested_table_expr.name if nested_table_expr.name else ""
                                database = (
                                    nested_table_expr.catalog
                                    if nested_table_expr.catalog
                                    else default_database
                                )
                            else:
                                # Unknown type, skip
                                continue
                            column = col_expr.name if col_expr.name else ""
                            if table and column:
                                source_columns.append((schema, table, column, database))

                    # Store transformation expression if it's not a simple column reference
                    if not isinstance(expr, exp.Column):
                        transformation = str(expr)

                # Create edges for each source column
                for source_schema, source_table, source_column, source_database in source_columns:
                    # Skip if source is the same as output (self-reference)
                    if (
                        source_schema == output_schema
                        and source_table == output_table_name
                        and source_database == output_database
                    ):
                        continue

                    edge = ColumnLineageEdge(
                        downstream_schema=output_schema,
                        downstream_table=output_table_name,
                        downstream_column=output_column,
                        upstream_schema=source_schema,
                        upstream_table=source_table,
                        upstream_column=source_column,
                        downstream_database=output_database,
                        upstream_database=source_database,
                        lineage_type="sql_parsed",
                        provider="sql_parser",
                        confidence_score=0.85,  # Lower confidence for parsed SQL
                        transformation_expression=transformation,
                        metadata={"sql_preview": sql[:200] if len(sql) > 200 else sql},
                    )
                    column_edges.append(edge)

            return column_edges

        except Exception as e:
            logger.warning(
                f"Error extracting column lineage from SQL: {e}",
                exc_info=True,
            )
            return []

    def extract_column_lineage(
        self,
        table_name: str,
        schema: Optional[str] = None,
    ) -> List[ColumnLineageEdge]:
        """
        Extract column-level lineage for a specific table by fetching view definitions.

        Args:
            table_name: Name of the table/view
            schema: Optional schema name

        Returns:
            List of ColumnLineageEdge objects if view definition can be fetched and parsed
        """
        # Use the engine passed to __init__
        engine = self.engine

        if not engine:
            logger.debug(
                f"SQLLineageProvider.extract_column_lineage for {schema}.{table_name} "
                "requires database engine to fetch view definitions."
            )
            return []

        # Get database name and default schema from engine URL
        database = None
        default_schema = None
        try:
            if hasattr(engine, "url") and engine.url:
                database = engine.url.database
                # For PostgreSQL, default schema is usually 'public'
                if "postgres" in str(engine.url).lower():
                    default_schema = schema or "public"
                else:
                    default_schema = schema
        except Exception:
            pass

        # Try to fetch view definition
        try:
            view_sql = self._get_view_definition(engine, table_name, schema)
            if view_sql:
                logger.info(
                    f"Fetched view definition for {schema}.{table_name}, "
                    f"length: {len(view_sql)} chars"
                )
                output_table = (schema or default_schema or "", table_name)
                # Pass default_schema to help with unqualified table names
                edges = self.extract_column_lineage_from_sql(
                    view_sql,
                    output_table,
                    output_database=database,
                    default_database=database,
                    default_schema=default_schema,
                )
                logger.info(
                    f"Extracted {len(edges)} column lineage edges from SQL for "
                    f"{schema}.{table_name}"
                )
                return edges
            else:
                logger.info(
                    f"No view definition found for {schema}.{table_name} "
                    "(might be a table, not a view)"
                )
        except Exception as e:
            logger.warning(
                f"Could not extract column lineage from view definition for "
                f"{schema}.{table_name}: {e}",
                exc_info=True,
            )

        return []
