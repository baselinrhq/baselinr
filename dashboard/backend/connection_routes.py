"""
Connection management API routes for Baselinr Dashboard.
"""

import sys
import os

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.engine import Engine

# Add parent directory to path to import baselinr
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from connection_models import (
    ConnectionsListResponse,
    SavedConnection,
    SaveConnectionRequest,
    SaveConnectionResponse,
)
from connection_service import ConnectionService
from database import DatabaseClient

router = APIRouter(prefix="/api/config/connections", tags=["connections"])

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

def get_connection_service() -> ConnectionService:
    """Dependency to get connection service instance."""
    if DEMO_MODE:
        return ConnectionService(db_engine=None)
    db_client = get_db_client()
    return ConnectionService(db_client.engine)


@router.get("", response_model=ConnectionsListResponse)
async def list_connections(
    connection_service: ConnectionService = Depends(get_connection_service)
):
    """
    List all saved connections.
    
    Returns a list of all saved database connections.
    """
    try:
        connections = connection_service.list_connections()
        connection_models = [
            SavedConnection(**conn) for conn in connections
        ]
        return ConnectionsListResponse(connections=connection_models, total=len(connection_models))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list connections: {str(e)}")


@router.get("/{connection_id}", response_model=SavedConnection)
async def get_connection(
    connection_id: str,
    connection_service: ConnectionService = Depends(get_connection_service)
):
    """
    Get specific connection.
    
    Returns connection details by ID.
    """
    try:
        connection = connection_service.get_connection(connection_id)
        if not connection:
            raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")
        
        return SavedConnection(**connection)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get connection: {str(e)}")


@router.post("", response_model=SaveConnectionResponse)
async def save_connection(
    request: SaveConnectionRequest,
    connection_service: ConnectionService = Depends(get_connection_service)
):
    """
    Create new connection.
    
    Saves a new database connection with encrypted password.
    """
    # Prevent connection edits in demo mode
    if DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="Connection management is not available in demo mode"
        )
    
    try:
        saved = connection_service.save_connection(request.name, request.connection)
        return SaveConnectionResponse(
            id=saved["id"],
            connection=SavedConnection(**saved)
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save connection: {str(e)}")


@router.put("/{connection_id}", response_model=SaveConnectionResponse)
async def update_connection(
    connection_id: str,
    request: SaveConnectionRequest,
    connection_service: ConnectionService = Depends(get_connection_service)
):
    """
    Update existing connection.
    
    Updates an existing database connection with encrypted password.
    """
    # Prevent connection edits in demo mode
    if DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="Connection management is not available in demo mode"
        )
    
    try:
        updated = connection_service.update_connection(
            connection_id,
            request.name,
            request.connection
        )
        return SaveConnectionResponse(
            id=updated["id"],
            connection=SavedConnection(**updated)
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update connection: {str(e)}")


@router.delete("/{connection_id}")
async def delete_connection(
    connection_id: str,
    connection_service: ConnectionService = Depends(get_connection_service)
):
    """
    Delete connection.
    
    Deletes a saved database connection.
    """
    # Prevent connection edits in demo mode
    if DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="Connection management is not available in demo mode"
        )
    
    try:
        deleted = connection_service.delete_connection(connection_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")
        
        return {"message": "Connection deleted successfully"}
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete connection: {str(e)}")

