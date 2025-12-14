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
    RunComparisonResponse,
    DriftAlertResponse,
    TableMetricsResponse,
    MetricsDashboardResponse,
    ColumnMetrics,
    KPI,
    TableMetricsTrend,
    TableListItem,
    TableListResponse,
    TableOverviewResponse,
    TableDriftHistoryResponse,
    TableValidationResultsResponse,
    ValidationResultResponse,
    DriftSummaryResponse,
    DriftDetailsResponse,
    DriftImpactResponse,
    TopAffectedTable,
    ValidationSummaryResponse,
    ValidationResultsListResponse,
    ValidationResultDetailsResponse,
    ValidationFailureSamplesResponse
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
                # Check database type
                dialect = self.engine.dialect.name
                if dialect == 'sqlite':
                    # SQLite uses sqlite_master
                    result = conn.execute(text("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name=:table_name
                    """), {'table_name': table_name})
                    return result.fetchone() is not None
                else:
                    # PostgreSQL and others use information_schema
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
        end_date: Optional[datetime] = None,
        min_duration: Optional[float] = None,
        max_duration: Optional[float] = None,
        sort_by: str = "profiled_at",
        sort_order: str = "desc",
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
        
        if warehouse:
            query += " AND r.warehouse_type = :warehouse"
            params["warehouse"] = warehouse
        
        if schema:
            query += " AND r.schema_name = :schema"
            params["schema"] = schema
        
        if table:
            query += " AND r.dataset_name = :table"
            params["table"] = table
        
        if status:
            # Support multiple statuses (comma-separated)
            if ',' in status:
                statuses = [s.strip() for s in status.split(',')]
                placeholders = ','.join([f':status_{i}' for i in range(len(statuses))])
                query += f" AND r.status IN ({placeholders})"
                for i, s in enumerate(statuses):
                    params[f"status_{i}"] = s
            else:
                query += " AND r.status = :status"
                params["status"] = status
        
        if start_date:
            query += " AND r.profiled_at >= :start_date"
            params["start_date"] = start_date
        
        if end_date:
            query += " AND r.profiled_at <= :end_date"
            params["end_date"] = end_date
        
        # Note: Duration filtering not yet supported as duration_seconds is not stored
        # Will be added when duration tracking is implemented
        # if min_duration is not None:
        #     query += " AND duration_seconds >= :min_duration"
        #     params["min_duration"] = min_duration
        # if max_duration is not None:
        #     query += " AND duration_seconds <= :max_duration"
        #     params["max_duration"] = max_duration
        
        # Sorting
        valid_sort_columns = {
            "profiled_at": "r.profiled_at",
            "duration_seconds": "duration_seconds",  # Not available yet
            "row_count": "r.row_count",
            "column_count": "r.column_count",
            "status": "r.status"
        }
        sort_column = valid_sort_columns.get(sort_by, "r.profiled_at")
        sort_dir = "DESC" if sort_order.lower() == "desc" else "ASC"
        
        query += f" ORDER BY {sort_column} {sort_dir} LIMIT :limit OFFSET :offset"
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
    
    async def compare_runs(self, run_ids: List[str]) -> RunComparisonResponse:
        """Compare multiple runs and calculate differences."""
        if len(run_ids) < 2:
            raise ValueError("At least 2 run IDs required for comparison")
        if len(run_ids) > 5:
            raise ValueError("Maximum 5 runs can be compared at once")
        
        # Fetch all runs
        runs = []
        run_details = []
        
        for run_id in run_ids:
            # Get run history
            run_query = """
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
                WHERE r.run_id = :run_id
                LIMIT 1
            """
            
            with self.engine.connect() as conn:
                result = conn.execute(text(run_query), {"run_id": run_id}).fetchone()
                if not result:
                    continue
                
                run = RunHistoryResponse(
                    run_id=result[0],
                    dataset_name=result[1],
                    schema_name=result[2],
                    warehouse_type=result[3],
                    profiled_at=result[4],
                    status=result[5] or "completed",
                    row_count=result[6],
                    column_count=result[7],
                    duration_seconds=None,
                    has_drift=result[8] or False
                )
                runs.append(run)
                
                # Get detailed metrics for comparison
                details = await self.get_run_details(run_id)
                if details:
                    run_details.append(details)
        
        if len(runs) < 2:
            raise ValueError("Could not find at least 2 valid runs to compare")
        
        # Build comparison data
        comparison = {
            "row_count_diff": 0,
            "column_count_diff": 0,
            "common_columns": [],
            "unique_columns": {},
            "metric_differences": []
        }
        
        # Compare row and column counts (use first run as baseline)
        if len(runs) >= 2:
            baseline = runs[0]
            for i, run in enumerate(runs[1:], 1):
                if baseline.row_count and run.row_count:
                    comparison["row_count_diff"] = run.row_count - baseline.row_count
                if baseline.column_count and run.column_count:
                    comparison["column_count_diff"] = run.column_count - baseline.column_count
        
        # Compare column metrics if we have detailed data
        if len(run_details) >= 2:
            baseline_details = run_details[0]
            baseline_columns = {col.column_name: col for col in baseline_details.columns}
            
            # Find common columns
            all_column_names = set(baseline_columns.keys())
            for details in run_details[1:]:
                all_column_names = all_column_names.intersection(
                    {col.column_name for col in details.columns}
                )
            comparison["common_columns"] = sorted(list(all_column_names))
            
            # Find unique columns per run
            for i, details in enumerate(run_details):
                run_columns = {col.column_name for col in details.columns}
                unique = run_columns - all_column_names
                if unique:
                    comparison["unique_columns"][runs[i].run_id] = sorted(list(unique))
            
            # Compare metrics for common columns
            for col_name in comparison["common_columns"]:
                baseline_col = baseline_columns.get(col_name)
                if not baseline_col:
                    continue
                
                for i, details in enumerate(run_details[1:], 1):
                    current_col = next((c for c in details.columns if c.column_name == col_name), None)
                    if not current_col:
                        continue
                    
                    # Compare numeric metrics
                    metrics_to_compare = [
                        ("null_percent", "null_percent"),
                        ("distinct_percent", "distinct_percent"),
                        ("mean", "mean"),
                        ("stddev", "stddev"),
                    ]
                    
                    for metric_key, metric_name in metrics_to_compare:
                        baseline_val = getattr(baseline_col, metric_key, None)
                        current_val = getattr(current_col, metric_key, None)
                        
                        if baseline_val is not None and current_val is not None:
                            try:
                                baseline_float = float(baseline_val)
                                current_float = float(current_val)
                                
                                if baseline_float != 0:
                                    change_percent = ((current_float - baseline_float) / abs(baseline_float)) * 100
                                else:
                                    change_percent = 100 if current_float != 0 else 0
                                
                                comparison["metric_differences"].append({
                                    "column": col_name,
                                    "metric": metric_name,
                                    "run_id": runs[i].run_id,
                                    "baseline_value": baseline_float,
                                    "current_value": current_float,
                                    "change_percent": round(change_percent, 2)
                                })
                            except (ValueError, TypeError):
                                pass
        
        return RunComparisonResponse(
            runs=runs,
            comparison=comparison
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
        
        # Drift count - use autocommit to avoid transaction issues
        drift_query = """
            SELECT COUNT(*)
            FROM baselinr_events
            WHERE event_type IN ('DataDriftDetected', 'drift_detected')
        """
        
        if start_date:
            drift_query += " AND timestamp >= :start_date"
        
        with self.engine.connect() as conn:
            stats = conn.execute(text(stats_query), params).fetchone()
            conn.commit()  # Commit the stats query
            
            # Handle case where baselinr_events table doesn't exist yet
            # Use separate connection to avoid transaction issues
            drift_count = 0
            try:
                with self.engine.connect() as drift_conn:
                    drift_result = drift_conn.execute(text(drift_query), params).fetchone()
                    drift_count = drift_result[0] if drift_result else 0
            except Exception as e:
                # Table doesn't exist or query failed - set to 0
                logger.warning(f"Could not query drift events (table may not exist): {e}")
                drift_count = 0
            
            # Validation metrics
            validation_pass_rate = None
            total_validation_rules = 0
            failed_validation_rules = 0
            
            try:
                validation_query = """
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN passed = true THEN 1 ELSE 0 END) as passed,
                        SUM(CASE WHEN passed = false THEN 1 ELSE 0 END) as failed
                    FROM baselinr_validation_results
                    WHERE 1=1
                """
                validation_params = {}
                if start_date:
                    validation_query += " AND validated_at >= :start_date"
                    validation_params["start_date"] = start_date
                
                validation_result = conn.execute(text(validation_query), validation_params).fetchone()
                if validation_result and validation_result[0] and validation_result[0] > 0:
                    total_validation_rules = validation_result[0] or 0
                    passed_count = validation_result[1] or 0
                    failed_validation_rules = validation_result[2] or 0
                    if total_validation_rules > 0:
                        validation_pass_rate = (passed_count / total_validation_rules) * 100.0
            except Exception as e:
                logger.warning(f"Could not query validation results (table may not exist): {e}")
            
            # Data freshness calculation
            data_freshness_hours = None
            stale_tables_count = 0
            
            try:
                freshness_query = """
                    SELECT MAX(profiled_at) as last_run
                    FROM baselinr_runs
                """
                freshness_result = conn.execute(text(freshness_query)).fetchone()
                if freshness_result and freshness_result[0]:
                    last_run = freshness_result[0]
                    if isinstance(last_run, str):
                        from dateutil.parser import parse
                        last_run = parse(last_run)
                    elif not isinstance(last_run, datetime):
                        # Handle different datetime types
                        last_run = datetime.fromisoformat(str(last_run))
                    
                    now = datetime.now()
                    if last_run.tzinfo:
                        # Handle timezone-aware datetime
                        if now.tzinfo is None:
                            from datetime import timezone
                            now = now.replace(tzinfo=timezone.utc)
                    else:
                        # Handle timezone-naive datetime
                        if now.tzinfo:
                            now = now.replace(tzinfo=None)
                    
                    time_diff = now - last_run
                    data_freshness_hours = time_diff.total_seconds() / 3600.0
                
                # Count stale tables (not profiled in last 24 hours)
                stale_query = """
                    SELECT COUNT(DISTINCT dataset_name)
                    FROM baselinr_runs r1
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM baselinr_runs r2
                        WHERE r2.dataset_name = r1.dataset_name
                        AND r2.profiled_at >= NOW() - INTERVAL '24 hours'
                    )
                """
                # Try PostgreSQL syntax first, fallback to generic
                try:
                    stale_result = conn.execute(text(stale_query)).fetchone()
                    stale_tables_count = stale_result[0] if stale_result else 0
                except Exception:
                    # Fallback for databases without INTERVAL support
                    from datetime import timedelta
                    stale_threshold = datetime.now() - timedelta(hours=24)
                    stale_query_generic = """
                        SELECT COUNT(DISTINCT dataset_name)
                        FROM baselinr_runs
                        WHERE dataset_name NOT IN (
                            SELECT DISTINCT dataset_name
                            FROM baselinr_runs
                            WHERE profiled_at >= :threshold
                        )
                    """
                    stale_result = conn.execute(
                        text(stale_query_generic), 
                        {"threshold": stale_threshold}
                    ).fetchone()
                    stale_tables_count = stale_result[0] if stale_result else 0
            except Exception as e:
                logger.warning(f"Could not calculate data freshness: {e}")
            
            # Active alerts: high severity drift + failed validations
            active_alerts = failed_validation_rules
            try:
                # Use drift_severity column (not severity) and handle both event types
                high_severity_drift_query = """
                    SELECT COUNT(*)
                    FROM baselinr_events
                    WHERE event_type IN ('DataDriftDetected', 'drift_detected')
                    AND drift_severity = 'high'
                """
                high_severity_params = {}
                if start_date:
                    high_severity_drift_query += " AND timestamp >= :start_date"
                    high_severity_params["start_date"] = start_date
                
                high_drift_result = conn.execute(
                    text(high_severity_drift_query), 
                    high_severity_params
                ).fetchone()
                if high_drift_result:
                    active_alerts += high_drift_result[0] or 0
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not query high severity drift: {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass
            
            # Validation trend (pass rate over time)
            validation_trend = []
            try:
                # Use separate connection to avoid transaction issues
                with self.engine.connect() as trend_conn:
                    # Try DATE() function first (PostgreSQL, MySQL), fallback to CAST
                    trend_query = """
                        SELECT 
                            DATE(validated_at) as date,
                            COUNT(*) as total,
                            SUM(CASE WHEN passed = true THEN 1 ELSE 0 END) as passed
                        FROM baselinr_validation_results
                        WHERE validated_at >= :start_date
                        GROUP BY DATE(validated_at)
                        ORDER BY date ASC
                    """
                    trend_params = {"start_date": start_date if start_date else datetime.now().replace(day=1)}
                    trend_results = trend_conn.execute(text(trend_query), trend_params).fetchall()
                    for row in trend_results:
                        date_val = row[0]
                        total = row[1] or 0
                        passed = row[2] or 0
                        if total > 0:
                            pass_rate = (passed / total) * 100.0
                            # Ensure date_val is a datetime
                            if isinstance(date_val, str):
                                try:
                                    from dateutil.parser import parse
                                    date_val = parse(date_val)
                                except Exception:
                                    date_val = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                            elif not isinstance(date_val, datetime):
                                # Handle date objects
                                if hasattr(date_val, 'isoformat'):
                                    date_val = datetime.combine(date_val, datetime.min.time())
                                else:
                                    date_val = datetime.fromisoformat(str(date_val))
                            validation_trend.append(
                                TableMetricsTrend(timestamp=date_val, value=pass_rate)
                            )
            except Exception as e:
                logger.warning(f"Could not calculate validation trend: {e}")
            
            # Calculate run trend (runs per day)
            run_trend = []
            try:
                # Use separate connection to avoid transaction issues
                with self.engine.connect() as trend_conn:
                    run_trend_query = """
                        SELECT 
                            DATE(profiled_at) as date,
                            COUNT(*) as run_count
                        FROM baselinr_runs
                        WHERE 1=1
                    """
                    run_trend_params = {}
                    if start_date:
                        run_trend_query += " AND profiled_at >= :start_date"
                        run_trend_params["start_date"] = start_date
                    run_trend_query += " GROUP BY DATE(profiled_at) ORDER BY date ASC"
                    
                    run_trend_results = trend_conn.execute(text(run_trend_query), run_trend_params).fetchall()
                    for row in run_trend_results:
                        date_val = row[0]
                        count = row[1] or 0
                        # Ensure date_val is a datetime
                        if isinstance(date_val, str):
                            try:
                                from dateutil.parser import parse
                                date_val = parse(date_val)
                            except Exception:
                                date_val = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                        elif not isinstance(date_val, datetime):
                            if hasattr(date_val, 'isoformat'):
                                date_val = datetime.combine(date_val, datetime.min.time())
                            else:
                                date_val = datetime.fromisoformat(str(date_val))
                        run_trend.append(
                            TableMetricsTrend(timestamp=date_val, value=float(count))
                        )
            except Exception as e:
                logger.warning(f"Could not calculate run trend: {e}")
            
            # Calculate drift trend (drift events per day)
            drift_trend = []
            try:
                # Use separate connection/transaction to avoid cascading failures
                with self.engine.connect() as trend_conn:
                    drift_trend_query = """
                        SELECT 
                            DATE(timestamp) as date,
                            COUNT(*) as drift_count
                        FROM baselinr_events
                        WHERE event_type IN ('DataDriftDetected', 'drift_detected')
                    """
                    drift_trend_params = {}
                    if start_date:
                        drift_trend_query += " AND timestamp >= :start_date"
                        drift_trend_params["start_date"] = start_date
                    drift_trend_query += " GROUP BY DATE(timestamp) ORDER BY date ASC"
                    
                    drift_trend_results = trend_conn.execute(text(drift_trend_query), drift_trend_params).fetchall()
                    for row in drift_trend_results:
                        date_val = row[0]
                        count = row[1] or 0
                        # Ensure date_val is a datetime
                        if isinstance(date_val, str):
                            try:
                                from dateutil.parser import parse
                                date_val = parse(date_val)
                            except Exception:
                                date_val = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                        elif not isinstance(date_val, datetime):
                            if hasattr(date_val, 'isoformat'):
                                date_val = datetime.combine(date_val, datetime.min.time())
                            else:
                                date_val = datetime.fromisoformat(str(date_val))
                        drift_trend.append(
                            TableMetricsTrend(timestamp=date_val, value=float(count))
                        )
            except Exception as e:
                logger.warning(f"Could not calculate drift trend: {e}")
            
            # Calculate warehouse breakdown
            # Note: warehouse_type may not exist in baselinr_runs table
            # For now, use a simple count - can be enhanced when warehouse_type is available
            warehouse_breakdown = {}
            try:
                # Try to get warehouse_type if column exists, otherwise default to postgres
                try:
                    warehouse_query = """
                        SELECT warehouse_type, COUNT(*) as count
                        FROM baselinr_runs
                        WHERE 1=1
                    """
                    warehouse_params = {}
                    if start_date:
                        warehouse_query += " AND profiled_at >= :start_date"
                        warehouse_params["start_date"] = start_date
                    warehouse_query += " GROUP BY warehouse_type"
                    
                    warehouse_results = conn.execute(text(warehouse_query), warehouse_params).fetchall()
                    for row in warehouse_results:
                        warehouse_breakdown[row[0] or 'unknown'] = row[1] or 0
                except Exception:
                    # Column doesn't exist, use default
                    warehouse_breakdown = {"postgres": stats[0] or 0}
            except Exception as e:
                logger.warning(f"Could not calculate warehouse breakdown: {e}")
                warehouse_breakdown = {"postgres": stats[0] or 0}
            
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
            
            # Get quality scores (system-level)
            system_quality_score = None
            quality_score_status = None
            quality_trend = None
            try:
                # Import here to avoid circular dependencies
                import sys
                import os
                sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
                from baselinr.quality.storage import QualityScoreStorage
                from baselinr.quality.scorer import QualityScorer
                
                storage = QualityScoreStorage(self.engine)
                system_scores = storage.query_system_scores()
                
                if system_scores:
                    # Calculate average score
                    total_score = sum(s.overall_score for s in system_scores)
                    avg_score = total_score / len(system_scores) if system_scores else 0.0
                    system_quality_score = round(avg_score, 2)
                    
                    # Determine overall status (worst status wins)
                    critical_count = sum(1 for s in system_scores if s.status == "critical")
                    warning_count = sum(1 for s in system_scores if s.status == "warning")
                    
                    if critical_count > 0:
                        quality_score_status = "critical"
                    elif warning_count > 0:
                        quality_score_status = "warning"
                    else:
                        quality_score_status = "healthy"
                    
                    # Calculate trend by comparing with previous system score
                    # Get historical scores for trend calculation
                    # We'll use a simple approach: compare current avg with previous period
                    # For now, set trend to None (can be enhanced later with proper historical comparison)
                    quality_trend = None
            except Exception as e:
                # Quality scoring may not be enabled or table may not exist
                logger.debug(f"Could not get quality scores (may not be enabled): {e}")
            
            return MetricsDashboardResponse(
                total_runs=stats[0] or 0,
                total_tables=stats[1] or 0,
                total_drift_events=drift_count,
                avg_row_count=float(stats[2] or 0),
                kpis=kpis,
                run_trend=run_trend,
                drift_trend=drift_trend,
                warehouse_breakdown=warehouse_breakdown,
                recent_runs=recent_runs,
                recent_drift=recent_drift,
                validation_pass_rate=validation_pass_rate,
                total_validation_rules=total_validation_rules,
                failed_validation_rules=failed_validation_rules,
                active_alerts=active_alerts,
                data_freshness_hours=data_freshness_hours,
                stale_tables_count=stale_tables_count,
                validation_trend=validation_trend,
                system_quality_score=system_quality_score,
                quality_score_status=quality_score_status,
                quality_trend=quality_trend
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
    
    async def get_tables(
        self,
        warehouse: Optional[str] = None,
        schema: Optional[str] = None,
        search: Optional[str] = None,
        has_drift: Optional[bool] = None,
        has_failed_validations: Optional[bool] = None,
        sort_by: str = "table_name",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 50
    ) -> TableListResponse:
        """Get list of tables with filters, sorting, and pagination."""
        
        offset = (page - 1) * page_size
        
        # Build base query to get distinct tables with latest run info
        base_query = """
            SELECT DISTINCT
                r.dataset_name as table_name,
                r.schema_name,
                'postgres' as warehouse_type,
                MAX(r.profiled_at) as last_profiled,
                (SELECT row_count FROM baselinr_runs 
                 WHERE dataset_name = r.dataset_name 
                 AND (r.schema_name IS NULL OR schema_name = r.schema_name)
                 ORDER BY profiled_at DESC LIMIT 1) as row_count,
                (SELECT column_count FROM baselinr_runs 
                 WHERE dataset_name = r.dataset_name 
                 AND (r.schema_name IS NULL OR schema_name = r.schema_name)
                 ORDER BY profiled_at DESC LIMIT 1) as column_count,
                COUNT(DISTINCT r.run_id) as total_runs
            FROM baselinr_runs r
            WHERE 1=1
        """
        
        params: Dict[str, Any] = {}
        
        # Apply filters
        if warehouse:
            base_query += " AND r.warehouse_type = :warehouse"
            params["warehouse"] = warehouse
        
        if schema:
            base_query += " AND r.schema_name = :schema"
            params["schema"] = schema
        
        if search:
            base_query += " AND (r.dataset_name ILIKE :search OR r.schema_name ILIKE :search)"
            params["search"] = f"%{search}%"
        
        # Group by for aggregation
        base_query += " GROUP BY r.dataset_name, r.schema_name"
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM ({base_query}) as subquery"
        
        # Note: drift_count and validation stats are calculated separately, so we'll sort in Python
        # For now, sort by available columns in SQL, then apply Python sorting if needed
        valid_sort_columns = {
            "table_name": "table_name",
            "last_profiled": "last_profiled",
            "row_count": "row_count"
        }
        sort_column = valid_sort_columns.get(sort_by, "table_name")
        sort_dir = "DESC" if sort_order.lower() == "desc" else "ASC"
        
        # Final query with sorting and pagination (without drift_count for now)
        final_query = f"""
            SELECT * FROM ({base_query}) as t
            ORDER BY {sort_column} {sort_dir}
        """
        # Don't apply limit/offset yet - we need to filter first
        
        with self.engine.connect() as conn:
            # Get all matching tables first (we'll filter and paginate in Python)
            table_rows = conn.execute(text(final_query), params).fetchall()
            
            tables = []
            for row in table_rows:
                table_name = row[0]
                schema_name = row[1]
                warehouse_type = row[2] or "postgres"
                last_profiled = row[3]
                row_count = row[4]
                column_count = row[5]
                total_runs = row[6] or 0
                
                # Get drift count
                drift_count = 0
                has_recent_drift = False
                try:
                    with self.engine.connect() as drift_conn:
                        drift_query = """
                            SELECT COUNT(*), MAX(timestamp)
                            FROM baselinr_events e
                            JOIN baselinr_runs r ON e.run_id = r.run_id
                            WHERE r.dataset_name = :table_name
                            AND e.event_type IN ('DataDriftDetected', 'drift_detected')
                        """
                        drift_params = {"table_name": table_name}
                        if schema_name:
                            drift_query += " AND r.schema_name = :schema_name"
                            drift_params["schema_name"] = schema_name
                        
                        drift_result = drift_conn.execute(text(drift_query), drift_params).fetchone()
                        if drift_result:
                            drift_count = drift_result[0] or 0
                            # Check if there's drift in last 7 days
                            if drift_result[1]:
                                from datetime import timedelta
                                recent_threshold = datetime.now() - timedelta(days=7)
                                if isinstance(drift_result[1], datetime):
                                    has_recent_drift = drift_result[1] >= recent_threshold
                                elif isinstance(drift_result[1], str):
                                    drift_date = datetime.fromisoformat(drift_result[1].replace('Z', '+00:00'))
                                    has_recent_drift = drift_date >= recent_threshold
                except Exception as e:
                    logger.warning(f"Could not get drift count for {table_name}: {e}")
                
                # Get validation stats
                validation_pass_rate = None
                table_has_failed_validations = False
                try:
                    with self.engine.connect() as validation_conn:
                        validation_query = """
                            SELECT 
                                COUNT(*) as total,
                                SUM(CASE WHEN passed = true THEN 1 ELSE 0 END) as passed
                            FROM baselinr_validation_results
                            WHERE table_name = :table_name
                        """
                        validation_params = {"table_name": table_name}
                        if schema_name:
                            validation_query += " AND schema_name = :schema_name"
                            validation_params["schema_name"] = schema_name
                        
                        validation_result = validation_conn.execute(text(validation_query), validation_params).fetchone()
                        if validation_result and validation_result[0] and validation_result[0] > 0:
                            total_validations = validation_result[0]
                            passed = validation_result[1] or 0
                            if total_validations > 0:
                                validation_pass_rate = (passed / total_validations) * 100.0
                                table_has_failed_validations = passed < total_validations
                except Exception as e:
                    logger.warning(f"Could not get validation stats for {table_name}: {e}")
                
                # Apply additional filters
                if has_drift is not None and has_drift != (drift_count > 0):
                    continue
                if has_failed_validations is not None and has_failed_validations != table_has_failed_validations:
                    continue
                
                tables.append(TableListItem(
                    table_name=table_name,
                    schema_name=schema_name,
                    warehouse_type=warehouse_type,
                    last_profiled=last_profiled,
                    row_count=row_count,
                    column_count=column_count,
                    total_runs=total_runs,
                    drift_count=drift_count,
                    validation_pass_rate=validation_pass_rate,
                    has_recent_drift=has_recent_drift,
                    has_failed_validations=table_has_failed_validations
                ))
            
            # Apply Python-based sorting for drift_count if needed
            if sort_by == "drift_count":
                tables.sort(key=lambda t: t.drift_count, reverse=(sort_order.lower() == "desc"))
            
            # Get total count after filtering
            total = len(tables)
            
            # Apply pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_tables = tables[start_idx:end_idx]
            
            return TableListResponse(
                tables=paginated_tables,
                total=total,
                page=page,
                page_size=page_size
            )
    
    async def get_table_overview(
        self,
        table_name: str,
        schema: Optional[str] = None,
        warehouse: Optional[str] = None
    ) -> Optional[TableOverviewResponse]:
        """Get enhanced table overview."""
        # Get base metrics
        base_metrics = await self.get_table_metrics(table_name, schema, warehouse)
        if not base_metrics:
            return None
        
        # Get recent runs
        recent_runs = await self.get_runs(
            table=table_name,
            schema=schema,
            warehouse=warehouse,
            limit=10
        )
        
        # Get validation stats
        validation_pass_rate = None
        total_validation_rules = 0
        failed_validation_rules = 0
        try:
            with self.engine.connect() as conn:
                validation_query = """
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN passed = true THEN 1 ELSE 0 END) as passed,
                        SUM(CASE WHEN passed = false THEN 1 ELSE 0 END) as failed
                    FROM baselinr_validation_results
                    WHERE table_name = :table_name
                """
                validation_params = {"table_name": table_name}
                if schema:
                    validation_query += " AND schema_name = :schema_name"
                    validation_params["schema_name"] = schema
                
                validation_result = conn.execute(text(validation_query), validation_params).fetchone()
                if validation_result and validation_result[0] and validation_result[0] > 0:
                    total_validation_rules = validation_result[0] or 0
                    passed_count = validation_result[1] or 0
                    failed_validation_rules = validation_result[2] or 0
                    if total_validation_rules > 0:
                        validation_pass_rate = (passed_count / total_validation_rules) * 100.0
        except Exception as e:
            logger.warning(f"Could not get validation stats: {e}")
        
        return TableOverviewResponse(
            table_name=base_metrics.table_name,
            schema_name=base_metrics.schema_name,
            warehouse_type=base_metrics.warehouse_type,
            last_profiled=base_metrics.last_profiled,
            row_count=base_metrics.row_count,
            column_count=base_metrics.column_count,
            total_runs=base_metrics.total_runs,
            drift_count=base_metrics.drift_count,
            validation_pass_rate=validation_pass_rate,
            total_validation_rules=total_validation_rules,
            failed_validation_rules=failed_validation_rules,
            row_count_trend=base_metrics.row_count_trend,
            null_percent_trend=base_metrics.null_percent_trend,
            columns=base_metrics.columns,
            recent_runs=recent_runs
        )
    
    async def get_table_drift_history(
        self,
        table_name: str,
        schema: Optional[str] = None,
        warehouse: Optional[str] = None,
        limit: int = 100
    ) -> TableDriftHistoryResponse:
        """Get drift history for a specific table."""
        # Get drift alerts for this table
        drift_alerts = await self.get_drift_alerts(
            table=table_name,
            warehouse=warehouse,
            limit=limit
        )
        
        # Calculate summary
        summary: Dict[str, Any] = {
            "total_events": len(drift_alerts),
            "by_severity": {},
            "by_column": {},
            "recent_count": 0
        }
        
        from datetime import timedelta
        recent_threshold = datetime.now() - timedelta(days=7)
        
        for alert in drift_alerts:
            # Count by severity
            severity = alert.severity if alert.severity else 'unknown'
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
            
            # Count by column
            if alert.column_name:
                summary["by_column"][alert.column_name] = summary["by_column"].get(alert.column_name, 0) + 1
            
            # Count recent
            if alert.timestamp >= recent_threshold:
                summary["recent_count"] += 1
        
        return TableDriftHistoryResponse(
            table_name=table_name,
            schema_name=schema,
            drift_events=drift_alerts,
            summary=summary
        )
    
    async def get_table_validation_results(
        self,
        table_name: str,
        schema: Optional[str] = None,
        limit: int = 100
    ) -> TableValidationResultsResponse:
        """Get validation results for a specific table."""
        validation_results = []
        summary: Dict[str, Any] = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "pass_rate": 0.0,
            "by_rule_type": {},
            "by_severity": {}
        }
        
        try:
            with self.engine.connect() as conn:
                query = """
                    SELECT 
                        id, run_id, table_name, schema_name, column_name, rule_type, passed,
                        failure_reason, total_rows, failed_rows, failure_rate,
                        severity, validated_at
                    FROM baselinr_validation_results
                    WHERE table_name = :table_name
                """
                params = {"table_name": table_name}
                if schema:
                    query += " AND schema_name = :schema_name"
                    params["schema_name"] = schema
                
                query += " ORDER BY validated_at DESC LIMIT :limit"
                params["limit"] = limit
                
                results = conn.execute(text(query), params).fetchall()
                
                for row in results:
                    validation_results.append(ValidationResultResponse(
                        id=row[0],
                        run_id=row[1],
                        table_name=row[2],
                        schema_name=row[3],
                        column_name=row[4],
                        rule_type=row[5],
                        passed=row[6],
                        failure_reason=row[7],
                        total_rows=row[8],
                        failed_rows=row[9],
                        failure_rate=float(row[10]) if row[10] else None,
                        severity=row[11],
                        validated_at=row[12]
                    ))
                    
                    # Update summary
                    summary["total"] += 1
                    if row[6]:  # passed
                        summary["passed"] += 1
                    else:
                        summary["failed"] += 1
                    
                    # Count by rule type
                    rule_type = row[5] or "unknown"
                    summary["by_rule_type"][rule_type] = summary["by_rule_type"].get(rule_type, 0) + 1
                    
                    # Count by severity
                    if row[11]:
                        severity = row[11]
                        summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
                
                # Calculate pass rate
                if summary["total"] > 0:
                    summary["pass_rate"] = (summary["passed"] / summary["total"]) * 100.0
        except Exception as e:
            logger.warning(f"Could not get validation results: {e}")
        
        return TableValidationResultsResponse(
            table_name=table_name,
            schema_name=schema,
            validation_results=validation_results,
            summary=summary
        )
    
    async def get_validation_summary(
        self,
        warehouse: Optional[str] = None,
        days: int = 30
    ) -> "ValidationSummaryResponse":
        """Get validation summary statistics."""
        from datetime import timedelta, timezone
        from models import ValidationSummaryResponse, TableMetricsTrend
        
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        total_validations = 0
        passed_count = 0
        failed_count = 0
        by_rule_type: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        by_table: Dict[str, int] = {}
        trending: List[TableMetricsTrend] = []
        recent_runs: List[Dict[str, Any]] = []
        
        if not self._table_exists('baselinr_validation_results'):
            logger.warning("baselinr_validation_results table does not exist, returning empty validation summary")
            return ValidationSummaryResponse(
                total_validations=0,
                passed_count=0,
                failed_count=0,
                pass_rate=0.0,
                by_rule_type=by_rule_type,
                by_severity=by_severity,
                by_table=by_table,
                trending=trending,
                recent_runs=recent_runs
            )
        
        try:
            with self.engine.connect() as conn:
                # Base WHERE clause
                where_clause = "WHERE validated_at >= :start_date"
                params = {"start_date": start_date}
                
                if warehouse:
                    where_clause += " AND EXISTS (SELECT 1 FROM baselinr_runs r WHERE r.run_id = baselinr_validation_results.run_id AND r.warehouse_type = :warehouse)"
                    params["warehouse"] = warehouse
                
                # Get totals
                count_query = f"""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE passed = true) as passed,
                        COUNT(*) FILTER (WHERE passed = false) as failed
                    FROM baselinr_validation_results
                    {where_clause}
                """
                count_result = conn.execute(text(count_query), params).fetchone()
                if count_result:
                    total_validations = count_result[0] or 0
                    passed_count = count_result[1] or 0
                    failed_count = count_result[2] or 0
                
                # Get breakdown by rule type
                rule_type_query = f"""
                    SELECT 
                        rule_type,
                        COUNT(*) as count
                    FROM baselinr_validation_results
                    {where_clause}
                    GROUP BY rule_type
                """
                rule_type_results = conn.execute(text(rule_type_query), params).fetchall()
                for row in rule_type_results:
                    rule_type = row[0] or "unknown"
                    count = row[1] or 0
                    by_rule_type[rule_type] = count
                
                # Get breakdown by severity
                severity_query = f"""
                    SELECT 
                        severity,
                        COUNT(*) as count
                    FROM baselinr_validation_results
                    {where_clause}
                    GROUP BY severity
                """
                severity_results = conn.execute(text(severity_query), params).fetchall()
                for row in severity_results:
                    severity = row[0] or "unknown"
                    count = row[1] or 0
                    by_severity[severity] = count
                
                # Get breakdown by table
                table_query = f"""
                    SELECT 
                        table_name,
                        COUNT(*) as count
                    FROM baselinr_validation_results
                    {where_clause}
                    GROUP BY table_name
                """
                table_results = conn.execute(text(table_query), params).fetchall()
                for row in table_results:
                    table_name = row[0] or "unknown"
                    count = row[1] or 0
                    by_table[table_name] = count
                
                # Get trending data (pass rate per day)
                trend_query = f"""
                    SELECT 
                        DATE(validated_at) as date,
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE passed = true) as passed
                    FROM baselinr_validation_results
                    {where_clause}
                    GROUP BY DATE(validated_at) ORDER BY date ASC
                """
                
                trend_results = conn.execute(text(trend_query), params).fetchall()
                for row in trend_results:
                    date_val = row[0]
                    total = row[1] or 0
                    passed = row[2] or 0
                    pass_rate = (passed / total * 100.0) if total > 0 else 0.0
                    
                    if isinstance(date_val, str):
                        try:
                            from dateutil.parser import parse
                            date_val = parse(date_val)
                        except Exception:
                            date_val = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                    elif not isinstance(date_val, datetime):
                        if hasattr(date_val, 'isoformat'):
                            date_val = datetime.combine(date_val, datetime.min.time())
                        else:
                            date_val = datetime.fromisoformat(str(date_val))
                    
                    trending.append(TableMetricsTrend(timestamp=date_val, value=pass_rate))
                
                # Get recent validation runs (grouped by run_id)
                recent_query = f"""
                    SELECT 
                        run_id,
                        MAX(validated_at) as validated_at,
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE passed = true) as passed,
                        COUNT(*) FILTER (WHERE passed = false) as failed
                    FROM baselinr_validation_results
                    {where_clause}
                    GROUP BY run_id ORDER BY validated_at DESC LIMIT 10
                """
                
                recent_results = conn.execute(text(recent_query), params).fetchall()
                for row in recent_results:
                    recent_runs.append({
                        "run_id": row[0],
                        "validated_at": row[1].isoformat() if isinstance(row[1], datetime) else str(row[1]),
                        "total": row[2] or 0,
                        "passed": row[3] or 0,
                        "failed": row[4] or 0
                    })
                
        except Exception as e:
            logger.warning(f"Could not get validation summary: {e}")
        
        pass_rate = (passed_count / total_validations * 100.0) if total_validations > 0 else 0.0
        
        return ValidationSummaryResponse(
            total_validations=total_validations,
            passed_count=passed_count,
            failed_count=failed_count,
            pass_rate=pass_rate,
            by_rule_type=by_rule_type,
            by_severity=by_severity,
            by_table=by_table,
            trending=trending,
            recent_runs=recent_runs
        )
    
    async def get_validation_results(
        self,
        table: Optional[str] = None,
        schema: Optional[str] = None,
        rule_type: Optional[str] = None,
        severity: Optional[str] = None,
        passed: Optional[bool] = None,
        days: int = 30,
        page: int = 1,
        page_size: int = 50
    ) -> "ValidationResultsListResponse":
        """Get validation results with filtering and pagination."""
        from datetime import timedelta, timezone
        from models import ValidationResultsListResponse, ValidationResultResponse
        
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        offset = (page - 1) * page_size
        
        results: List[ValidationResultResponse] = []
        total = 0
        
        if not self._table_exists('baselinr_validation_results'):
            logger.warning("baselinr_validation_results table does not exist, returning empty results")
            return ValidationResultsListResponse(
                results=results,
                total=0,
                page=page,
                page_size=page_size
            )
        
        try:
            with self.engine.connect() as conn:
                # Build query with filters
                query = """
                    SELECT 
                        id, run_id, table_name, schema_name, column_name, rule_type, passed,
                        failure_reason, total_rows, failed_rows, failure_rate, severity, validated_at
                    FROM baselinr_validation_results
                    WHERE validated_at >= :start_date
                """
                params = {"start_date": start_date, "limit": page_size, "offset": offset}
                
                if table:
                    query += " AND table_name = :table_name"
                    params["table_name"] = table
                
                if schema:
                    query += " AND schema_name = :schema_name"
                    params["schema_name"] = schema
                
                if rule_type:
                    query += " AND rule_type = :rule_type"
                    params["rule_type"] = rule_type
                
                if severity:
                    query += " AND severity = :severity"
                    params["severity"] = severity
                
                if passed is not None:
                    query += " AND passed = :passed"
                    params["passed"] = passed
                
                # Get total count
                count_query = query.replace("SELECT id, run_id, table_name, schema_name, column_name, rule_type, passed, failure_reason, total_rows, failed_rows, failure_rate, severity, validated_at", "SELECT COUNT(*)")
                count_result = conn.execute(text(count_query), params).fetchone()
                total = count_result[0] if count_result else 0
                
                # Get paginated results
                query += " ORDER BY validated_at DESC LIMIT :limit OFFSET :offset"
                
                result_rows = conn.execute(text(query), params).fetchall()
                
                for row in result_rows:
                    results.append(ValidationResultResponse(
                        id=row[0],
                        run_id=row[1],
                        table_name=row[2],
                        schema_name=row[3],
                        column_name=row[4],
                        rule_type=row[5],
                        passed=row[6],
                        failure_reason=row[7],
                        total_rows=row[8],
                        failed_rows=row[9],
                        failure_rate=float(row[10]) if row[10] else None,
                        severity=row[11],
                        validated_at=row[12]
                    ))
                
        except Exception as e:
            logger.warning(f"Could not get validation results: {e}")
        
        return ValidationResultsListResponse(
            results=results,
            total=total,
            page=page,
            page_size=page_size
        )
    
    async def get_validation_result_details(
        self,
        result_id: int
    ) -> "ValidationResultDetailsResponse":
        """Get detailed validation result with context."""
        from models import ValidationResultDetailsResponse, ValidationResultResponse
        
        result: Optional[ValidationResultResponse] = None
        rule_config: Optional[Dict[str, Any]] = None
        run_info: Optional[Dict[str, Any]] = None
        historical_results: List[ValidationResultResponse] = []
        
        if not self._table_exists('baselinr_validation_results'):
            raise ValueError(f"Validation result {result_id} not found")
        
        try:
            with self.engine.connect() as conn:
                # Get the result
                result_query = """
                    SELECT 
                        id, run_id, table_name, schema_name, column_name, rule_type, passed,
                        failure_reason, total_rows, failed_rows, failure_rate, severity, validated_at
                    FROM baselinr_validation_results
                    WHERE id = :result_id
                """
                result_row = conn.execute(text(result_query), {"result_id": result_id}).fetchone()
                
                if not result_row:
                    raise ValueError(f"Validation result {result_id} not found")
                
                result = ValidationResultResponse(
                    id=result_row[0],
                    run_id=result_row[1],
                    table_name=result_row[2],
                    schema_name=result_row[3],
                    column_name=result_row[4],
                    rule_type=result_row[5],
                    passed=result_row[6],
                    failure_reason=result_row[7],
                    total_rows=result_row[8],
                    failed_rows=result_row[9],
                    failure_rate=float(result_row[10]) if result_row[10] else None,
                    severity=result_row[11],
                    validated_at=result_row[12]
                )
                
                # Get run info
                run_query = """
                    SELECT run_id, dataset_name, profiled_at, warehouse_type
                    FROM baselinr_runs
                    WHERE run_id = :run_id
                """
                run_row = conn.execute(text(run_query), {"run_id": result.run_id}).fetchone()
                if run_row:
                    run_info = {
                        "run_id": run_row[0],
                        "dataset_name": run_row[1],
                        "profiled_at": run_row[2].isoformat() if isinstance(run_row[2], datetime) else str(run_row[2]),
                        "warehouse_type": run_row[3]
                    }
                
                # Get historical results for same rule
                hist_query = """
                    SELECT 
                        id, run_id, table_name, schema_name, column_name, rule_type, passed,
                        failure_reason, total_rows, failed_rows, failure_rate, severity, validated_at
                    FROM baselinr_validation_results
                    WHERE table_name = :table_name
                    AND rule_type = :rule_type
                    AND id != :result_id
                """
                hist_params = {
                    "table_name": result_row[2],  # table_name from result
                    "rule_type": result_row[5],  # rule_type from result
                    "result_id": result_id
                }
                
                if result_row[4]:  # column_name
                    hist_query += " AND column_name = :column_name"
                    hist_params["column_name"] = result_row[4]
                
                hist_query += " ORDER BY validated_at DESC LIMIT 10"
                
                hist_rows = conn.execute(text(hist_query), hist_params).fetchall()
                for row in hist_rows:
                    historical_results.append(ValidationResultResponse(
                        id=row[0],
                        run_id=row[1],
                        table_name=row[2],
                        schema_name=row[3],
                        column_name=row[4],
                        rule_type=row[5],
                        passed=row[6],
                        failure_reason=row[7],
                        total_rows=row[8],
                        failed_rows=row[9],
                        failure_rate=float(row[10]) if row[10] else None,
                        severity=row[11],
                        validated_at=row[12]
                    ))
                
        except ValueError:
            raise
        except Exception as e:
            logger.warning(f"Could not get validation result details: {e}")
            raise ValueError(f"Validation result {result_id} not found")
        
        return ValidationResultDetailsResponse(
            result=result,
            rule_config=rule_config,
            run_info=run_info,
            historical_results=historical_results
        )
    
    async def get_validation_failure_samples(
        self,
        result_id: int
    ) -> "ValidationFailureSamplesResponse":
        """Get failure samples for a validation result."""
        from models import ValidationFailureSamplesResponse
        
        total_failures = 0
        sample_failures: List[Dict[str, Any]] = []
        failure_patterns: Optional[Dict[str, Any]] = None
        
        if not self._table_exists('baselinr_validation_results'):
            raise ValueError(f"Validation result {result_id} not found")
        
        try:
            with self.engine.connect() as conn:
                # Get the result to check if it failed
                result_query = """
                    SELECT failed_rows, failure_reason
                    FROM baselinr_validation_results
                    WHERE id = :result_id
                """
                result_row = conn.execute(text(result_query), {"result_id": result_id}).fetchone()
                
                if not result_row:
                    raise ValueError(f"Validation result {result_id} not found")
                
                total_failures = result_row[0] or 0
                
                # Sample failures are typically stored in metadata or a separate table
                # For now, we'll return the failure_reason and create a basic sample
                if result_row[1]:  # failure_reason
                    sample_failures.append({
                        "failure_reason": result_row[1],
                        "note": "Detailed failure samples may not be available for all validation types"
                    })
                
        except ValueError:
            raise
        except Exception as e:
            logger.warning(f"Could not get validation failure samples: {e}")
            raise ValueError(f"Validation result {result_id} not found")
        
        return ValidationFailureSamplesResponse(
            result_id=result_id,
            total_failures=total_failures,
            sample_failures=sample_failures,
            failure_patterns=failure_patterns
        )
    
    async def get_drift_summary(
        self,
        warehouse: Optional[str] = None,
        days: int = 30
    ) -> DriftSummaryResponse:
        """Get drift summary statistics."""
        from datetime import timedelta, timezone
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        total_events = 0
        by_severity: Dict[str, int] = {"low": 0, "medium": 0, "high": 0}
        trending: List[TableMetricsTrend] = []
        top_affected_tables: List[TopAffectedTable] = []
        warehouse_breakdown: Dict[str, int] = {}
        recent_activity: List[DriftAlertResponse] = []
        
        if not self._table_exists('baselinr_events'):
            logger.warning("baselinr_events table does not exist, returning empty drift summary")
            return DriftSummaryResponse(
                total_events=0,
                by_severity=by_severity,
                trending=trending,
                top_affected_tables=top_affected_tables,
                warehouse_breakdown=warehouse_breakdown,
                recent_activity=recent_activity
            )
        
        try:
            with self.engine.connect() as conn:
                # Get total events and by severity
                count_query = """
                    SELECT 
                        COUNT(*) as total,
                        drift_severity,
                        COUNT(*) FILTER (WHERE drift_severity = 'low') as low_count,
                        COUNT(*) FILTER (WHERE drift_severity = 'medium') as medium_count,
                        COUNT(*) FILTER (WHERE drift_severity = 'high') as high_count
                    FROM baselinr_events
                    WHERE event_type IN ('DataDriftDetected', 'drift_detected')
                    AND timestamp >= :start_date
                """
                params = {"start_date": start_date}
                
                if warehouse:
                    count_query += " AND EXISTS (SELECT 1 FROM baselinr_runs r WHERE r.run_id = baselinr_events.run_id AND r.warehouse_type = :warehouse)"
                    params["warehouse"] = warehouse
                
                count_query += " GROUP BY drift_severity"
                
                count_results = conn.execute(text(count_query), params).fetchall()
                for row in count_results:
                    severity = row[1] or "low"
                    count = row[0] or 0
                    total_events += count
                    by_severity[severity] = count
                
                # Get trending data (events per day)
                trend_query = """
                    SELECT 
                        DATE(timestamp) as date,
                        COUNT(*) as drift_count
                    FROM baselinr_events
                    WHERE event_type IN ('DataDriftDetected', 'drift_detected')
                    AND timestamp >= :start_date
                """
                if warehouse:
                    trend_query += " AND EXISTS (SELECT 1 FROM baselinr_runs r WHERE r.run_id = baselinr_events.run_id AND r.warehouse_type = :warehouse)"
                
                trend_query += " GROUP BY DATE(timestamp) ORDER BY date ASC"
                
                trend_results = conn.execute(text(trend_query), params).fetchall()
                for row in trend_results:
                    date_val = row[0]
                    count = row[1] or 0
                    if isinstance(date_val, str):
                        try:
                            from dateutil.parser import parse
                            date_val = parse(date_val)
                        except Exception:
                            date_val = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                    elif not isinstance(date_val, datetime):
                        if hasattr(date_val, 'isoformat'):
                            date_val = datetime.combine(date_val, datetime.min.time())
                        else:
                            date_val = datetime.fromisoformat(str(date_val))
                    trending.append(TableMetricsTrend(timestamp=date_val, value=float(count)))
                
                # Get top affected tables
                top_tables_query = """
                    SELECT 
                        table_name,
                        COUNT(*) as drift_count,
                        COUNT(*) FILTER (WHERE drift_severity = 'low') as low_count,
                        COUNT(*) FILTER (WHERE drift_severity = 'medium') as medium_count,
                        COUNT(*) FILTER (WHERE drift_severity = 'high') as high_count
                    FROM baselinr_events
                    WHERE event_type IN ('DataDriftDetected', 'drift_detected')
                    AND timestamp >= :start_date
                """
                if warehouse:
                    top_tables_query += " AND EXISTS (SELECT 1 FROM baselinr_runs r WHERE r.run_id = baselinr_events.run_id AND r.warehouse_type = :warehouse)"
                
                top_tables_query += " GROUP BY table_name ORDER BY drift_count DESC LIMIT 10"
                
                top_tables_results = conn.execute(text(top_tables_query), params).fetchall()
                for row in top_tables_results:
                    table_name = row[0]
                    drift_count = row[1] or 0
                    severity_breakdown = {
                        "low": row[2] or 0,
                        "medium": row[3] or 0,
                        "high": row[4] or 0
                    }
                    top_affected_tables.append(TopAffectedTable(
                        table_name=table_name,
                        drift_count=drift_count,
                        severity_breakdown=severity_breakdown
                    ))
                
                # Get warehouse breakdown
                warehouse_query = """
                    SELECT 
                        COALESCE(r.warehouse_type, 'unknown') as warehouse_type,
                        COUNT(*) as drift_count
                    FROM baselinr_events e
                    LEFT JOIN baselinr_runs r ON e.run_id = r.run_id
                    WHERE e.event_type IN ('DataDriftDetected', 'drift_detected')
                    AND e.timestamp >= :start_date
                """
                if warehouse:
                    warehouse_query += " AND r.warehouse_type = :warehouse"
                
                warehouse_query += " GROUP BY r.warehouse_type"
                
                warehouse_results = conn.execute(text(warehouse_query), params).fetchall()
                for row in warehouse_results:
                    wh_type = row[0] or "unknown"
                    count = row[1] or 0
                    warehouse_breakdown[wh_type] = count
                
                # Get recent activity (last 10 events)
                recent_activity = await self.get_drift_alerts(
                    warehouse=warehouse,
                    start_date=start_date,
                    limit=10
                )
                
        except Exception as e:
            logger.warning(f"Could not get drift summary: {e}")
        
        return DriftSummaryResponse(
            total_events=total_events,
            by_severity=by_severity,
            trending=trending,
            top_affected_tables=top_affected_tables,
            warehouse_breakdown=warehouse_breakdown,
            recent_activity=recent_activity
        )
    
    async def get_drift_details(
        self,
        event_id: str
    ) -> DriftDetailsResponse:
        """Get detailed drift information for a specific event."""
        # Get the event itself
        all_alerts = await self.get_drift_alerts(limit=10000)  # Get all to find the one we need
        event = None
        for alert in all_alerts:
            if alert.event_id == event_id:
                event = alert
                break
        
        if not event:
            raise ValueError(f"Drift event {event_id} not found")
        
        # Get baseline and current metrics from runs
        baseline_metrics: Dict[str, Any] = {}
        current_metrics: Dict[str, Any] = {}
        historical_values: List[Dict[str, Any]] = []
        statistical_tests: Optional[List[Dict[str, Any]]] = None
        related_events: List[DriftAlertResponse] = []
        
        try:
            with self.engine.connect() as conn:
                # Get run details for baseline and current
                run_query = """
                    SELECT run_id, dataset_name, profiled_at
                    FROM baselinr_runs
                    WHERE run_id = :run_id
                """
                run_result = conn.execute(text(run_query), {"run_id": event.run_id}).fetchone()
                
                if run_result:
                    # Get column metrics for the run
                    metrics_query = """
                        SELECT column_name, metric_name, metric_value
                        FROM baselinr_results
                        WHERE run_id = :run_id
                        AND table_name = :table_name
                    """
                    metrics_params = {"run_id": event.run_id, "table_name": event.table_name}
                    if event.column_name:
                        metrics_query += " AND column_name = :column_name"
                        metrics_params["column_name"] = event.column_name
                    
                    metrics_results = conn.execute(text(metrics_query), metrics_params).fetchall()
                    for row in metrics_results:
                        col_name = row[0]
                        metric_name = row[1]
                        metric_value = row[2]
                        if col_name not in current_metrics:
                            current_metrics[col_name] = {}
                        current_metrics[col_name][metric_name] = metric_value
                
                # Get historical values (previous runs for same table/column)
                if event.column_name:
                    hist_query = """
                        SELECT r.profiled_at, res.metric_value
                        FROM baselinr_runs r
                        JOIN baselinr_results res ON r.run_id = res.run_id
                        WHERE res.table_name = :table_name
                        AND res.column_name = :column_name
                        AND res.metric_name = :metric_name
                        AND r.profiled_at < (SELECT profiled_at FROM baselinr_runs WHERE run_id = :run_id)
                        ORDER BY r.profiled_at DESC
                        LIMIT 10
                    """
                    hist_params = {
                        "table_name": event.table_name,
                        "column_name": event.column_name,
                        "metric_name": event.metric_name,
                        "run_id": event.run_id
                    }
                    hist_results = conn.execute(text(hist_query), hist_params).fetchall()
                    for row in hist_results:
                        historical_values.append({
                            "timestamp": row[0].isoformat() if isinstance(row[0], datetime) else str(row[0]),
                            "value": float(row[1]) if row[1] is not None else None
                        })
                
                # Get related events (same table/column)
                related_alerts = await self.get_drift_alerts(
                    table=event.table_name,
                    limit=20
                )
                for alert in related_alerts:
                    if alert.event_id != event_id:
                        if not event.column_name or alert.column_name == event.column_name:
                            related_events.append(alert)
                            if len(related_events) >= 5:
                                break
                
                # Try to get statistical test results from event metadata if available
                # This would require checking if metadata column exists and contains test results
                # For now, we'll leave it as None
                
        except Exception as e:
            logger.warning(f"Could not get drift details: {e}")
        
        return DriftDetailsResponse(
            event=event,
            baseline_metrics=baseline_metrics,
            current_metrics=current_metrics,
            statistical_tests=statistical_tests,
            historical_values=historical_values,
            related_events=related_events
        )
    
    async def get_drift_impact(
        self,
        event_id: str
    ) -> DriftImpactResponse:
        """Get drift impact analysis."""
        # Get the event
        all_alerts = await self.get_drift_alerts(limit=10000)
        event = None
        for alert in all_alerts:
            if alert.event_id == event_id:
                event = alert
                break
        
        if not event:
            raise ValueError(f"Drift event {event_id} not found")
        
        affected_tables: List[str] = []
        affected_metrics = 1  # At least the current metric
        impact_score = 0.5  # Default medium impact
        recommendations: List[str] = []
        
        # Try to use lineage to find downstream tables
        try:
            # Check if lineage is available
            LINEAGE_AVAILABLE = False
            try:
                from lineage_graph import LineageGraphBuilder
                LINEAGE_AVAILABLE = True
            except ImportError:
                pass
            
            # Check if lineage is available
            try:
                from baselinr.visualization import LineageGraphBuilder
                lineage_available = True
            except ImportError:
                lineage_available = False
            
            if lineage_available:
                builder = LineageGraphBuilder(self.engine)
                try:
                    graph = builder.build_table_graph(
                        root_table=event.table_name,
                        direction="downstream",
                        max_depth=3
                    )
                    for node in graph.nodes:
                        if node.id != graph.root_id:
                            affected_tables.append(node.id)
                except Exception as e:
                    logger.warning(f"Could not build lineage graph for impact analysis: {e}")
        except Exception as e:
            logger.warning(f"Could not get drift impact: {e}")
        
        # Calculate impact score based on severity and affected tables
        severity_scores = {"low": 0.2, "medium": 0.5, "high": 0.8}
        base_score = severity_scores.get(event.severity, 0.5)
        table_multiplier = min(1.0, 1.0 + (len(affected_tables) * 0.1))
        impact_score = min(1.0, base_score * table_multiplier)
        
        # Generate recommendations
        if event.severity == "high":
            recommendations.append("High severity drift detected. Investigate immediately.")
        if len(affected_tables) > 0:
            recommendations.append(f"Check {len(affected_tables)} downstream table(s) for cascading effects.")
        if event.change_percent and abs(event.change_percent) > 50:
            recommendations.append("Significant change detected (>50%). Review data pipeline.")
        recommendations.append("Consider adjusting drift detection thresholds if this is expected.")
        
        return DriftImpactResponse(
            event_id=event_id,
            affected_tables=affected_tables,
            affected_metrics=affected_metrics,
            impact_score=impact_score,
            recommendations=recommendations
        )
    
    async def get_lineage_impact(
        self,
        table: str,
        schema: Optional[str] = None,
        include_metrics: bool = True
    ) -> "LineageImpactResponse":
        """Calculate impact analysis for a table."""
        from lineage_models import LineageImpactResponse, TableInfoResponse
        
        affected_tables: List[TableInfoResponse] = []
        drift_propagation: List[str] = []
        recommendations: List[str] = []
        impact_score = 0.0
        affected_metrics = 0
        
        # Check if lineage is available
        try:
            from baselinr.visualization import LineageGraphBuilder
            lineage_available = True
        except ImportError:
            lineage_available = False
        
        if not lineage_available:
            logger.warning("Lineage not available, returning empty impact")
            return LineageImpactResponse(
                table=table,
                schema=schema,
                affected_tables=affected_tables,
                impact_score=0.0,
                affected_metrics=0,
                drift_propagation=drift_propagation,
                recommendations=recommendations
            )
        
        try:
            try:
                from baselinr.visualization import LineageGraphBuilder
            except ImportError:
                try:
                    from lineage_graph import LineageGraphBuilder
                except ImportError:
                    logger.warning("LineageGraphBuilder not available")
                    return LineageImpactResponse(
                        table=table,
                        schema=schema,
                        affected_tables=affected_tables,
                        impact_score=0.0,
                        affected_metrics=0,
                        drift_propagation=drift_propagation,
                        recommendations=recommendations
                    )
            
            # Build downstream graph to find affected tables
            builder = LineageGraphBuilder(self.engine)
            graph = builder.build_table_graph(
                root_table=table,
                schema=schema,
                direction="downstream",
                max_depth=5,
                confidence_threshold=0.5
            )
            
            # Get downstream tables
            for node in graph.nodes:
                if node.id != graph.root_id and node.type == "table":
                    affected_tables.append(TableInfoResponse(
                        schema=node.schema or "",
                        table=node.table or node.label,
                        database=node.database
                    ))
                    drift_propagation.append(node.id)
            
            # Check for drift in root table
            root_node = graph.get_node_by_id(graph.root_id or "")
            has_drift = root_node and root_node.metadata.get("has_drift", False)
            drift_severity = root_node.metadata.get("drift_severity") if root_node else None
            
            # Calculate impact score
            # Base score from number of downstream tables
            table_count_score = min(1.0, len(affected_tables) * 0.1)
            
            # Add drift severity multiplier
            severity_multipliers = {"low": 0.2, "medium": 0.5, "high": 0.8}
            drift_multiplier = severity_multipliers.get(drift_severity, 0.0) if has_drift else 0.0
            
            # Combine scores
            impact_score = min(1.0, table_count_score + (drift_multiplier * 0.5))
            
            # Count affected metrics if requested
            if include_metrics and self._table_exists('baselinr_results'):
                try:
                    with self.engine.connect() as conn:
                        query = """
                            SELECT COUNT(DISTINCT metric_name)
                            FROM baselinr_results
                            WHERE table_name = :table_name
                        """
                        params = {"table_name": table}
                        if schema:
                            query += " AND schema_name = :schema_name"
                            params["schema_name"] = schema
                        
                        result = conn.execute(text(query), params).fetchone()
                        affected_metrics = result[0] if result else 0
                except Exception as e:
                    logger.warning(f"Could not count metrics: {e}")
            
            # Generate recommendations
            if has_drift:
                if drift_severity == "high":
                    recommendations.append("High severity drift detected. Investigate immediately.")
                recommendations.append(f"Check {len(affected_tables)} downstream table(s) for cascading effects.")
            
            if len(affected_tables) > 10:
                recommendations.append("Large number of downstream dependencies. Consider breaking into smaller tables.")
            
            if impact_score > 0.7:
                recommendations.append("High impact score detected. Review data pipeline dependencies.")
            
            if len(affected_tables) == 0:
                recommendations.append("No downstream dependencies found. This table may be a source table.")
            else:
                recommendations.append(f"Monitor {len(affected_tables)} downstream table(s) for data quality issues.")
        
        except Exception as e:
            logger.warning(f"Could not calculate lineage impact: {e}")
        
        return LineageImpactResponse(
            table=table,
            schema=schema,
            affected_tables=affected_tables,
            impact_score=impact_score,
            affected_metrics=affected_metrics,
            drift_propagation=drift_propagation,
            recommendations=recommendations
        )

