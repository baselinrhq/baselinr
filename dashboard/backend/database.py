"""
Database client for Baselinr Dashboard.

Connects to Baselinr storage database and retrieves profiling results.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from datetime import datetime
from typing import List, Optional, Dict, Any
import os
import json
import logging

from models import (
    RunHistoryResponse,
    ProfilingResultResponse,
    DriftAlertResponse,
    TableMetricsResponse,
    MetricsDashboardResponse,
    ColumnMetrics,
    KPI,
    TableMetricsTrend
)

logger = logging.getLogger(__name__)


class DatabaseClient:
    """Client for accessing Baselinr storage database."""
    
    def __init__(self):
        """Initialize database connection."""
        # Get connection string from environment or use default
        self.connection_string = os.getenv(
            "BASELINR_DB_URL",
            "postgresql://baselinr:baselinr@localhost:5433/baselinr"
        )
        self.engine: Optional[Engine] = None
        self._connect()
    
    def _connect(self):
        """Establish database connection."""
        self.engine = create_engine(self.connection_string)
    
    def _table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = :table_name
                    )
                """), {'table_name': table_name})
                return result.fetchone()[0]
        except Exception:
            return False
    
    async def get_runs(
        self,
        warehouse: Optional[str] = None,
        schema: Optional[str] = None,
        table: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[RunHistoryResponse]:
        """Get profiling run history with filters."""
        
        # Check if baselinr_events table exists
        events_table_exists = self._table_exists('baselinr_events')
        
        if events_table_exists:
            query = """
                SELECT 
                    r.run_id,
                    r.dataset_name,
                    r.schema_name,
                    'postgres' as warehouse_type,
                    r.profiled_at,
                    r.status,
                    r.row_count,
                    r.column_count,
                    CASE WHEN d.drift_count > 0 THEN true ELSE false END as has_drift
                FROM baselinr_runs r
                LEFT JOIN (
                    SELECT run_id, COUNT(*) as drift_count
                    FROM baselinr_events
                    WHERE event_type = 'DataDriftDetected'
                    GROUP BY run_id
                ) d ON r.run_id = d.run_id
                WHERE 1=1
            """
        else:
            # If events table doesn't exist, skip the join
            query = """
                SELECT 
                    r.run_id,
                    r.dataset_name,
                    r.schema_name,
                    'postgres' as warehouse_type,
                    r.profiled_at,
                    r.status,
                    r.row_count,
                    r.column_count,
                    false as has_drift
                FROM baselinr_runs r
                WHERE 1=1
            """
        
        params = {}
        
        if schema:
            query += " AND r.schema_name = :schema"
            params["schema"] = schema
        
        if table:
            query += " AND r.dataset_name = :table"
            params["table"] = table
        
        if status:
            query += " AND r.status = :status"
            params["status"] = status
        
        if start_date:
            query += " AND r.profiled_at >= :start_date"
            params["start_date"] = start_date
        
        query += " ORDER BY r.profiled_at DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset
        
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params)
            rows = result.fetchall()
            
            return [
                RunHistoryResponse(
                    run_id=row[0],
                    dataset_name=row[1],
                    schema_name=row[2],
                    warehouse_type=row[3],
                    profiled_at=row[4],
                    status=row[5] or "completed",
                    row_count=row[6],
                    column_count=row[7],
                    duration_seconds=None,  # Not stored in current schema
                    has_drift=row[8] or False
                )
                for row in rows
            ]
    
    async def get_run_details(self, run_id: str) -> Optional[ProfilingResultResponse]:
        """Get detailed profiling results for a run."""
        
        # Get run metadata
        run_query = """
            SELECT 
                run_id, dataset_name, schema_name, profiled_at,
                environment, row_count, column_count
            FROM baselinr_runs
            WHERE run_id = :run_id
        """
        
        # Get column metrics
        metrics_query = """
            SELECT 
                column_name, column_type, metric_name, metric_value
            FROM baselinr_results
            WHERE run_id = :run_id
            ORDER BY column_name
        """
        
        with self.engine.connect() as conn:
            # Fetch run metadata
            run_result = conn.execute(text(run_query), {"run_id": run_id}).fetchone()
            if not run_result:
                return None
            
            # Fetch metrics
            metrics_result = conn.execute(text(metrics_query), {"run_id": run_id}).fetchall()
            
            # Group metrics by column
            columns_dict = {}
            for row in metrics_result:
                col_name = row[0]
                if col_name not in columns_dict:
                    columns_dict[col_name] = {
                        "column_name": col_name,
                        "column_type": row[1],
                        "metrics": {}
                    }
                
                metric_name = row[2]
                metric_value = row[3]
                
                # Parse metric value
                try:
                    if metric_value:
                        # Handle histogram (JSON string) and other complex types
                        if metric_name == "histogram":
                            # Histogram is stored as JSON string (list of dicts)
                            try:
                                parsed_value = json.loads(metric_value)
                                # Ensure it's a list or dict
                                if isinstance(parsed_value, (list, dict)):
                                    columns_dict[col_name]["metrics"][metric_name] = parsed_value
                                else:
                                    columns_dict[col_name]["metrics"][metric_name] = None
                            except (json.JSONDecodeError, TypeError, ValueError):
                                # If parsing fails, set to None
                                columns_dict[col_name]["metrics"][metric_name] = None
                        else:
                            # Try to parse as float for numeric values
                            try:
                                parsed_value = float(metric_value)
                                columns_dict[col_name]["metrics"][metric_name] = parsed_value
                            except (ValueError, TypeError):
                                # Keep as string if not numeric
                                columns_dict[col_name]["metrics"][metric_name] = metric_value
                    else:
                        columns_dict[col_name]["metrics"][metric_name] = None
                except Exception:
                    columns_dict[col_name]["metrics"][metric_name] = metric_value
            
            # Build column metrics
            columns = []
            for col_data in columns_dict.values():
                metrics = col_data["metrics"]
                columns.append(ColumnMetrics(
                    column_name=col_data["column_name"],
                    column_type=col_data["column_type"],
                    null_count=metrics.get("null_count"),
                    null_percent=metrics.get("null_percent"),
                    distinct_count=metrics.get("distinct_count"),
                    distinct_percent=metrics.get("distinct_percent"),
                    min_value=metrics.get("min"),
                    max_value=metrics.get("max"),
                    mean=metrics.get("mean"),
                    stddev=metrics.get("stddev"),
                    histogram=metrics.get("histogram")
                ))
            
            return ProfilingResultResponse(
                run_id=run_result[0],
                dataset_name=run_result[1],
                schema_name=run_result[2],
                warehouse_type="postgres",
                profiled_at=run_result[3],
                environment=run_result[4] or "development",
                row_count=run_result[5] or 0,
                column_count=run_result[6] or 0,
                columns=columns
            )
    
    async def get_drift_alerts(
        self,
        warehouse: Optional[str] = None,
        table: Optional[str] = None,
        severity: Optional[str] = None,
        start_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[DriftAlertResponse]:
        """Get drift detection alerts."""
        
        # Check if events table exists
        if not self._table_exists('baselinr_events'):
            logger.warning("baselinr_events table does not exist, returning empty drift alerts")
            return []
        
        query = """
            SELECT 
                event_id, e.run_id, table_name, column_name, metric_name,
                baseline_value, current_value, change_percent, drift_severity,
                timestamp, 'postgres' as warehouse_type
            FROM baselinr_events e
            WHERE event_type = 'DataDriftDetected'
        """
        
        params = {}
        
        if table:
            query += " AND table_name = :table"
            params["table"] = table
        
        if severity:
            query += " AND drift_severity = :severity"
            params["severity"] = severity
        
        if start_date:
            query += " AND timestamp >= :start_date"
            params["start_date"] = start_date
        
        query += " ORDER BY timestamp DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset
        
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params)
            rows = result.fetchall()
            
            return [
                DriftAlertResponse(
                    event_id=row[0],
                    run_id=row[1],
                    table_name=row[2],
                    column_name=row[3],
                    metric_name=row[4],
                    baseline_value=row[5],
                    current_value=row[6],
                    change_percent=row[7],
                    severity=row[8] or "low",
                    timestamp=row[9],
                    warehouse_type=row[10]
                )
                for row in rows
            ]
    
    async def get_table_metrics(
        self,
        table_name: str,
        schema: Optional[str] = None,
        warehouse: Optional[str] = None
    ) -> Optional[TableMetricsResponse]:
        """Get detailed metrics for a specific table."""
        
        # Get latest run for this table
        latest_run_query = """
            SELECT run_id, profiled_at, row_count, column_count
            FROM baselinr_runs
            WHERE dataset_name = :table
        """
        
        if schema:
            latest_run_query += " AND schema_name = :schema"
        
        latest_run_query += " ORDER BY profiled_at DESC LIMIT 1"
        
        # Get historical trends
        trend_query = """
            SELECT profiled_at, row_count
            FROM baselinr_runs
            WHERE dataset_name = :table
            ORDER BY profiled_at DESC
            LIMIT 30
        """
        
        params = {"table": table_name}
        if schema:
            params["schema"] = schema
        
        with self.engine.connect() as conn:
            # Latest run
            latest = conn.execute(text(latest_run_query), params).fetchone()
            if not latest:
                return None
            
            # Get column metrics from latest run
            run_details = await self.get_run_details(latest[0])
            
            # Historical trends
            trends = conn.execute(text(trend_query), {"table": table_name}).fetchall()
            row_count_trend = [
                TableMetricsTrend(timestamp=row[0], value=float(row[1] or 0))
                for row in trends
            ]
            
            # Count drift events (only if events table exists)
            drift_count = 0
            if self._table_exists('baselinr_events'):
                drift_query = """
                    SELECT COUNT(*)
                    FROM baselinr_events e
                    JOIN baselinr_runs r ON e.run_id = r.run_id
                    WHERE r.dataset_name = :table
                    AND e.event_type = 'DataDriftDetected'
                """
                drift_params = {"table": table_name}
                if schema:
                    drift_query += " AND r.schema_name = :schema"
                    drift_params["schema"] = schema
                
                drift_result = conn.execute(text(drift_query), drift_params).fetchone()
                drift_count = drift_result[0] if drift_result else 0
            
            # Total runs
            total_runs = len(trends)
            
            return TableMetricsResponse(
                table_name=table_name,
                schema_name=schema,
                warehouse_type="postgres",
                last_profiled=latest[1],
                row_count=latest[2] or 0,
                column_count=latest[3] or 0,
                total_runs=total_runs,
                drift_count=drift_count,
                row_count_trend=row_count_trend,
                null_percent_trend=[],  # TODO: Calculate from metrics
                columns=run_details.columns if run_details else []
            )
    
    async def get_dashboard_metrics(
        self,
        warehouse: Optional[str] = None,
        start_date: Optional[datetime] = None
    ) -> MetricsDashboardResponse:
        """Get aggregate metrics for dashboard."""
        
        # Total counts
        stats_query = """
            SELECT 
                COUNT(DISTINCT run_id) as total_runs,
                COUNT(DISTINCT dataset_name) as total_tables,
                AVG(row_count) as avg_row_count
            FROM baselinr_runs
            WHERE 1=1
        """
        
        params = {}
        if start_date:
            stats_query += " AND profiled_at >= :start_date"
            params["start_date"] = start_date
        
        # Drift count
        drift_query = """
            SELECT COUNT(*)
            FROM baselinr_events
            WHERE event_type = 'DataDriftDetected'
        """
        
        if start_date:
            drift_query += " AND timestamp >= :start_date"
        
        with self.engine.connect() as conn:
            stats = conn.execute(text(stats_query), params).fetchone()
            
            # Handle case where baselinr_events table doesn't exist yet
            try:
                drift_result = conn.execute(text(drift_query), params).fetchone()
                drift_count = drift_result[0] if drift_result else 0
            except Exception as e:
                # Table doesn't exist or query failed - set to 0
                logger.warning(f"Could not query drift events (table may not exist): {e}")
                drift_count = 0
            
            # Get recent runs and drift
            recent_runs = await self.get_runs(limit=5)
            recent_drift = await self.get_drift_alerts(limit=5)
            
            # Build KPIs
            kpis = [
                KPI(name="Total Runs", value=stats[0] or 0, change_percent=None, trend="up"),
                KPI(name="Tables Profiled", value=stats[1] or 0, change_percent=None, trend="stable"),
                KPI(name="Drift Events", value=drift_count, change_percent=None, trend="down"),
                KPI(name="Avg Rows", value=int(stats[2] or 0), change_percent=None, trend="up")
            ]
            
            return MetricsDashboardResponse(
                total_runs=stats[0] or 0,
                total_tables=stats[1] or 0,
                total_drift_events=drift_count,
                avg_row_count=float(stats[2] or 0),
                kpis=kpis,
                run_trend=[],  # TODO: Calculate trends
                drift_trend=[],
                warehouse_breakdown={"postgres": stats[0] or 0},
                recent_runs=recent_runs,
                recent_drift=recent_drift
            )
    
    async def get_warehouses(self) -> List[str]:
        """Get list of warehouse types."""
        # For now, hardcoded. Could query from runs table
        return ["postgres", "snowflake", "mysql", "bigquery", "redshift", "sqlite"]
    
    async def export_runs(
        self,
        format: str,
        warehouse: Optional[str] = None,
        start_date: Optional[datetime] = None
    ) -> Any:
        """Export run data."""
        runs = await self.get_runs(warehouse=warehouse, start_date=start_date, limit=1000)
        
        if format == "json":
            return {"runs": [run.model_dump() for run in runs]}
        elif format == "csv":
            # TODO: Implement CSV export
            return {"error": "CSV export not yet implemented"}
    
    async def export_drift(
        self,
        format: str,
        warehouse: Optional[str] = None,
        start_date: Optional[datetime] = None
    ) -> Any:
        """Export drift data."""
        drift = await self.get_drift_alerts(warehouse=warehouse, start_date=start_date, limit=1000)
        
        if format == "json":
            return {"drift_alerts": [alert.model_dump() for run in drift]}
        elif format == "csv":
            # TODO: Implement CSV export
            return {"error": "CSV export not yet implemented"}

