"""
Quality scores API routes for Baselinr Dashboard.
"""

import sys
import os
import logging

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.engine import Engine

# Add parent directory to path to import baselinr
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from quality_models import (
    QualityScoreResponse,
    ScoreComponentResponse,
    ScoreHistoryResponse,
    QualityScoresListResponse,
    SchemaScoreResponse,
    SystemScoreResponse,
    TrendAnalysisResponse,
    ColumnScoresListResponse,
    ScoreComparisonResponse,
)
from quality_service import QualityService
from database import DatabaseClient
from demo_quality_storage import DemoQualityStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quality/scores", tags=["quality-scores"])

# Check if demo mode is enabled
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Global storage instances
_db_client = None
_demo_quality_storage = None


def get_db_client() -> DatabaseClient:
    """Get or create database client instance."""
    global _db_client
    if _db_client is None:
        _db_client = DatabaseClient()
    return _db_client


def get_demo_quality_storage() -> DemoQualityStorage:
    """Get or create demo quality storage instance."""
    global _demo_quality_storage
    if _demo_quality_storage is None:
        # Get the data directory relative to this file
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(backend_dir, "demo_data")
        _demo_quality_storage = DemoQualityStorage(data_dir)
    return _demo_quality_storage


def get_quality_service() -> QualityService:
    """Dependency to get quality service instance."""
    if DEMO_MODE:
        # In demo mode, use demo quality storage
        logger.info("Quality service running in demo mode with demo quality storage")
        demo_storage = get_demo_quality_storage()
        # Create a QualityService but override its storage with demo storage
        service = QualityService(db_engine=None)
        service.storage = demo_storage
        return service
    
    db_client = get_db_client()
    return QualityService(db_client.engine)


@router.get("", response_model=QualityScoresListResponse)
async def get_all_scores(
    schema: str = Query(None, description="Filter by schema name"),
    status: str = Query(None, description="Filter by status (healthy, warning, critical)"),
    quality_service: QualityService = Depends(get_quality_service),
):
    """
    Get all table scores with optional filters.

    Returns a list of all table quality scores, optionally filtered by schema or status.
    """
    try:
        scores = quality_service.get_all_scores(schema=schema, status=status)
        return QualityScoresListResponse(scores=scores, total=len(scores))
    except Exception as e:
        logger.error(f"Failed to get all scores: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get all scores: {str(e)}")


@router.get("/{table_name}", response_model=QualityScoreResponse)
async def get_table_score(
    table_name: str,
    schema: str = Query(None, description="Schema name"),
    quality_service: QualityService = Depends(get_quality_service),
):
    """
    Get specific table score.

    Returns the latest quality score for a specific table.
    """
    try:
        logger.debug(f"API: Getting score for table={table_name}, schema={schema}")
        score = quality_service.get_table_score(table_name, schema_name=schema)
        if not score:
            logger.debug(f"API: No score found for table={table_name}, schema={schema}")
            raise HTTPException(
                status_code=404, detail=f"Quality score not found for table: {table_name}"
            )
        logger.debug(f"API: Found score for {table_name}: {score.overall_score}")
        return score
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get table score: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get table score: {str(e)}")


@router.get("/schema/{schema_name}", response_model=SchemaScoreResponse)
async def get_schema_score(
    schema_name: str,
    quality_service: QualityService = Depends(get_quality_service),
):
    """
    Get schema-level scores.

    Returns aggregated quality scores for all tables in a schema.
    """
    try:
        schema_score = quality_service.get_schema_score(schema_name)
        if not schema_score:
            raise HTTPException(
                status_code=404, detail=f"No quality scores found for schema: {schema_name}"
            )
        return schema_score
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get schema score: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get schema score: {str(e)}")


@router.get("/system", response_model=SystemScoreResponse)
async def get_system_score(
    quality_service: QualityService = Depends(get_quality_service),
):
    """
    Get system-level score.

    Returns aggregated quality score across all tables in the system.
    """
    try:
        return quality_service.get_system_score()
    except Exception as e:
        logger.error(f"Failed to get system score: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get system score: {str(e)}")


@router.get("/{table_name}/history", response_model=ScoreHistoryResponse)
async def get_score_history(
    table_name: str,
    schema: str = Query(None, description="Schema name"),
    days: int = Query(30, description="Number of days to look back"),
    quality_service: QualityService = Depends(get_quality_service),
):
    """
    Get score history for a table.

    Returns historical quality scores for a specific table over the specified time period.
    """
    try:
        scores = quality_service.get_score_history(
            table_name, schema_name=schema, days=days
        )
        return ScoreHistoryResponse(scores=scores, total=len(scores))
    except Exception as e:
        logger.error(f"Failed to get score history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get score history: {str(e)}")


@router.get("/{table_name}/components", response_model=ScoreComponentResponse)
async def get_component_breakdown(
    table_name: str,
    schema: str = Query(None, description="Schema name"),
    quality_service: QualityService = Depends(get_quality_service),
):
    """
    Get component breakdown for a table.

    Returns the component scores (completeness, validity, consistency, etc.) for a specific table.
    """
    try:
        components = quality_service.get_component_breakdown(table_name, schema_name=schema)
        if not components:
            raise HTTPException(
                status_code=404,
                detail=f"Component breakdown not found for table: {table_name}",
            )
        return components
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get component breakdown: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get component breakdown: {str(e)}"
        )


@router.get("/{table_name}/trend", response_model=TrendAnalysisResponse)
async def get_score_trend(
    table_name: str,
    schema: str = Query(None, description="Schema name"),
    days: int = Query(30, description="Number of days to look back"),
    quality_service: QualityService = Depends(get_quality_service),
):
    """
    Get trend analysis for a table.

    Returns trend analysis including direction, rate of change, and confidence.
    """
    try:
        trend = quality_service.get_trend_analysis(table_name, schema_name=schema, days=days)
        if not trend:
            raise HTTPException(
                status_code=404,
                detail=f"Trend analysis not available for table: {table_name} (insufficient data)",
            )
        return trend
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trend analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get trend analysis: {str(e)}")


@router.get("/{table_name}/columns", response_model=ColumnScoresListResponse)
async def get_column_scores(
    table_name: str,
    schema: str = Query(None, description="Schema name"),
    days: int = Query(30, description="Number of days to look back"),
    quality_service: QualityService = Depends(get_quality_service),
):
    """
    Get column-level scores for a table.

    Returns quality scores for all columns in the specified table.
    """
    try:
        return quality_service.get_column_scores(table_name, schema_name=schema, days=days)
    except Exception as e:
        logger.error(f"Failed to get column scores: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get column scores: {str(e)}")


@router.get("/compare", response_model=ScoreComparisonResponse)
async def compare_scores(
    tables: str = Query(..., description="Comma-separated list of table names to compare"),
    schema: str = Query(None, description="Schema name"),
    quality_service: QualityService = Depends(get_quality_service),
):
    """
    Compare scores across multiple tables.

    Returns comparison data including best/worst performers and metrics.
    """
    try:
        table_list = [t.strip() for t in tables.split(",")]
        if len(table_list) < 2:
            raise HTTPException(
                status_code=400, detail="At least 2 tables required for comparison"
            )
        return quality_service.compare_scores(table_list, schema_name=schema)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compare scores: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to compare scores: {str(e)}")
