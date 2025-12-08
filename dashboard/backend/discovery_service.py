"""
Service layer for table discovery operations.
"""

import os
import sys
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.engine import Engine
from sqlalchemy import inspect, text

# Add parent directory to path to import baselinr
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

try:
    from baselinr.config.schema import ConnectionConfig, TablePattern
    from baselinr.connectors.factory import create_connector
    from baselinr.profiling.table_matcher import TableMatcher
    BASELINR_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Baselinr modules not available: {e}")
    BASELINR_AVAILABLE = False

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Service for table discovery operations."""
    
    def __init__(self, db_engine: Optional[Engine] = None):
        """
        Initialize discovery service.
        
        Args:
            db_engine: Optional database engine (not used currently, but kept for consistency)
        """
        self.db_engine = db_engine
    
    def discover_tables(
        self,
        filters: Dict[str, Any],
        connection: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Discover tables with filters.
        
        Args:
            filters: Discovery filters (schemas, patterns, etc.)
            connection: Connection configuration dictionary
            
        Returns:
            Dictionary with tables, total, and schemas
        """
        if not BASELINR_AVAILABLE:
            raise RuntimeError("Baselinr modules not available")
        
        try:
            # Create connector
            connection_config = ConnectionConfig(**connection)
            connector = create_connector(connection_config)
            
            # Get schemas to search
            all_schemas = connector.list_schemas()
            
            # Filter schemas
            include_schemas = filters.get("schemas", [])
            exclude_schemas = filters.get("exclude_schemas", [])
            
            if include_schemas:
                schemas_to_search = [s for s in all_schemas if s in include_schemas]
            else:
                schemas_to_search = [s for s in all_schemas if s not in exclude_schemas]
            
            # Get table types filter
            include_table_types = filters.get("table_types", [])
            exclude_table_types = filters.get("exclude_table_types", [])
            
            # Discover tables
            tables = []
            discovered_schemas = set()
            
            matcher = TableMatcher(validate_regex=True)
            pattern = filters.get("pattern")
            pattern_type = filters.get("pattern_type", "wildcard")
            
            for schema in schemas_to_search:
                try:
                    schema_tables = connector.list_tables(schema=schema)
                    
                    # Filter by pattern if provided
                    if pattern:
                        schema_tables = matcher.filter_tables(
                            schema_tables,
                            pattern=pattern,
                            pattern_type=pattern_type
                        )
                    
                    # Get table metadata
                    inspector = inspect(connector.engine)
                    views = set(inspector.get_view_names(schema=schema))
                    
                    for table_name in schema_tables:
                        try:
                            # Get table type
                            if table_name in views:
                                table_type = "view"
                            else:
                                table_type = "table"
                            
                            # Filter by table type
                            if include_table_types and table_type not in include_table_types:
                                continue
                            if exclude_table_types and table_type in exclude_table_types:
                                continue
                            
                            # Row count is expensive, skip for discovery endpoint
                            # Can be retrieved via preview endpoint if needed
                            table_info = {
                                "schema": schema,
                                "table": table_name,
                                "table_type": table_type,
                                "row_count": None,
                                "database": connection.get("database"),
                                "tags": []  # Tags would require tag provider integration
                            }
                            tables.append(table_info)
                            discovered_schemas.add(schema)
                        except Exception as e:
                            logger.warning(f"Failed to get metadata for {schema}.{table_name}: {e}")
                            continue
                except Exception as e:
                    logger.warning(f"Failed to list tables in schema {schema}: {e}")
                    continue
            
            return {
                "tables": tables,
                "total": len(tables),
                "schemas": sorted(list(discovered_schemas))
            }
        except Exception as e:
            logger.error(f"Table discovery failed: {e}", exc_info=True)
            raise RuntimeError(f"Failed to discover tables: {str(e)}")
    
    def preview_pattern(
        self,
        pattern: Dict[str, Any],
        connection: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Preview table pattern matches.
        
        Args:
            pattern: Table pattern dictionary
            connection: Connection configuration dictionary
            
        Returns:
            Dictionary with matching tables and pattern info
        """
        if not BASELINR_AVAILABLE:
            raise RuntimeError("Baselinr modules not available")
        
        try:
            # Create connector
            connection_config = ConnectionConfig(**connection)
            connector = create_connector(connection_config)
            
            # Create TablePattern from dict
            table_pattern = TablePattern(**pattern)
            
            # Get schemas to search
            all_schemas = connector.list_schemas()
            
            # Determine which schemas to search
            if table_pattern.select_all_schemas:
                schemas_to_search = all_schemas
            elif table_pattern.select_schema:
                if table_pattern.schema_:
                    schemas_to_search = [table_pattern.schema_]
                else:
                    schemas_to_search = all_schemas
            elif table_pattern.schema_:
                schemas_to_search = [table_pattern.schema_]
            else:
                schemas_to_search = all_schemas
            
            # Filter schemas by schema_pattern if provided
            if table_pattern.schema_pattern:
                matcher = TableMatcher(validate_regex=True)
                pattern_type = "regex" if table_pattern.schema_pattern.startswith("^") else "wildcard"
                schemas_to_search = matcher.filter_tables(
                    schemas_to_search,
                    pattern=table_pattern.schema_pattern,
                    pattern_type=pattern_type
                )
            
            # Discover matching tables
            tables = []
            matcher = TableMatcher(validate_regex=True)
            pattern_type = table_pattern.pattern_type or "wildcard"
            
            for schema in schemas_to_search:
                try:
                    schema_tables = connector.list_tables(schema=schema)
                    
                    # Match tables based on pattern type
                    if table_pattern.table:
                        # Explicit table name
                        if table_pattern.table in schema_tables:
                            tables.append({
                                "schema": schema,
                                "table": table_pattern.table,
                                "table_type": "table",
                                "database": connection.get("database"),
                                "tags": []
                            })
                    elif table_pattern.pattern:
                        # Pattern-based matching
                        matched = matcher.filter_tables(
                            schema_tables,
                            pattern=table_pattern.pattern,
                            pattern_type=pattern_type,
                            exclude_patterns=table_pattern.exclude_patterns
                        )
                        for table_name in matched:
                            tables.append({
                                "schema": schema,
                                "table": table_name,
                                "table_type": "table",
                                "database": connection.get("database"),
                                "tags": []
                            })
                    elif table_pattern.select_schema or table_pattern.select_all_schemas:
                        # All tables in schema(s)
                        for table_name in schema_tables:
                            tables.append({
                                "schema": schema,
                                "table": table_name,
                                "table_type": "table",
                                "database": connection.get("database"),
                                "tags": []
                            })
                except Exception as e:
                    logger.warning(f"Failed to list tables in schema {schema}: {e}")
                    continue
            
            # Build pattern string for response
            pattern_str = table_pattern.pattern or table_pattern.table or "all tables"
            if table_pattern.schema_:
                pattern_str = f"{table_pattern.schema_}.{pattern_str}"
            
            return {
                "tables": tables,
                "total": len(tables),
                "pattern": pattern_str
            }
        except Exception as e:
            logger.error(f"Pattern preview failed: {e}", exc_info=True)
            raise RuntimeError(f"Failed to preview pattern: {str(e)}")
    
    def get_table_metadata(
        self,
        schema: str,
        table: str,
        connection: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get table metadata and columns.
        
        Args:
            schema: Schema name
            table: Table name
            connection: Connection configuration dictionary
            
        Returns:
            Dictionary with table metadata and columns
        """
        if not BASELINR_AVAILABLE:
            raise RuntimeError("Baselinr modules not available")
        
        try:
            # Create connector
            connection_config = ConnectionConfig(**connection)
            connector = create_connector(connection_config)
            
            # Get table object
            table_obj = connector.get_table(table, schema=schema)
            
            # Get table type
            inspector = inspect(connector.engine)
            table_type = "table"
            try:
                views = inspector.get_view_names(schema=schema)
                if table in views:
                    table_type = "view"
                # Check for materialized views (PostgreSQL specific)
                try:
                    materialized_views = inspector.get_view_names(schema=schema, include="materialized")
                    if table in materialized_views:
                        table_type = "materialized_view"
                except Exception:
                    pass
            except Exception:
                pass
            
            # Get row count (optional, may be slow for large tables)
            row_count = None
            try:
                from sqlalchemy import func, select
                with connector.engine.connect() as conn:
                    # Use SQLAlchemy to properly quote identifiers
                    table_obj_ref = table_obj
                    count_query = select(func.count()).select_from(table_obj_ref)
                    result = conn.execute(count_query)
                    row_count = result.scalar()
            except Exception as e:
                logger.debug(f"Could not get row count for {schema}.{table}: {e}")
                pass
            
            # Get columns
            columns = []
            for col in table_obj.columns:
                columns.append({
                    "name": col.name,
                    "type": str(col.type),
                    "nullable": col.nullable
                })
            
            return {
                "schema": schema,
                "table": table,
                "columns": columns,
                "row_count": row_count,
                "table_type": table_type
            }
        except Exception as e:
            logger.error(f"Failed to get table metadata: {e}", exc_info=True)
            if "not found" in str(e).lower() or "does not exist" in str(e).lower():
                raise FileNotFoundError(f"Table {schema}.{table} not found")
            raise RuntimeError(f"Failed to get table metadata: {str(e)}")

