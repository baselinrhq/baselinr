"""
Baselinr Dashboard Backend API

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
import sys
import logging

logger = logging.getLogger(__name__)

from models import (
    RunHistoryResponse,
    ProfilingResultResponse,
    RunComparisonResponse,
    DriftAlertResponse,
    MetricsDashboardResponse,
    TableMetricsResponse,
    TableListResponse,
    TableOverviewResponse,
    TableDriftHistoryResponse,
    TableValidationResultsResponse,
    TableConfigResponse,
    DriftSummaryResponse,
    DriftDetailsResponse,
    DriftImpactResponse,
    ValidationSummaryResponse,
    ValidationResultsListResponse,
    ValidationResultDetailsResponse,
    ValidationFailureSamplesResponse
)
from lineage_models import (
    LineageGraphResponse,
    LineageNodeResponse,
    LineageEdgeResponse,
    NodeDetailsResponse,
    TableInfoResponse,
    DriftPathResponse,
    LineageImpactResponse,
)
from database import DatabaseClient
from demo_data_service import DemoDataService
import rca_routes
import chat_routes
import config_routes
import connection_routes
import contracts_routes
import discovery_routes
import hook_routes
import recommendation_routes
import validation_routes
import quality_routes

# Check if demo mode is enabled
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Initialize FastAPI app
app = FastAPI(
    title="Baselinr Dashboard API",
    description="Backend API for Baselinr internal dashboard" + (" - DEMO MODE" if DEMO_MODE else ""),
    version="2.0.0"
)

# Configure CORS with demo domain support
allowed_origins = [
    "http://localhost:3000",  # Next.js default port
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

# Add demo domain if in demo mode
if DEMO_MODE:
    allowed_origins.extend([
        "https://demo.baselinr.io",
        "https://*.pages.dev",  # Cloudflare Pages preview URLs
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database client or demo service based on mode
if DEMO_MODE:
    logger.info("Starting in DEMO MODE - using DemoDataService")
    db_client = DemoDataService()
else:
    logger.info("Starting in DATABASE MODE - using DatabaseClient")
    db_client = DatabaseClient()

# Register RCA routes
if DEMO_MODE:
    # In demo mode, register routes with None engine (will return empty data)
    logger.info("RCA routes enabled in demo mode (returning empty data)")
    rca_routes.register_routes(app, None)
elif hasattr(db_client, 'engine'):
    rca_routes.register_routes(app, db_client.engine)

# Register config and connection routes
app.include_router(config_routes.router)
app.include_router(connection_routes.router)
app.include_router(contracts_routes.router)
app.include_router(discovery_routes.router)
app.include_router(hook_routes.router)
app.include_router(recommendation_routes.router)
app.include_router(validation_routes.router)
app.include_router(quality_routes.router)


# Load config for chat (from environment or default)
def _load_chat_config():
    """Load chat configuration from environment or config file."""
    import yaml

    config = {
        "llm": {
            "enabled": os.getenv("LLM_ENABLED", "false").lower() == "true",
            "provider": os.getenv("LLM_PROVIDER", "openai"),
            "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
            "api_key": os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"),
            "chat": {
                "max_iterations": int(os.getenv("CHAT_MAX_ITERATIONS", "5")),
                "max_history_messages": int(os.getenv("CHAT_MAX_HISTORY", "20")),
                "tool_timeout": int(os.getenv("CHAT_TOOL_TIMEOUT", "30")),
            }
        },
        "storage": {
            "runs_table": os.getenv("BASELINR_RUNS_TABLE", "baselinr_runs"),
            "results_table": os.getenv("BASELINR_RESULTS_TABLE", "baselinr_results"),
        }
    }

    # Try to find config file
    config_path = os.getenv("BASELINR_CONFIG")
    
    # If not set, try common locations
    if not config_path:
        # Get the project root (assuming backend is in dashboard/backend/)
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(backend_dir, "../../"))
        
        # Try common config file locations
        possible_paths = [
            os.path.join(project_root, "examples", "config.yml"),
            os.path.join(project_root, "config.yml"),
            os.path.join(project_root, "baselinr", "examples", "config.yml"),
            "examples/config.yml",
            "config.yml",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                print(f"Found config file at: {config_path}")
                break
    
    # Load from config file if found
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    # Deep merge llm config (including nested chat config)
                    if "llm" in file_config:
                        llm_file = file_config["llm"]
                        # Update top-level llm settings
                        if "enabled" in llm_file:
                            # Ensure boolean conversion (handle string "true"/"false")
                            enabled_val = llm_file["enabled"]
                            if isinstance(enabled_val, str):
                                config["llm"]["enabled"] = enabled_val.lower() in ("true", "1", "yes")
                            else:
                                config["llm"]["enabled"] = bool(enabled_val)
                        if "provider" in llm_file:
                            config["llm"]["provider"] = llm_file["provider"]
                        if "model" in llm_file:
                            config["llm"]["model"] = llm_file["model"]
                        if "api_key" in llm_file:
                            # Support environment variable expansion
                            api_key = llm_file["api_key"]
                            if isinstance(api_key, str) and api_key.startswith("${") and api_key.endswith("}"):
                                env_var = api_key[2:-1]
                                config["llm"]["api_key"] = os.getenv(env_var) or api_key
                            else:
                                config["llm"]["api_key"] = api_key
                        # Merge chat config if present
                        if "chat" in llm_file:
                            chat_file = llm_file["chat"]
                            if isinstance(chat_file, dict):
                                # Handle boolean conversion for chat.enabled if present
                                if "enabled" in chat_file:
                                    chat_enabled = chat_file["enabled"]
                                    if isinstance(chat_enabled, str):
                                        chat_file["enabled"] = chat_enabled.lower() in ("true", "1", "yes")
                                    else:
                                        chat_file["enabled"] = bool(chat_enabled)
                                config["llm"]["chat"].update(chat_file)
                    
                    # Merge storage config
                    if "storage" in file_config:
                        storage_file = file_config["storage"]
                        if "runs_table" in storage_file:
                            config["storage"]["runs_table"] = storage_file["runs_table"]
                        if "results_table" in storage_file:
                            config["storage"]["results_table"] = storage_file["results_table"]
                    
                    print(f"Loaded LLM config: enabled={config['llm']['enabled']}, provider={config['llm']['provider']}, has_api_key={bool(config['llm']['api_key'])}")
        except Exception as e:
            print(f"Warning: Could not load config from {config_path}: {e}")

    return config


chat_config = _load_chat_config()

# Register Chat routes (only if not in demo mode, as chat requires database)
if not DEMO_MODE and hasattr(db_client, 'engine'):
    chat_routes.register_chat_routes(app, db_client.engine, chat_config)
elif DEMO_MODE:
    logger.info("Chat routes disabled in demo mode")

# Import baselinr visualization components
# Add parent directory to path to import baselinr
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

try:
    from baselinr.visualization import LineageGraphBuilder
    LINEAGE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Lineage visualization not available: {e}")
    LINEAGE_AVAILABLE = False


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Baselinr Dashboard API",
        "version": "2.0.0",
        "mode": "demo" if DEMO_MODE else "database"
    }


@app.get("/api/demo/info")
async def get_demo_info():
    """Get demo mode information and metadata."""
    if not DEMO_MODE:
        raise HTTPException(status_code=404, detail="Demo mode not enabled")
    
    # Get demo metadata if available
    metadata = {}
    if hasattr(db_client, 'metadata'):
        metadata = db_client.metadata
    
    return {
        "demo_mode": True,
        "metadata": metadata,
        "statistics": {
            "total_runs": len(db_client.runs_raw) if hasattr(db_client, 'runs_raw') else 0,
            "total_metrics": len(db_client.metrics_raw) if hasattr(db_client, 'metrics_raw') else 0,
            "total_drift_events": len(db_client.drift_events_raw) if hasattr(db_client, 'drift_events_raw') else 0,
            "total_tables": len(db_client.tables_raw) if hasattr(db_client, 'tables_raw') else 0,
            "total_validation_results": len(db_client.validation_results_raw) if hasattr(db_client, 'validation_results_raw') else 0,
        },
        "features": {
            "read_only": True,
            "real_time_updates": False,
            "data_source": "pre-generated_json"
        }
    }


@app.get("/api/runs", response_model=List[RunHistoryResponse])
async def get_runs(
    warehouse: Optional[str] = Query(None, description="Filter by warehouse type"),
    schema: Optional[str] = Query(None, description="Filter by schema"),
    table: Optional[str] = Query(None, description="Filter by table name"),
    status: Optional[str] = Query(None, description="Filter by status (comma-separated for multiple)"),
    days: Optional[int] = Query(None, description="Number of days to look back"),
    start_date: Optional[str] = Query(None, description="Start date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    end_date: Optional[str] = Query(None, description="End date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    min_duration: Optional[float] = Query(None, description="Minimum duration in seconds"),
    max_duration: Optional[float] = Query(None, description="Maximum duration in seconds"),
    sort_by: str = Query("profiled_at", description="Sort by column (profiled_at, row_count, column_count, status)"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Offset for pagination")
):
    """
    Get profiling run history with optional filters.
    
    Returns a list of profiling runs with metadata.
    """
    # Parse dates if provided
    start_date_obj = None
    end_date_obj = None
    
    if start_date:
        try:
            start_date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use ISO format.")
    elif days:
        # Backward compatibility: use days if start_date not provided
        start_date_obj = datetime.utcnow() - timedelta(days=days)
    
    if end_date:
        try:
            end_date_obj = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                # Set to end of day
                end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use ISO format.")
    
    runs = await db_client.get_runs(
        warehouse=warehouse,
        schema=schema,
        table=table,
        status=status,
        start_date=start_date_obj,
        end_date=end_date_obj,
        min_duration=min_duration,
        max_duration=max_duration,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset
    )
    
    return runs


@app.get("/api/runs/compare", response_model=RunComparisonResponse)
async def compare_runs(
    run_ids: str = Query(..., description="Comma-separated list of run IDs to compare (2-5 runs)")
):
    """
    Compare multiple runs side-by-side.
    
    Returns comparison data including:
    - Row and column count differences
    - Common columns across runs
    - Unique columns per run
    - Metric differences for common columns
    """
    run_id_list = [rid.strip() for rid in run_ids.split(',')]
    
    if len(run_id_list) < 2:
        raise HTTPException(status_code=400, detail="At least 2 run IDs required for comparison")
    if len(run_id_list) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 runs can be compared at once")
    
    try:
        comparison = await db_client.compare_runs(run_id_list)
        return comparison
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare runs: {str(e)}")


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


@app.post("/api/runs/{run_id}/retry")
async def retry_run(run_id: str):
    """
    Retry a failed run.
    
    Note: This is a placeholder endpoint. Actual retry functionality
    requires integration with the profiling service.
    """
    # Check if run exists
    result = await db_client.get_run_details(run_id)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    # TODO: Integrate with profiling service to actually retry the run
    # For now, return a placeholder response
    return {
        "status": "pending",
        "message": "Retry request received. Integration with profiling service pending.",
        "run_id": run_id
    }


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


@app.get("/api/drift/summary", response_model=DriftSummaryResponse)
async def get_drift_summary(
    warehouse: Optional[str] = Query(None),
    days: int = Query(30)
):
    """
    Get drift summary statistics.
    
    Returns aggregate drift statistics including:
    - Total events by severity
    - Trending data over time
    - Top affected tables
    - Warehouse breakdown
    - Recent activity
    """
    summary = await db_client.get_drift_summary(
        warehouse=warehouse,
        days=days
    )
    return summary


@app.get("/api/drift/{event_id}/details", response_model=DriftDetailsResponse)
async def get_drift_details(event_id: str):
    """
    Get detailed drift information for a specific event.
    
    Returns:
    - Full baseline vs current comparison
    - Statistical test results (if available)
    - Historical context (previous values)
    - Related drift events
    """
    try:
        details = await db_client.get_drift_details(event_id)
        return details
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get drift details: {str(e)}")


@app.get("/api/drift/{event_id}/impact", response_model=DriftImpactResponse)
async def get_drift_impact(event_id: str):
    """
    Get drift impact analysis.
    
    Returns:
    - Downstream table impact (via lineage)
    - Affected metrics count
    - Business impact assessment
    - Recommendations
    """
    try:
        impact = await db_client.get_drift_impact(event_id)
        return impact
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get drift impact: {str(e)}")


@app.get("/api/tables", response_model=TableListResponse)
async def get_tables(
    warehouse: Optional[str] = Query(None),
    schema: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    has_drift: Optional[bool] = Query(None),
    has_failed_validations: Optional[bool] = Query(None),
    sort_by: str = Query("table_name"),
    sort_order: str = Query("asc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    Get list of profiled tables with filters, sorting, and pagination.
    """
    result = await db_client.get_tables(
        warehouse=warehouse,
        schema=schema,
        search=search,
        has_drift=has_drift,
        has_failed_validations=has_failed_validations,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )
    
    return result


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


@app.get("/api/tables/{table}/overview", response_model=TableOverviewResponse)
async def get_table_overview(
    table: str,
    schema: Optional[str] = Query(None),
    warehouse: Optional[str] = Query(None)
):
    """
    Get enhanced table overview with additional stats and recent runs.
    """
    overview = await db_client.get_table_overview(
        table_name=table,
        schema=schema,
        warehouse=warehouse
    )
    
    if not overview:
        raise HTTPException(status_code=404, detail=f"Table {table} not found")
    
    return overview


@app.get("/api/tables/{table}/drift-history", response_model=TableDriftHistoryResponse)
async def get_table_drift_history(
    table: str,
    schema: Optional[str] = Query(None),
    warehouse: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get drift history for a specific table.
    """
    history = await db_client.get_table_drift_history(
        table_name=table,
        schema=schema,
        warehouse=warehouse,
        limit=limit
    )
    
    return history


@app.get("/api/tables/{table}/validation-results", response_model=TableValidationResultsResponse)
async def get_table_validation_results(
    table: str,
    schema: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get validation results for a specific table.
    """
    results = await db_client.get_table_validation_results(
        table_name=table,
        schema=schema,
        limit=limit
    )
    
    return results


@app.get("/api/validation/summary", response_model=ValidationSummaryResponse)
async def get_validation_summary(
    warehouse: Optional[str] = Query(None),
    days: int = Query(30)
):
    """
    Get validation summary statistics.
    
    Returns aggregate statistics including pass/fail rates, breakdowns by rule type,
    severity, and table, plus trending data and recent validation runs.
    """
    summary = await db_client.get_validation_summary(
        warehouse=warehouse,
        days=days
    )
    
    return summary


@app.get("/api/validation/results", response_model=ValidationResultsListResponse)
async def get_validation_results(
    table: Optional[str] = Query(None),
    schema: Optional[str] = Query(None),
    rule_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    passed: Optional[bool] = Query(None),
    days: int = Query(30),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000)
):
    """
    List validation results with filtering and pagination.
    
    Supports filtering by table, schema, rule type, severity, and pass status.
    """
    results = await db_client.get_validation_results(
        table=table,
        schema=schema,
        rule_type=rule_type,
        severity=severity,
        passed=passed,
        days=days,
        page=page,
        page_size=page_size
    )
    
    return results


@app.get("/api/validation/results/{result_id}", response_model=ValidationResultDetailsResponse)
async def get_validation_result_details(result_id: int):
    """
    Get detailed validation result information.
    
    Returns full result details, rule configuration, associated run information,
    and historical context (previous validations for same rule).
    """
    try:
        details = await db_client.get_validation_result_details(result_id)
        return details
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/validation/results/{result_id}/failures", response_model=ValidationFailureSamplesResponse)
async def get_validation_failure_samples(result_id: int):
    """
    Get failure samples for a validation result.
    
    Returns sample failed rows (up to 100), failure reasons per row,
    and column values that failed validation.
    """
    try:
        samples = await db_client.get_validation_failure_samples(result_id)
        return samples
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/tables/{table}/config", response_model=TableConfigResponse)
async def get_table_config(
    table: str,
    schema: Optional[str] = Query(None)
):
    """
    Get table configuration (placeholder for now).
    """
    # TODO: Implement actual config retrieval
    return TableConfigResponse(
        table_name=table,
        schema_name=schema,
        config={}
    )


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


# ============================================================================
# LINEAGE ENDPOINTS
# ============================================================================

@app.get("/api/lineage/graph", response_model=LineageGraphResponse)
async def get_lineage_graph(
    table: str = Query(..., description="Table name"),
    schema: Optional[str] = Query(None, description="Schema name"),
    direction: str = Query("both", pattern="^(upstream|downstream|both)$"),
    depth: int = Query(3, ge=1, le=10, description="Maximum depth to traverse"),
    confidence_threshold: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence score"),
    provider: Optional[str] = Query(None, description="Filter by lineage provider (comma-separated)"),
    schemas: Optional[str] = Query(None, description="Filter by schemas (comma-separated)"),
    databases: Optional[str] = Query(None, description="Filter by databases (comma-separated)"),
    node_type: Optional[str] = Query(None, pattern="^(table|column|both)$", description="Filter by node type"),
    has_drift: Optional[bool] = Query(None, description="Filter nodes with drift"),
    drift_severity: Optional[str] = Query(None, pattern="^(low|medium|high)$", description="Filter by drift severity"),
):
    """
    Get lineage graph for a table.
    
    Returns nodes and edges representing the lineage relationships.
    """
    if not LINEAGE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Lineage visualization not available")
    
    # In demo mode, return demo lineage data
    if DEMO_MODE:
        try:
            nodes_raw = db_client.lineage_raw.get('nodes', [])
            edges_raw = db_client.lineage_raw.get('edges', [])
            
            # Convert to response models
            nodes = [LineageNodeResponse(**node) for node in nodes_raw]
            edges = [LineageEdgeResponse(**edge) for edge in edges_raw]
            
            # Find root node
            root_id = None
            for node in nodes_raw:
                if node.get('table') == table and (not schema or node.get('schema') == schema):
                    root_id = node.get('id')
                    break
            
            return LineageGraphResponse(
                nodes=nodes,
                edges=edges,
                root_id=root_id,
                direction=direction
            )
        except Exception as e:
            logger.error(f"Failed to get demo lineage graph: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to build lineage graph: {str(e)}")
    
    try:
        builder = LineageGraphBuilder(db_client.engine)
        graph = builder.build_table_graph(
            root_table=table,
            schema=schema,
            direction=direction,
            max_depth=depth,
            confidence_threshold=confidence_threshold,
        )
        
        # Parse filter parameters
        provider_list = [p.strip() for p in provider.split(',')] if provider else None
        schema_list = [s.strip() for s in schemas.split(',')] if schemas else None
        database_list = [d.strip() for d in databases.split(',')] if databases else None
        
        # Filter nodes
        filtered_nodes = []
        for node in graph.nodes:
            # Provider filter
            if provider_list:
                node_providers = node.metadata.get("providers", [])
                if not any(p in node_providers for p in provider_list):
                    continue
            
            # Schema filter
            if schema_list and node.schema:
                if node.schema not in schema_list:
                    continue
            
            # Database filter
            if database_list and node.database:
                if node.database not in database_list:
                    continue
            
            # Node type filter
            if node_type and node_type != "both":
                if node.type != node_type:
                    continue
            
            # Drift filter
            if has_drift is not None:
                node_has_drift = node.metadata.get("has_drift", False)
                if node_has_drift != has_drift:
                    continue
            
            # Drift severity filter
            if drift_severity:
                node_severity = node.metadata.get("drift_severity")
                if node_severity != drift_severity:
                    continue
            
            filtered_nodes.append(node)
        
        # Filter edges to only include edges between filtered nodes
        filtered_node_ids = {node.id for node in filtered_nodes}
        filtered_edges = [
            edge for edge in graph.edges
            if edge.source in filtered_node_ids and edge.target in filtered_node_ids
        ]
        
        # Provider filter for edges
        if provider_list:
            filtered_edges = [
                edge for edge in filtered_edges
                if edge.provider in provider_list
            ]
        
        # Convert to response model
        nodes = [
            LineageNodeResponse(**node.to_dict())
            for node in filtered_nodes
        ]
        edges = [
            LineageEdgeResponse(**edge.to_dict())
            for edge in filtered_edges
        ]
        
        return LineageGraphResponse(
            nodes=nodes,
            edges=edges,
            root_id=graph.root_id if graph.root_id in filtered_node_ids else None,
            direction=graph.direction,
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build lineage graph: {str(e)}")


@app.get("/api/lineage/column-graph", response_model=LineageGraphResponse)
async def get_column_lineage_graph(
    table: str = Query(..., description="Table name"),
    column: str = Query(..., description="Column name"),
    schema: Optional[str] = Query(None, description="Schema name"),
    direction: str = Query("both", pattern="^(upstream|downstream|both)$"),
    depth: int = Query(3, ge=1, le=10, description="Maximum depth to traverse"),
    confidence_threshold: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence score"),
):
    """
    Get column-level lineage graph.
    
    Returns nodes and edges representing column-level dependencies.
    """
    if not LINEAGE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Lineage visualization not available")
    
    try:
        builder = LineageGraphBuilder(db_client.engine)
        graph = builder.build_column_graph(
            root_table=table,
            root_column=column,
            schema=schema,
            direction=direction,
            max_depth=depth,
            confidence_threshold=confidence_threshold,
        )
        
        # Convert to response model
        nodes = [
            LineageNodeResponse(**node.to_dict())
            for node in graph.nodes
        ]
        edges = [
            LineageEdgeResponse(**edge.to_dict())
            for edge in graph.edges
        ]
        
        return LineageGraphResponse(
            nodes=nodes,
            edges=edges,
            root_id=graph.root_id,
            direction=graph.direction,
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build column lineage graph: {str(e)}")


@app.get("/api/lineage/node/{node_id}", response_model=NodeDetailsResponse)
async def get_node_details(node_id: str):
    """
    Get detailed information about a specific node.
    
    Includes upstream/downstream counts and provider information.
    """
    if not LINEAGE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Lineage visualization not available")
    
    try:
        from sqlalchemy import text
        
        # Parse node_id (format: "schema.table" or "schema.table.column")
        parts = node_id.split(".")
        
        if len(parts) == 2:
            # Table node
            schema, table = parts
            node_type = "table"
            
            # Count upstream/downstream tables
            upstream_query = text("""
                SELECT COUNT(DISTINCT upstream_table)
                FROM baselinr_lineage
                WHERE downstream_schema = :schema AND downstream_table = :table
            """)
            downstream_query = text("""
                SELECT COUNT(DISTINCT downstream_table)
                FROM baselinr_lineage
                WHERE upstream_schema = :schema AND upstream_table = :table
            """)
            
            # Get providers
            providers_query = text("""
                SELECT DISTINCT provider
                FROM baselinr_lineage
                WHERE (downstream_schema = :schema AND downstream_table = :table)
                   OR (upstream_schema = :schema AND upstream_table = :table)
            """)
            
            with db_client.engine.connect() as conn:
                upstream_count = conn.execute(upstream_query, {"schema": schema, "table": table}).scalar() or 0
                downstream_count = conn.execute(downstream_query, {"schema": schema, "table": table}).scalar() or 0
                providers = [row[0] for row in conn.execute(providers_query, {"schema": schema, "table": table})]
            
            return NodeDetailsResponse(
                id=node_id,
                type=node_type,
                label=table,
                schema=schema,
                table=table,
                upstream_count=upstream_count,
                downstream_count=downstream_count,
                providers=providers,
            )
        
        elif len(parts) == 3:
            # Column node
            schema, table, column = parts
            node_type = "column"
            
            # Count upstream/downstream columns
            upstream_query = text("""
                SELECT COUNT(*)
                FROM baselinr_column_lineage
                WHERE downstream_schema = :schema 
                  AND downstream_table = :table 
                  AND downstream_column = :column
            """)
            downstream_query = text("""
                SELECT COUNT(*)
                FROM baselinr_column_lineage
                WHERE upstream_schema = :schema 
                  AND upstream_table = :table 
                  AND upstream_column = :column
            """)
            
            # Get providers
            providers_query = text("""
                SELECT DISTINCT provider
                FROM baselinr_column_lineage
                WHERE (downstream_schema = :schema AND downstream_table = :table AND downstream_column = :column)
                   OR (upstream_schema = :schema AND upstream_table = :table AND upstream_column = :column)
            """)
            
            with db_client.engine.connect() as conn:
                upstream_count = conn.execute(upstream_query, {"schema": schema, "table": table, "column": column}).scalar() or 0
                downstream_count = conn.execute(downstream_query, {"schema": schema, "table": table, "column": column}).scalar() or 0
                providers = [row[0] for row in conn.execute(providers_query, {"schema": schema, "table": table, "column": column})]
            
            return NodeDetailsResponse(
                id=node_id,
                type=node_type,
                label=f"{table}.{column}",
                schema=schema,
                table=table,
                column=column,
                upstream_count=upstream_count,
                downstream_count=downstream_count,
                providers=providers,
            )
        
        else:
            raise HTTPException(status_code=400, detail="Invalid node_id format")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get node details: {str(e)}")


@app.get("/api/lineage/search", response_model=List[TableInfoResponse])
async def search_lineage(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Search for tables in lineage data and profiled tables.
    
    Returns matching tables based on name pattern. Searches both lineage data
    and profiled tables (from baselinr_runs) as a fallback.
    """
    from sqlalchemy import text
    
    logger.info(f"Search request: q='{q}', limit={limit}")
    logger.info(f"LINEAGE_AVAILABLE={LINEAGE_AVAILABLE}")
    
    try:
        search_lower = q.lower()
        matching_tables = []
        seen_keys = set()
        
        # First, try direct query to lineage table (most reliable)
        try:
            lineage_table_exists = db_client._table_exists('baselinr_lineage')
            logger.info(f"baselinr_lineage table exists: {lineage_table_exists}")
            
            if lineage_table_exists:
                with db_client.engine.connect() as conn:
                    # First, let's see what tables exist in the lineage table
                    count_query = text("SELECT COUNT(*) FROM baselinr_lineage")
                    total_count = conn.execute(count_query).scalar()
                    logger.info(f"Total rows in baselinr_lineage: {total_count}")
                    
                    # Get a sample of table names
                    sample_query = text("""
                        SELECT DISTINCT downstream_table, upstream_table
                        FROM baselinr_lineage
                        LIMIT 10
                    """)
                    sample_rows = conn.execute(sample_query).fetchall()
                    logger.info(f"Sample tables in lineage: {[row for row in sample_rows]}")
                    
                    query = text("""
                        SELECT DISTINCT downstream_schema, downstream_table
                        FROM baselinr_lineage
                        WHERE LOWER(downstream_table) LIKE :pattern 
                           OR LOWER(COALESCE(downstream_schema, '')) LIKE :pattern
                        UNION
                        SELECT DISTINCT upstream_schema, upstream_table
                        FROM baselinr_lineage
                        WHERE LOWER(upstream_table) LIKE :pattern 
                           OR LOWER(COALESCE(upstream_schema, '')) LIKE :pattern
                        ORDER BY downstream_schema, downstream_table
                        LIMIT :limit
                    """)
                    pattern = f"%{search_lower}%"
                    logger.info(f"Executing search query with pattern: {pattern}")
                    result = conn.execute(query, {"pattern": pattern, "limit": limit})
                    rows = result.fetchall()
                    logger.info(f"Query returned {len(rows)} rows")
                    
                    for row in rows:
                        schema, table = row
                        table_key = f"{schema or ''}.{table or ''}"
                        logger.debug(f"Found table: {table_key}")
                        if table_key not in seen_keys and table:
                            matching_tables.append(TableInfoResponse(
                                schema=schema or "",
                                table=table,
                                database=None
                            ))
                            seen_keys.add(table_key)
                    logger.info(f"Found {len(matching_tables)} unique tables from lineage table")
            else:
                logger.warning("baselinr_lineage table does not exist")
        except Exception as e:
            logger.error(f"Failed to query lineage table directly: {e}", exc_info=True)
        
        # Also try LineageGraphBuilder as fallback
        if len(matching_tables) < limit and LINEAGE_AVAILABLE:
            try:
                builder = LineageGraphBuilder(db_client.engine)
                all_tables = builder.get_all_tables()
                logger.debug(f"LineageGraphBuilder found {len(all_tables)} tables")
                
                for t in all_tables:
                    # get_all_tables returns {"schema": ..., "table": ...}
                    table_name = t.get("table", "")
                    schema_name = t.get("schema", "")
                    table_key = f"{schema_name}.{table_name}"
                    
                    if table_key not in seen_keys and table_name:
                        if search_lower in table_name.lower() or search_lower in (schema_name or "").lower():
                            matching_tables.append(TableInfoResponse(
                                schema=schema_name or "",
                                table=table_name,
                                database=t.get("database")
                            ))
                            seen_keys.add(table_key)
            except Exception as e:
                logger.error(f"Failed to search lineage via LineageGraphBuilder: {e}", exc_info=True)
        
        # Also search in profiled tables (baselinr_runs) as fallback
        if len(matching_tables) < limit:
            try:
                # Check if baselinr_runs table exists
                if db_client._table_exists('baselinr_runs'):
                    with db_client.engine.connect() as conn:
                        query = text("""
                            SELECT DISTINCT schema_name, dataset_name, warehouse_type
                            FROM baselinr_runs
                            WHERE LOWER(dataset_name) LIKE :pattern 
                               OR LOWER(COALESCE(schema_name, '')) LIKE :pattern
                            ORDER BY schema_name, dataset_name
                            LIMIT :limit
                        """)
                        pattern = f"%{search_lower}%"
                        result = conn.execute(query, {"pattern": pattern, "limit": limit - len(matching_tables)})
                        
                        for row in result:
                            schema, table, warehouse = row
                            table_key = f"{schema or ''}.{table or ''}"
                            if table_key not in seen_keys and table:
                                matching_tables.append(TableInfoResponse(
                                    schema=schema or "",
                                    table=table,
                                    database=None
                                ))
                                seen_keys.add(table_key)
            except Exception as e:
                # If table doesn't exist or query fails, continue
                logger.warning(f"Failed to search profiled tables: {e}")
                pass
        
        final_results = matching_tables[:limit]
        logger.info(f"Returning {len(final_results)} matching tables for search '{q}'")
        for result in final_results:
            logger.debug(f"  - {result.schema}.{result.table}")
        
        return final_results
    
    except Exception as e:
        logger.error(f"Search endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/api/lineage/tables", response_model=List[TableInfoResponse])
async def get_all_lineage_tables(
    limit: int = Query(100, ge=1, le=1000),
):
    """
    Get all tables with lineage data.
    
    Returns list of tables that have lineage relationships.
    """
    if not LINEAGE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Lineage visualization not available")
    
    # In demo mode, return tables from demo lineage data  
    if DEMO_MODE:
        try:
            nodes = db_client.lineage_raw.get('nodes', [])
            tables = []
            for node in nodes[:limit]:
                if node.get('type') == 'table':
                    tables.append(TableInfoResponse(
                        schema=node.get('schema'),
                        table=node.get('table'),
                        database=node.get('database'),
                        row_count=node.get('metadata', {}).get('row_count'),
                        column_count=node.get('metadata', {}).get('column_count'),
                        warehouse_type=node.get('metadata', {}).get('warehouse_type')
                    ))
            logger.info(f"Demo mode: returning {len(tables)} lineage tables")
            return tables
        except Exception as e:
            logger.error(f"Failed to get demo lineage tables: {e}", exc_info=True)
            return []
    
    try:
        builder = LineageGraphBuilder(db_client.engine)
        tables = builder.get_all_tables()
        
        return [TableInfoResponse(**t) for t in tables[:limit]]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tables: {str(e)}")


@app.get("/api/lineage/drift-path", response_model=DriftPathResponse)
async def get_drift_propagation(
    table: str = Query(..., description="Table name"),
    schema: Optional[str] = Query(None, description="Schema name"),
    run_id: Optional[str] = Query(None, description="Optional run ID"),
):
    """
    Get drift propagation path showing affected downstream tables.
    
    Identifies tables with drift and visualizes impact on downstream dependencies.
    """
    if not LINEAGE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Lineage visualization not available")
    
    try:
        # Build lineage graph
        builder = LineageGraphBuilder(db_client.engine)
        graph = builder.build_table_graph(
            root_table=table,
            schema=schema,
            direction="downstream",
            max_depth=5,
        )
        
        # Add drift annotations
        graph = builder.add_drift_annotations(graph, run_id=run_id)
        
        # Check if root has drift
        root_node = graph.get_node_by_id(graph.root_id or "")
        has_drift = root_node and root_node.metadata.get("has_drift", False)
        drift_severity = root_node.metadata.get("drift_severity") if root_node else None
        
        # Find affected downstream tables
        affected = []
        for node in graph.nodes:
            if node.metadata.get("has_drift") and node.id != graph.root_id:
                affected.append(TableInfoResponse(
                    schema=node.schema or "",
                    table=node.table or node.label,
                ))
        
        # Convert graph to response
        nodes = [LineageNodeResponse(**node.to_dict()) for node in graph.nodes]
        edges = [LineageEdgeResponse(**edge.to_dict()) for edge in graph.edges]
        
        return DriftPathResponse(
            table=table,
            schema=schema,
            has_drift=has_drift,
            drift_severity=drift_severity,
            affected_downstream=affected,
            lineage_path=LineageGraphResponse(
                nodes=nodes,
                edges=edges,
                root_id=graph.root_id,
                direction=graph.direction,
            ),
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get drift path: {str(e)}")


@app.get("/api/lineage/impact", response_model=LineageImpactResponse)
async def get_lineage_impact(
    table: str = Query(..., description="Table name"),
    schema: Optional[str] = Query(None, description="Schema name"),
    include_metrics: bool = Query(True, description="Include metric impact"),
):
    """
    Get impact analysis for a table.
    
    Returns:
    - Affected downstream tables
    - Impact score (0-1 scale)
    - Affected metrics count
    - Drift propagation path
    - Recommendations
    """
    if not LINEAGE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Lineage visualization not available")
    
    try:
        impact = await db_client.get_lineage_impact(
            table=table,
            schema=schema,
            include_metrics=include_metrics
        )
        return impact
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get lineage impact: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)

