"""
Table discovery API routes for Baselinr Dashboard.
"""

import sys
import os
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.engine import Engine

# Add parent directory to path to import baselinr
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from discovery_models import (
    TableDiscoveryResponse,
    TableInfo,
    TablePatternRequest,
    TablePreviewResponse,
    TableMetadataResponse,
)
from discovery_service import DiscoveryService
from config_service import ConfigService
from connection_service import ConnectionService
from database import DatabaseClient

router = APIRouter(prefix="/api/tables", tags=["tables"])

# Check if demo mode is enabled
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Global database client instance
_db_client = None

def get_db_client() -> DatabaseClient:
    """Get or create database client instance."""
    global _db_client
    if DEMO_MODE:
        return None
    if _db_client is None:
        _db_client = DatabaseClient()
    return _db_client

def get_config_service() -> ConfigService:
    """Dependency to get config service instance."""
    if DEMO_MODE:
        return ConfigService(db_engine=None)
    db_client = get_db_client()
    return ConfigService(db_client.engine)

def get_connection_service() -> ConnectionService:
    """Dependency to get connection service instance."""
    if DEMO_MODE:
        return ConnectionService(db_engine=None)
    db_client = get_db_client()
    return ConnectionService(db_client.engine)

def get_discovery_service() -> DiscoveryService:
    """Dependency to get discovery service instance."""
    if DEMO_MODE:
        return DiscoveryService(db_engine=None)
    db_client = get_db_client()
    return DiscoveryService(db_client.engine)

def _get_connection_config(
    connection_id: Optional[str],
    config_service: ConfigService,
    connection_service: ConnectionService
) -> dict:
    """
    Get connection configuration from connection_id or config.source.
    
    Args:
        connection_id: Optional connection ID
        config_service: Config service instance
        connection_service: Connection service instance
        
    Returns:
        Connection configuration dictionary
        
    Raises:
        HTTPException: If connection not found or config.source not available
    """
    if connection_id:
        # Get from saved connections
        connection_data = connection_service.get_connection(connection_id)
        if not connection_data:
            raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")
        return connection_data.get("connection", {})
    else:
        # Fall back to config.source
        try:
            config = config_service.load_config()
            source = config.get("source")
            if not source:
                raise HTTPException(
                    status_code=400,
                    detail="No connection specified. Provide connection_id or configure config.source"
                )
            return source
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail="Configuration file not found. Provide connection_id or configure config.source"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load configuration: {str(e)}"
            )


@router.get("/discover", response_model=TableDiscoveryResponse)
async def discover_tables(
    connection_id: Optional[str] = Query(None, description="ID of saved connection"),
    database: Optional[str] = Query(None, description="Database name filter"),
    schemas: Optional[List[str]] = Query(None, description="Include schemas"),
    exclude_schemas: Optional[List[str]] = Query(None, description="Exclude schemas"),
    table_types: Optional[List[str]] = Query(None, description="Include table types"),
    exclude_table_types: Optional[List[str]] = Query(None, description="Exclude table types"),
    pattern: Optional[str] = Query(None, description="Table name pattern"),
    pattern_type: Optional[str] = Query(None, description="Pattern type: wildcard or regex"),
    tags: Optional[List[str]] = Query(None, description="Required tags (AND logic)"),
    tags_any: Optional[List[str]] = Query(None, description="Optional tags (OR logic)"),
    config_service: ConfigService = Depends(get_config_service),
    connection_service: ConnectionService = Depends(get_connection_service),
    discovery_service: DiscoveryService = Depends(get_discovery_service)
):
    """
    Discover tables with filters.
    
    Returns a list of tables matching the specified filters.
    """
    try:
        # Get connection config
        connection = _get_connection_config(connection_id, config_service, connection_service)
        
        # Build filters dictionary
        filters = {}
        if database:
            filters["database"] = database
        if schemas:
            filters["schemas"] = schemas
        if exclude_schemas:
            filters["exclude_schemas"] = exclude_schemas
        if table_types:
            filters["table_types"] = table_types
        if exclude_table_types:
            filters["exclude_table_types"] = exclude_table_types
        if pattern:
            filters["pattern"] = pattern
        if pattern_type:
            filters["pattern_type"] = pattern_type
        if tags:
            filters["tags"] = tags
        if tags_any:
            filters["tags_any"] = tags_any
        
        # Discover tables
        result = discovery_service.discover_tables(filters, connection)
        
        # Convert to response models
        table_infos = [
            TableInfo(**table) for table in result["tables"]
        ]
        
        return TableDiscoveryResponse(
            tables=table_infos,
            total=result["total"],
            schemas=result["schemas"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to discover tables: {str(e)}")


@router.post("/discover", response_model=TablePreviewResponse)
async def preview_pattern(
    pattern: TablePatternRequest,
    connection_id: Optional[str] = Query(None, description="ID of saved connection"),
    config_service: ConfigService = Depends(get_config_service),
    connection_service: ConnectionService = Depends(get_connection_service),
    discovery_service: DiscoveryService = Depends(get_discovery_service)
):
    """
    Preview table pattern matches.
    
    Returns a list of tables that match the specified pattern.
    """
    try:
        # Get connection config
        connection = _get_connection_config(connection_id, config_service, connection_service)
        
        # Convert pattern to dict
        pattern_dict = pattern.model_dump(exclude_none=True)
        
        # Preview pattern
        result = discovery_service.preview_pattern(pattern_dict, connection)
        
        # Convert to response models
        table_infos = [
            TableInfo(**table) for table in result["tables"]
        ]
        
        return TablePreviewResponse(
            tables=table_infos,
            total=result["total"],
            pattern=result["pattern"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to preview pattern: {str(e)}")


@router.get("/{schema}/{table}/preview", response_model=TableMetadataResponse)
async def get_table_preview(
    schema: str,
    table: str,
    connection_id: Optional[str] = Query(None, description="ID of saved connection"),
    config_service: ConfigService = Depends(get_config_service),
    connection_service: ConnectionService = Depends(get_connection_service),
    discovery_service: DiscoveryService = Depends(get_discovery_service)
):
    """
    Get table metadata preview.
    
    Returns table schema, columns, row count, and table type.
    """
    try:
        # Get connection config
        connection = _get_connection_config(connection_id, config_service, connection_service)
        
        # Get table metadata
        result = discovery_service.get_table_metadata(schema, table, connection)
        
        # Convert to response model
        from discovery_models import ColumnInfo
        columns = [ColumnInfo(**col) for col in result["columns"]]
        
        return TableMetadataResponse(
            schema=result["schema"],
            table=result["table"],
            columns=columns,
            row_count=result.get("row_count"),
            table_type=result.get("table_type")
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get table preview: {str(e)}")

