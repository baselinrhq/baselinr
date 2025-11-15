"""
ProfileMesh Dashboard Backend API

FastAPI server that provides endpoints for:
- Run history
- Profiling results
- Drift detection alerts  
- Metrics and KPIs
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import List, Optional
import os

from models import (
    RunHistoryResponse,
    ProfilingResultResponse,
    DriftAlertResponse,
    MetricsDashboardResponse,
    TableMetricsResponse
)
from database import DatabaseClient

# Initialize FastAPI app
app = FastAPI(
    title="ProfileMesh Dashboard API",
    description="Backend API for ProfileMesh internal dashboard",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database client
db_client = DatabaseClient()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ProfileMesh Dashboard API",
        "version": "2.0.0"
    }


@app.get("/api/runs", response_model=List[RunHistoryResponse])
async def get_runs(
    warehouse: Optional[str] = Query(None, description="Filter by warehouse type"),
    schema: Optional[str] = Query(None, description="Filter by schema"),
    table: Optional[str] = Query(None, description="Filter by table name"),
    status: Optional[str] = Query(None, description="Filter by status"),
    days: int = Query(30, description="Number of days to look back"),
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Offset for pagination")
):
    """
    Get profiling run history with optional filters.
    
    Returns a list of profiling runs with metadata.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    runs = await db_client.get_runs(
        warehouse=warehouse,
        schema=schema,
        table=table,
        status=status,
        start_date=start_date,
        limit=limit,
        offset=offset
    )
    
    return runs


@app.get("/api/runs/{run_id}", response_model=ProfilingResultResponse)
async def get_run_details(run_id: str):
    """
    Get detailed profiling results for a specific run.
    
    Includes table-level and column-level metrics.
    """
    result = await db_client.get_run_details(run_id)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    return result


@app.get("/api/drift", response_model=List[DriftAlertResponse])
async def get_drift_alerts(
    warehouse: Optional[str] = Query(None),
    table: Optional[str] = Query(None),
    severity: Optional[str] = Query(None, description="low, medium, high"),
    days: int = Query(30),
    limit: int = Query(100),
    offset: int = Query(0)
):
    """
    Get drift detection alerts with optional filters.
    
    Returns detected drift events with affected tables/columns.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    alerts = await db_client.get_drift_alerts(
        warehouse=warehouse,
        table=table,
        severity=severity,
        start_date=start_date,
        limit=limit,
        offset=offset
    )
    
    return alerts


@app.get("/api/tables/{table_name}/metrics", response_model=TableMetricsResponse)
async def get_table_metrics(
    table_name: str,
    schema: Optional[str] = Query(None),
    warehouse: Optional[str] = Query(None)
):
    """
    Get detailed metrics for a specific table.
    
    Includes historical trends and column-level breakdowns.
    """
    metrics = await db_client.get_table_metrics(
        table_name=table_name,
        schema=schema,
        warehouse=warehouse
    )
    
    if not metrics:
        raise HTTPException(status_code=404, detail=f"Table {table_name} not found")
    
    return metrics


@app.get("/api/dashboard/metrics", response_model=MetricsDashboardResponse)
async def get_dashboard_metrics(
    warehouse: Optional[str] = Query(None),
    days: int = Query(30)
):
    """
    Get aggregate metrics for the dashboard overview.
    
    Includes KPIs, trends, and warehouse-level summaries.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    metrics = await db_client.get_dashboard_metrics(
        warehouse=warehouse,
        start_date=start_date
    )
    
    return metrics


@app.get("/api/warehouses")
async def get_warehouses():
    """
    Get list of available warehouses.
    
    Returns warehouse types and their connection status.
    """
    warehouses = await db_client.get_warehouses()
    return {"warehouses": warehouses}


@app.get("/api/export/runs")
async def export_runs(
    format: str = Query("json", pattern="^(json|csv)$"),
    warehouse: Optional[str] = None,
    days: int = 30
):
    """
    Export run history data.
    
    Supports JSON and CSV formats.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    data = await db_client.export_runs(
        format=format,
        warehouse=warehouse,
        start_date=start_date
    )
    
    return data


@app.get("/api/export/drift")
async def export_drift(
    format: str = Query("json", pattern="^(json|csv)$"),
    warehouse: Optional[str] = None,
    days: int = 30
):
    """
    Export drift alert data.
    
    Supports JSON and CSV formats.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    data = await db_client.export_drift(
        format=format,
        warehouse=warehouse,
        start_date=start_date
    )
    
    return data


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

