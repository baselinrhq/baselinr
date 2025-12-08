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

from models import (
    RunHistoryResponse,
    ProfilingResultResponse,
    DriftAlertResponse,
    MetricsDashboardResponse,
    TableMetricsResponse
)
from lineage_models import (
    LineageGraphResponse,
    LineageNodeResponse,
    LineageEdgeResponse,
    NodeDetailsResponse,
    TableInfoResponse,
    DriftPathResponse,
)
from database import DatabaseClient
import rca_routes
import chat_routes
import config_routes
import connection_routes
import discovery_routes

# Initialize FastAPI app
app = FastAPI(
    title="Baselinr Dashboard API",
    description="Backend API for Baselinr internal dashboard",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js default port
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database client
db_client = DatabaseClient()

# Register RCA routes
rca_routes.register_routes(app, db_client.engine)

# Register config and connection routes
app.include_router(config_routes.router)
app.include_router(connection_routes.router)
app.include_router(discovery_routes.router)


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

# Register Chat routes
chat_routes.register_chat_routes(app, db_client.engine, chat_config)

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
):
    """
    Get lineage graph for a table.
    
    Returns nodes and edges representing the lineage relationships.
    """
    if not LINEAGE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Lineage visualization not available")
    
    try:
        builder = LineageGraphBuilder(db_client.engine)
        graph = builder.build_table_graph(
            root_table=table,
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
    Search for tables in lineage data.
    
    Returns matching tables based on name pattern.
    """
    if not LINEAGE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Lineage visualization not available")
    
    try:
        builder = LineageGraphBuilder(db_client.engine)
        all_tables = builder.get_all_tables()
        
        # Filter tables matching search query
        search_lower = q.lower()
        matching = [
            TableInfoResponse(**t)
            for t in all_tables
            if search_lower in t["table"].lower() or search_lower in (t["schema"] or "").lower()
        ]
        
        return matching[:limit]
    
    except Exception as e:
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


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)

