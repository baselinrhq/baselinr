"""
RCA API routes for Baselinr Dashboard.
"""

import json
import sys
import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Add parent directory to path to import baselinr
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from baselinr.rca.service import RCAService
from baselinr.rca.storage import RCAStorage
from baselinr.rca.collectors.code_change_collector import CodeChangeCollector

from rca_models import (
    AnalyzeRequestBody,
    CodeDeploymentResponse,
    EventTimelineResponse,
    PipelineRunResponse,
    ProbableCauseResponse,
    RCAListResponse,
    RCAResultResponse,
    RCAStatisticsResponse,
)
from database import DatabaseClient

router = APIRouter(prefix="/api/rca", tags=["rca"])

# Global instances
_db_client = None
_engine = None
_demo_mode = False

def get_db_client():
    """Get or create database client instance."""
    global _db_client
    if _demo_mode:
        return None
    if _db_client is None:
        _db_client = DatabaseClient()
    return _db_client

def get_rca_service():
    """Get or create RCA service instance."""
    if _demo_mode:
        return None
    db_client = get_db_client()
    return RCAService(
        engine=db_client.engine,
        auto_analyze=False,  # Disabled for API mode
        lookback_window_hours=24,
        max_depth=5,
        max_causes_to_return=5,
        min_confidence_threshold=0.3,
        enable_pattern_learning=True,
    )

def get_rca_storage():
    """Get or create RCA storage instance."""
    if _demo_mode:
        return None
    db_client = get_db_client()
    return RCAStorage(db_client.engine)


@router.post("/analyze", response_model=RCAResultResponse)
async def analyze_anomaly(body: AnalyzeRequestBody):
    """
    Trigger RCA for a specific anomaly.

    Analyzes temporal correlations, lineage relationships, and historical patterns
    to identify probable root causes.
    """
    try:
        service = get_rca_service()

        result = service.analyze_anomaly(
            anomaly_id=body.anomaly_id,
            table_name=body.table_name,
            anomaly_timestamp=body.anomaly_timestamp,
            schema_name=body.schema_name,
            column_name=body.column_name,
            metric_name=body.metric_name,
            anomaly_type=body.anomaly_type,
        )

        # Convert to response model
        return RCAResultResponse(
            anomaly_id=result.anomaly_id,
            table_name=result.table_name,
            schema_name=result.schema_name,
            column_name=result.column_name,
            metric_name=result.metric_name,
            analyzed_at=result.analyzed_at,
            rca_status=result.rca_status,
            probable_causes=[
                ProbableCauseResponse(**cause) for cause in result.probable_causes
            ],
            impact_analysis=(
                {
                    "upstream_affected": result.impact_analysis.upstream_affected,
                    "downstream_affected": result.impact_analysis.downstream_affected,
                    "blast_radius_score": result.impact_analysis.blast_radius_score,
                }
                if result.impact_analysis
                else None
            ),
            metadata=result.metadata,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RCA analysis failed: {str(e)}")


@router.get("/{anomaly_id}", response_model=RCAResultResponse)
async def get_rca_result(anomaly_id: str):
    """
    Get stored RCA result for an anomaly.

    Returns cached analysis results if available.
    """
    try:
        storage = get_rca_storage()
        result = storage.get_rca_result(anomaly_id)

        if not result:
            raise HTTPException(status_code=404, detail=f"RCA result not found for {anomaly_id}")

        return RCAResultResponse(
            anomaly_id=result.anomaly_id,
            table_name=result.table_name,
            schema_name=result.schema_name,
            column_name=result.column_name,
            metric_name=result.metric_name,
            analyzed_at=result.analyzed_at,
            rca_status=result.rca_status,
            probable_causes=[
                ProbableCauseResponse(**cause) for cause in result.probable_causes
            ],
            impact_analysis=(
                {
                    "upstream_affected": result.impact_analysis.upstream_affected,
                    "downstream_affected": result.impact_analysis.downstream_affected,
                    "blast_radius_score": result.impact_analysis.blast_radius_score,
                }
                if result.impact_analysis
                else None
            ),
            metadata=result.metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get RCA result: {str(e)}")


@router.get("/", response_model=List[RCAListResponse])
async def list_rca_results(
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None, pattern="^(analyzed|pending|dismissed)$"),
):
    """
    Get list of recent RCA results.

    Returns summary information for recent analyses.
    """
    # Return empty list in demo mode
    if _demo_mode:
        return []
    
    try:
        service = get_rca_service()
        results = service.get_recent_rca_results(limit=limit)

        # Filter by status if provided
        if status:
            results = [r for r in results if r.get("rca_status") == status]

        # Ensure all results have required fields and correct types
        cleaned_results = []
        for r in results:
            cleaned = {
                "anomaly_id": str(r.get("anomaly_id", "")),
                "table_name": str(r.get("table_name", "")),
                "schema_name": r.get("schema_name"),
                "column_name": r.get("column_name"),
                "metric_name": r.get("metric_name"),
                "analyzed_at": str(r.get("analyzed_at", "")),
                "rca_status": str(r.get("rca_status", "pending")),
                "num_causes": int(r.get("num_causes", 0)),
                "top_cause": r.get("top_cause"),
            }
            cleaned_results.append(RCAListResponse(**cleaned))

        return cleaned_results

    except Exception as e:
        logger.error(f"Failed to list RCA results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list RCA results: {str(e)}")


@router.get("/statistics/summary", response_model=RCAStatisticsResponse)
async def get_rca_statistics():
    """
    Get RCA statistics.

    Returns aggregate statistics about RCA operations.
    """
    # Return zero stats in demo mode
    if _demo_mode:
        return RCAStatisticsResponse(
            total_analyses=0,
            analyzed=0,
            dismissed=0,
            pending=0,
            avg_causes_per_anomaly=0.0
        )
    
    try:
        service = get_rca_service()
        stats = service.get_rca_statistics()
        
        logger.debug(f"RCA statistics retrieved: {stats}")
        
        # Ensure all values are the correct type (convert Decimal to float/int if needed)
        stats_clean = {
            "total_analyses": int(stats.get("total_analyses", 0)),
            "analyzed": int(stats.get("analyzed", 0)),
            "dismissed": int(stats.get("dismissed", 0)),
            "pending": int(stats.get("pending", 0)),
            "avg_causes_per_anomaly": float(stats.get("avg_causes_per_anomaly", 0.0)),
        }

        return RCAStatisticsResponse(**stats_clean)

    except Exception as e:
        logger.error(f"Failed to get RCA statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.post("/{anomaly_id}/reanalyze", response_model=RCAResultResponse)
async def reanalyze_anomaly(anomaly_id: str):
    """
    Re-run RCA for an existing anomaly.

    Useful after new data is available or patterns have been learned.
    """
    try:
        service = get_rca_service()
        result = service.reanalyze_anomaly(anomaly_id)

        if not result:
            raise HTTPException(status_code=404, detail=f"Anomaly {anomaly_id} not found")

        return RCAResultResponse(
            anomaly_id=result.anomaly_id,
            table_name=result.table_name,
            schema_name=result.schema_name,
            column_name=result.column_name,
            metric_name=result.metric_name,
            analyzed_at=result.analyzed_at,
            rca_status=result.rca_status,
            probable_causes=[
                ProbableCauseResponse(**cause) for cause in result.probable_causes
            ],
            impact_analysis=(
                {
                    "upstream_affected": result.impact_analysis.upstream_affected,
                    "downstream_affected": result.impact_analysis.downstream_affected,
                    "blast_radius_score": result.impact_analysis.blast_radius_score,
                }
                if result.impact_analysis
                else None
            ),
            metadata=result.metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reanalysis failed: {str(e)}")


@router.delete("/{anomaly_id}")
async def dismiss_rca_result(
    anomaly_id: str,
    reason: Optional[str] = Query(None, description="Reason for dismissing"),
):
    """
    Mark an RCA result as dismissed.

    Used when the analysis is not relevant or has been resolved.
    """
    try:
        service = get_rca_service()
        service.dismiss_rca_result(anomaly_id, reason)

        return {"status": "dismissed", "anomaly_id": anomaly_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dismiss: {str(e)}")


@router.get("/pipeline-runs/recent", response_model=List[PipelineRunResponse])
async def get_recent_pipeline_runs(
    limit: int = Query(20, ge=1, le=100),
    pipeline_name: Optional[str] = None,
    status: Optional[str] = None,
):
    """
    Get recent pipeline runs.

    Returns pipeline execution history.
    """
    try:
        storage = get_rca_storage()
        runs = storage.get_pipeline_runs(
            start_time=datetime.utcnow() - timedelta(days=7),
            pipeline_name=pipeline_name,
            status=status,
            limit=limit,
        )

        return [
            PipelineRunResponse(
                run_id=run.run_id,
                pipeline_name=run.pipeline_name,
                pipeline_type=run.pipeline_type,
                started_at=run.started_at,
                completed_at=run.completed_at,
                duration_seconds=run.duration_seconds,
                status=run.status,
                input_row_count=run.input_row_count,
                output_row_count=run.output_row_count,
                git_commit_sha=run.git_commit_sha,
                git_branch=run.git_branch,
                affected_tables=run.affected_tables,
            )
            for run in runs
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pipeline runs: {str(e)}")


@router.get("/deployments/recent", response_model=List[CodeDeploymentResponse])
async def get_recent_deployments(
    limit: int = Query(20, ge=1, le=100),
    git_commit_sha: Optional[str] = None,
):
    """
    Get recent code deployments.

    Returns deployment history.
    """
    try:
        storage = get_rca_storage()
        deployments = storage.get_code_deployments(
            start_time=datetime.utcnow() - timedelta(days=7),
            git_commit_sha=git_commit_sha,
            limit=limit,
        )

        return [
            CodeDeploymentResponse(
                deployment_id=dep.deployment_id,
                deployed_at=dep.deployed_at,
                git_commit_sha=dep.git_commit_sha,
                git_branch=dep.git_branch,
                changed_files=dep.changed_files,
                deployment_type=dep.deployment_type,
                affected_pipelines=dep.affected_pipelines,
            )
            for dep in deployments
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get deployments: {str(e)}")


@router.get("/timeline", response_model=List[EventTimelineResponse])
async def get_events_timeline(
    start_time: str = Query(..., description="Start of time window (ISO format)"),
    end_time: str = Query(..., description="End of time window (ISO format)"),
    asset_name: Optional[str] = Query(None, description="Filter by table/asset name"),
):
    """
    Get timeline view of events (anomalies, pipeline runs, deployments).

    Returns chronologically ordered events for RCA visualization.
    """
    try:
        # Parse datetime strings
        try:
            start_time_obj = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        except ValueError:
            try:
                start_time_obj = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_time format. Use ISO format (YYYY-MM-DDTHH:MM or YYYY-MM-DDTHH:MM:SS)")
        
        try:
            end_time_obj = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        except ValueError:
            try:
                end_time_obj = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_time format. Use ISO format (YYYY-MM-DDTHH:MM or YYYY-MM-DDTHH:MM:SS)")

        db_client = get_db_client()
        events = []

        # Get anomalies from events table
        anomaly_query = text(
            """
            SELECT event_id, event_type, table_name, column_name, metric_name,
                   timestamp, drift_severity, metadata
            FROM baselinr_events
            WHERE event_type = 'AnomalyDetected'
            AND timestamp >= :start_time
            AND timestamp <= :end_time
            AND (:asset_name IS NULL OR table_name = :asset_name)
            ORDER BY timestamp DESC
            LIMIT 50
        """
        )

        with db_client.engine.connect() as conn:
            result = conn.execute(
                anomaly_query,
                {
                    "start_time": start_time_obj,
                    "end_time": end_time_obj,
                    "asset_name": asset_name,
                },
            )

            for row in result:
                events.append(
                    EventTimelineResponse(
                        timestamp=row[5],
                        event_type="anomaly",
                        event_data={
                            "event_id": row[0],
                            "table_name": row[2],
                            "column_name": row[3],
                            "metric_name": row[4],
                            "severity": row[6],
                        },
                        relevance_score=1.0,
                    )
                )

        # Get pipeline runs
        storage = get_rca_storage()
        runs = storage.get_pipeline_runs(
            start_time=start_time_obj, end_time=end_time_obj, limit=50
        )

        for run in runs:
            relevance = 1.0 if asset_name in run.affected_tables else 0.5
            events.append(
                EventTimelineResponse(
                    timestamp=run.started_at,
                    event_type="pipeline_run",
                    event_data={
                        "run_id": run.run_id,
                        "pipeline_name": run.pipeline_name,
                        "status": run.status,
                        "affected_tables": run.affected_tables,
                    },
                    relevance_score=relevance,
                )
            )

        # Get deployments
        deployments = storage.get_code_deployments(
            start_time=start_time_obj, end_time=end_time_obj, limit=50
        )

        for dep in deployments:
            events.append(
                EventTimelineResponse(
                    timestamp=dep.deployed_at,
                    event_type="code_deployment",
                    event_data={
                        "deployment_id": dep.deployment_id,
                        "git_commit_sha": dep.git_commit_sha,
                        "deployment_type": dep.deployment_type,
                        "affected_pipelines": dep.affected_pipelines,
                    },
                    relevance_score=0.7,
                )
            )

        # Sort by timestamp (most recent first)
        events.sort(key=lambda e: e.timestamp, reverse=True)

        return events[:100]  # Limit to 100 events

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get timeline: {str(e)}")


def register_routes(app, db_engine):
    """
    Register RCA routes with the FastAPI app.

    Args:
        app: FastAPI application instance
        db_engine: Database engine (None in demo mode)
    """
    global _engine, _demo_mode
    _engine = db_engine
    _demo_mode = (db_engine is None)
    
    if _demo_mode:
        logger.info("RCA routes registered in demo mode - will return empty data")
    
    # Simply include the router - routes now use get_db_client() internally
    app.include_router(router)
