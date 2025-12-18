"""
Recommendation API routes for Baselinr Dashboard.
"""

import sys
import os
import logging
from typing import Optional, List, Any

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# Add parent directory to path to import baselinr
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from recommendation_models import (
    RecommendationRequest,
    RecommendationReportResponse,
    TableRecommendationResponse,
    ColumnCheckRecommendationResponse,
    ExcludedTableResponse,
    ColumnRecommendationRequest,
    ApplyRecommendationsRequest,
    ApplyRecommendationsResponse,
    AppliedTable,
)
from recommendation_service import RecommendationService
from database import DatabaseClient

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

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

def get_recommendation_service() -> RecommendationService:
    """Dependency to get recommendation service instance."""
    if DEMO_MODE:
        logger.info("Recommendation service running in demo mode - will return empty data")
        return RecommendationService(db_engine=None)
    
    db_client = get_db_client()
    return RecommendationService(db_client.engine)


def _convert_report_to_response(report: Any) -> RecommendationReportResponse:
    """Convert RecommendationReport to response model."""
    # Convert recommended tables
    recommended_tables = []
    for rec in report.recommended_tables:
        try:
            # Convert column recommendations safely
            column_recs = []
            for col in getattr(rec, 'column_recommendations', []):
                try:
                    column_recs.append(
                        ColumnCheckRecommendationResponse(
                            column=getattr(col, 'column', ''),
                            data_type=getattr(col, 'data_type', ''),
                            confidence=getattr(col, 'confidence', 0.0),
                            signals=getattr(col, 'signals', []),
                            suggested_checks=getattr(col, 'suggested_checks', []),
                        )
                    )
                except Exception as e:
                    logger.warning(f"Error converting column recommendation: {e}")
            
            low_conf_cols = []
            for col in getattr(rec, 'low_confidence_columns', []):
                try:
                    low_conf_cols.append(
                        ColumnCheckRecommendationResponse(
                            column=getattr(col, 'column', ''),
                            data_type=getattr(col, 'data_type', ''),
                            confidence=getattr(col, 'confidence', 0.0),
                            signals=getattr(col, 'signals', []),
                            suggested_checks=getattr(col, 'suggested_checks', []),
                        )
                    )
                except Exception as e:
                    logger.warning(f"Error converting low confidence column: {e}")
            
            recommended_tables.append(
                TableRecommendationResponse(
                    schema=getattr(rec, 'schema', ''),
                    table=getattr(rec, 'table', ''),
                    database=getattr(rec, 'database', None),
                    confidence=getattr(rec, 'confidence', 0.0),
                    score=getattr(rec, 'score', 0.0),
                    reasons=getattr(rec, 'reasons', []),
                    warnings=getattr(rec, 'warnings', []),
                    suggested_checks=getattr(rec, 'suggested_checks', []),
                    column_recommendations=column_recs,
                    low_confidence_columns=low_conf_cols,
                    query_count=getattr(rec, 'query_count', 0),
                    queries_per_day=getattr(rec, 'queries_per_day', 0.0),
                    row_count=getattr(rec, 'row_count', None),
                    last_query_days_ago=getattr(rec, 'last_query_days_ago', None),
                    column_count=getattr(rec, 'column_count', 0),
                    lineage_score=getattr(rec, 'lineage_score', 0.0),
                    lineage_context=getattr(rec, 'lineage_context', None),
                )
            )
        except Exception as e:
            logger.error(f"Error converting table recommendation {getattr(rec, 'table', 'unknown')}: {e}", exc_info=True)
    
    # Convert excluded tables
    excluded_tables = [
        ExcludedTableResponse(
            schema=getattr(exc, 'schema', ''),
            table=getattr(exc, 'table', ''),
            database=getattr(exc, 'database', None),
            reasons=getattr(exc, 'reasons', []),
        )
        for exc in report.excluded_tables
    ]
    
    return RecommendationReportResponse(
        generated_at=report.generated_at,
        lookback_days=report.lookback_days,
        database_type=report.database_type,
        recommended_tables=recommended_tables,
        excluded_tables=excluded_tables,
        total_tables_analyzed=getattr(report, 'total_tables_analyzed', 0),
        total_recommended=getattr(report, 'total_recommended', 0),
        total_excluded=getattr(report, 'total_excluded', 0),
        confidence_distribution=getattr(report, 'confidence_distribution', {}),
        total_columns_analyzed=getattr(report, 'total_columns_analyzed', 0),
        total_column_checks_recommended=getattr(report, 'total_column_checks_recommended', 0),
        column_confidence_distribution=getattr(report, 'column_confidence_distribution', {}),
        low_confidence_suggestions=getattr(report, 'low_confidence_suggestions', []),
    )


@router.get("", response_model=RecommendationReportResponse)
async def get_recommendations(
    connection_id: str = Query(..., description="ID of the saved connection"),
    schema: Optional[str] = Query(None, description="Optional schema to limit recommendations"),
    include_columns: bool = Query(False, description="Include column-level recommendations"),
    refresh: bool = Query(False, description="Force refresh recommendations"),
    service: RecommendationService = Depends(get_recommendation_service),
):
    """
    Get smart selection recommendations.
    
    Returns recommendations for tables to monitor based on query patterns,
    table usage, and other heuristics.
    """
    # Return empty recommendations in demo mode
    if DEMO_MODE:
        return RecommendationReportResponse(
            recommended_tables=[],
            excluded_tables=[],
            total_tables_analyzed=0,
            recommendation_confidence=0.0,
            analysis_metadata={}
        )
    
    try:
        logger.info(f"Getting recommendations for connection_id={connection_id}, schema={schema}, include_columns={include_columns}")
        
        report = service.generate_recommendations(
            connection_id=connection_id,
            schema=schema,
            include_columns=include_columns,
        )
        
        logger.info(f"Got report with {len(report.recommended_tables)} recommended tables")
        
        # Convert to response model
        return _convert_report_to_response(report)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {str(e)}")


@router.get("/columns", response_model=List[ColumnCheckRecommendationResponse])
async def get_column_recommendations(
    connection_id: str = Query(..., description="ID of the saved connection"),
    table: str = Query(..., description="Table name"),
    schema: Optional[str] = Query(None, description="Schema name"),
    use_profiling_data: bool = Query(True, description="Use profiling data if available"),
    service: RecommendationService = Depends(get_recommendation_service),
):
    """
    Get column-level recommendations for a specific table.
    
    Returns recommended validation checks for columns in the specified table.
    """
    # Return empty list in demo mode
    if DEMO_MODE:
        return []
    
    try:
        recommendations = service.get_column_recommendations(
            connection_id=connection_id,
            table=table,
            schema=schema,
            use_profiling_data=use_profiling_data,
        )
        
        return [
            ColumnCheckRecommendationResponse(
                column=rec.column,
                data_type=rec.data_type,
                confidence=rec.confidence,
                signals=rec.signals,
                suggested_checks=rec.suggested_checks,
            )
            for rec in recommendations
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get column recommendations: {str(e)}")


@router.post("/apply", response_model=ApplyRecommendationsResponse)
async def apply_recommendations(
    request: ApplyRecommendationsRequest,
    service: RecommendationService = Depends(get_recommendation_service),
):
    """
    Apply recommendations to configuration.
    
    Adds selected tables and column checks to the configuration file.
    """
    # Return empty success in demo mode
    if DEMO_MODE:
        return ApplyRecommendationsResponse(
            success=False,
            applied_tables=[],
            total_tables_applied=0,
            total_column_checks_applied=0,
            message="Apply recommendations is not available in demo mode"
        )
    
    try:
        result = service.apply_recommendations(
            connection_id=request.connection_id,
            selected_tables=request.selected_tables,
            column_checks=request.column_checks,
            comment=request.comment,
        )
        
        applied_tables = [
            AppliedTable(
                schema=table['schema'],
                table=table['table'],
                database=table.get('database'),
                column_checks_applied=table.get('column_checks_applied', 0),
            )
            for table in result['applied_tables']
        ]
        
        return ApplyRecommendationsResponse(
            success=result['success'],
            applied_tables=applied_tables,
            total_tables_applied=result['total_tables_applied'],
            total_column_checks_applied=result['total_column_checks_applied'],
            message=result['message'],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply recommendations: {str(e)}")


@router.post("/refresh", response_model=RecommendationReportResponse)
async def refresh_recommendations(
    request: RecommendationRequest,
    service: RecommendationService = Depends(get_recommendation_service),
):
    """
    Force refresh recommendations.
    
    Regenerates recommendations for the specified connection.
    """
    # Return empty recommendations in demo mode
    if DEMO_MODE:
        return RecommendationReportResponse(
            recommended_tables=[],
            excluded_tables=[],
            total_tables_analyzed=0,
            recommendation_confidence=0.0,
            analysis_metadata={}
        )
    
    try:
        report = service.generate_recommendations(
            connection_id=request.connection_id,
            schema=request.schema,
            include_columns=request.include_columns,
        )
        
        # Convert to response model (same as get_recommendations)
        return _convert_report_to_response(report)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh recommendations: {str(e)}")

