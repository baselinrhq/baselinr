"""
Demo Data Service for Baselinr Quality Studio.

Provides the same interface as DatabaseClient but serves data from pre-generated
JSON files instead of a database. Used for the Cloudflare Pages demo deployment.
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from collections import defaultdict
import logging

from models import (
    RunHistoryResponse,
    ProfilingResultResponse,
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

from lineage_models import (
    LineageGraphResponse,
    LineageNodeResponse,
    LineageEdgeResponse,
    LineageImpactResponse,
    TableInfoResponse
)

logger = logging.getLogger(__name__)


class DemoDataService:
    """Service that loads and serves demo data from JSON files."""
    
    def __init__(self, data_dir: str = None):
        """Initialize demo data service by loading JSON files."""
        if data_dir is None:
            # Default to demo_data directory relative to this file
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir, "demo_data")
        
        self.data_dir = data_dir
        self.runs_raw = []
        self.metrics_raw = []
        self.drift_events_raw = []
        self.tables_raw = []
        self.validation_results_raw = []
        self.lineage_raw = {}
        self.metadata = {}
        self.table_quality_scores_raw = []
        self.column_quality_scores_raw = []
        
        # Lookup indices for fast access
        self.runs_by_id = {}
        self.metrics_by_run_id = defaultdict(list)
        self.drift_by_run_id = defaultdict(list)
        self.validations_by_run_id = defaultdict(list)
        
        self._load_data()
        logger.info(f"Demo data loaded: {len(self.runs_raw)} runs, {len(self.metrics_raw)} metrics")
    
    def _load_data(self):
        """Load all JSON files and build indices."""
        try:
            # Load runs
            with open(os.path.join(self.data_dir, "runs.json"), 'r') as f:
                self.runs_raw = json.load(f)
            
            # Load metrics
            with open(os.path.join(self.data_dir, "metrics.json"), 'r') as f:
                self.metrics_raw = json.load(f)
            
            # Load drift events
            with open(os.path.join(self.data_dir, "drift_events.json"), 'r') as f:
                self.drift_events_raw = json.load(f)
            
            # Load tables
            with open(os.path.join(self.data_dir, "tables.json"), 'r') as f:
                self.tables_raw = json.load(f)
            
            # Load validation results
            with open(os.path.join(self.data_dir, "validation_results.json"), 'r') as f:
                self.validation_results_raw = json.load(f)
            
            # Load lineage
            with open(os.path.join(self.data_dir, "lineage.json"), 'r') as f:
                self.lineage_raw = json.load(f)
            
            # Load table quality scores
            quality_scores_file = os.path.join(self.data_dir, "table_quality_scores.json")
            if os.path.exists(quality_scores_file):
                with open(quality_scores_file, 'r') as f:
                    self.table_quality_scores_raw = json.load(f)
            
            # Load column quality scores
            column_scores_file = os.path.join(self.data_dir, "column_quality_scores.json")
            if os.path.exists(column_scores_file):
                with open(column_scores_file, 'r') as f:
                    self.column_quality_scores_raw = json.load(f)
            
            # Load metadata
            with open(os.path.join(self.data_dir, "metadata.json"), 'r') as f:
                self.metadata = json.load(f)
            
            # Build indices
            self._build_indices()
            
        except Exception as e:
            logger.error(f"Error loading demo data: {e}")
            raise
    
    def _build_indices(self):
        """Build lookup indices for fast access."""
        # Index runs by ID
        for run in self.runs_raw:
            self.runs_by_id[run['run_id']] = run
        
        # Index metrics by run_id
        for metric in self.metrics_raw:
            self.metrics_by_run_id[metric['run_id']].append(metric)
        
        # Index drift events by run_id
        for event in self.drift_events_raw:
            self.drift_by_run_id[event['run_id']].append(event)
        
        # Index validation results by run_id
        for result in self.validation_results_raw:
            self.validations_by_run_id[result['run_id']].append(result)
    
    def _parse_datetime(self, date_str: str) -> datetime:
        """Parse ISO datetime string to datetime object."""
        if isinstance(date_str, datetime):
            return date_str
        dt = datetime.fromisoformat(date_str)
        # Make timezone-naive for consistent comparison
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    
    def _filter_by_date_range(self, items: List[Dict], date_field: str, 
                              start_date: Optional[datetime], end_date: Optional[datetime]) -> List[Dict]:
        """Filter items by date range."""
        if not start_date and not end_date:
            return items
        
        # Make filter dates timezone-naive for consistent comparison
        if start_date and start_date.tzinfo is not None:
            start_date = start_date.replace(tzinfo=None)
        if end_date and end_date.tzinfo is not None:
            end_date = end_date.replace(tzinfo=None)
        
        result = []
        for item in items:
            item_date = self._parse_datetime(item[date_field])
            if start_date and item_date < start_date:
                continue
            if end_date and item_date > end_date:
                continue
            result.append(item)
        return result
    
    def _sort_items(self, items: List[Dict], sort_by: str, sort_order: str) -> List[Dict]:
        """Sort items by field."""
        reverse = sort_order.lower() == "desc"
        
        def get_sort_key(item):
            value = item.get(sort_by)
            if value is None:
                return ""
            if isinstance(value, str) and "T" in value:  # ISO date string
                try:
                    return self._parse_datetime(value)
                except:
                    return value
            return value
        
        return sorted(items, key=get_sort_key, reverse=reverse)
    
    def _paginate(self, items: List, offset: int, limit: int) -> List:
        """Apply pagination to items."""
        return items[offset:offset + limit]
    
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
        # Start with all runs
        filtered = list(self.runs_raw)
        
        # Apply filters
        if warehouse:
            filtered = [r for r in filtered if r.get('warehouse_type') == warehouse]
        if schema:
            filtered = [r for r in filtered if r.get('schema_name') == schema]
        if table:
            filtered = [r for r in filtered if r.get('dataset_name') == table]
        if status:
            filtered = [r for r in filtered if r.get('status') == status]
        
        # Date range filter
        filtered = self._filter_by_date_range(filtered, 'profiled_at', start_date, end_date)
        
        # Duration filters
        if min_duration is not None:
            filtered = [r for r in filtered if r.get('duration_seconds') and r['duration_seconds'] >= min_duration]
        if max_duration is not None:
            filtered = [r for r in filtered if r.get('duration_seconds') and r['duration_seconds'] <= max_duration]
        
        # Sort
        filtered = self._sort_items(filtered, sort_by, sort_order)
        
        # Paginate
        paginated = self._paginate(filtered, offset, limit)
        
        # Convert to response models
        return [
            RunHistoryResponse(
                run_id=r['run_id'],
                dataset_name=r['dataset_name'],
                schema_name=r.get('schema_name'),
                warehouse_type=r['warehouse_type'],
                profiled_at=self._parse_datetime(r['profiled_at']),
                status=r['status'],
                row_count=r.get('row_count'),
                column_count=r.get('column_count'),
                duration_seconds=r.get('duration_seconds'),
                has_drift=r.get('has_drift', False)
            )
            for r in paginated
        ]
    
    async def get_run_details(self, run_id: str) -> Optional[ProfilingResultResponse]:
        """Get detailed profiling result for a specific run."""
        run = self.runs_by_id.get(run_id)
        if not run:
            return None
        
        # Get metrics for this run
        metrics = self.metrics_by_run_id.get(run_id, [])
        
        # Convert metrics to ColumnMetrics
        column_metrics = []
        for m in metrics:
            column_metrics.append(ColumnMetrics(
                column_name=m['column_name'],
                column_type=m['column_type'],
                null_count=m.get('null_count'),
                null_percent=m.get('null_percent'),
                distinct_count=m.get('distinct_count'),
                distinct_percent=m.get('distinct_percent'),
                min_value=m.get('min_value'),
                max_value=m.get('max_value'),
                mean=m.get('mean'),
                stddev=m.get('stddev'),
                histogram=None
            ))
        
        return ProfilingResultResponse(
            run_id=run['run_id'],
            dataset_name=run['dataset_name'],
            schema_name=run.get('schema_name'),
            warehouse_type=run['warehouse_type'],
            profiled_at=self._parse_datetime(run['profiled_at']),
            environment=run.get('environment', 'production'),
            row_count=run.get('row_count', 0),
            column_count=run.get('column_count', 0),
            columns=column_metrics,
            metadata={}
        )
    
    async def get_drift_alerts(
        self,
        warehouse: Optional[str] = None,
        schema: Optional[str] = None,
        table: Optional[str] = None,
        severity: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sort_by: str = "timestamp",
        sort_order: str = "desc",
        limit: int = 100,
        offset: int = 0
    ) -> List[DriftAlertResponse]:
        """Get drift detection alerts with filters."""
        filtered = list(self.drift_events_raw)
        
        # Apply filters
        if warehouse:
            filtered = [e for e in filtered if e.get('warehouse_type') == warehouse]
        if schema:
            # Get schema from run
            filtered = [e for e in filtered if self.runs_by_id.get(e['run_id'], {}).get('schema_name') == schema]
        if table:
            filtered = [e for e in filtered if e.get('table_name') == table]
        if severity:
            filtered = [e for e in filtered if e.get('severity') == severity]
        
        # Date range
        filtered = self._filter_by_date_range(filtered, 'timestamp', start_date, end_date)
        
        # Sort
        filtered = self._sort_items(filtered, sort_by, sort_order)
        
        # Paginate
        paginated = self._paginate(filtered, offset, limit)
        
        # Convert to response models
        return [
            DriftAlertResponse(
                event_id=e['event_id'],
                run_id=e['run_id'],
                table_name=e['table_name'],
                column_name=e.get('column_name'),
                metric_name=e['metric_name'],
                baseline_value=e.get('baseline_value'),
                current_value=e.get('current_value'),
                change_percent=e.get('change_percent'),
                severity=e['severity'],
                timestamp=self._parse_datetime(e['timestamp']),
                warehouse_type=e['warehouse_type']
            )
            for e in paginated
        ]
    
    async def get_table_metrics(
        self,
        table_name: str,
        schema: Optional[str] = None,
        warehouse: Optional[str] = None
    ) -> Optional[TableMetricsResponse]:
        """Get detailed metrics for a specific table."""
        # Find table metadata
        table_meta = None
        for t in self.tables_raw:
            if t['table_name'] == table_name:
                if schema and t.get('schema_name') != schema:
                    continue
                if warehouse and t.get('warehouse_type') != warehouse:
                    continue
                table_meta = t
                break
        
        if not table_meta:
            return None
        
        # Get all runs for this table
        table_runs = [r for r in self.runs_raw 
                     if r['dataset_name'] == table_name 
                     and (not schema or r.get('schema_name') == schema)]
        
        if not table_runs:
            return None
        
        # Sort by date
        table_runs = self._sort_items(table_runs, 'profiled_at', 'desc')
        latest_run = table_runs[0]
        
        # Get metrics from latest run
        metrics = self.metrics_by_run_id.get(latest_run['run_id'], [])
        column_metrics = []
        for m in metrics:
            column_metrics.append(ColumnMetrics(
                column_name=m['column_name'],
                column_type=m['column_type'],
                null_count=m.get('null_count'),
                null_percent=m.get('null_percent'),
                distinct_count=m.get('distinct_count'),
                distinct_percent=m.get('distinct_percent'),
                min_value=m.get('min_value'),
                max_value=m.get('max_value'),
                mean=m.get('mean'),
                stddev=m.get('stddev'),
                histogram=None
            ))
        
        # Calculate trends
        row_count_trend = []
        null_percent_trend = []
        for run in table_runs[-30:]:  # Last 30 runs
            row_count_trend.append(TableMetricsTrend(
                timestamp=self._parse_datetime(run['profiled_at']),
                value=float(run.get('row_count', 0))
            ))
            # Calculate average null percent for this run
            run_metrics = self.metrics_by_run_id.get(run['run_id'], [])
            if run_metrics:
                avg_null = sum(m.get('null_percent', 0) for m in run_metrics) / len(run_metrics)
                null_percent_trend.append(TableMetricsTrend(
                    timestamp=self._parse_datetime(run['profiled_at']),
                    value=avg_null
                ))
        
        # Count drift events
        drift_count = sum(1 for e in self.drift_events_raw if e['table_name'] == table_name)
        
        return TableMetricsResponse(
            table_name=table_name,
            schema_name=schema,
            warehouse_type=table_meta.get('warehouse_type', 'unknown'),
            last_profiled=self._parse_datetime(latest_run['profiled_at']),
            row_count=latest_run.get('row_count', 0),
            column_count=latest_run.get('column_count', 0),
            total_runs=len(table_runs),
            drift_count=drift_count,
            row_count_trend=row_count_trend,
            null_percent_trend=null_percent_trend,
            columns=column_metrics
        )
    
    async def get_dashboard_metrics(
        self,
        warehouse: Optional[str] = None,
        start_date: Optional[datetime] = None
    ) -> MetricsDashboardResponse:
        """Get aggregate metrics for dashboard overview."""
        # Filter runs if warehouse or start_date specified
        filtered_runs = list(self.runs_raw)
        if warehouse:
            filtered_runs = [r for r in filtered_runs if r.get('warehouse_type') == warehouse]
        if start_date:
            filtered_runs = self._filter_by_date_range(filtered_runs, 'profiled_at', start_date, None)
        
        # Count totals
        total_runs = len(filtered_runs)
        total_tables = len(self.tables_raw)
        total_drift_events = len(self.drift_events_raw)
        
        # Calculate average row count (use filtered runs)
        row_counts = [r.get('row_count', 0) for r in filtered_runs if r.get('row_count')]
        avg_row_count = sum(row_counts) / len(row_counts) if row_counts else 0
        
        # Warehouse breakdown (use filtered runs)
        warehouse_breakdown = {}
        for run in filtered_runs:
            wh = run.get('warehouse_type', 'unknown')
            warehouse_breakdown[wh] = warehouse_breakdown.get(wh, 0) + 1
        
        # Calculate KPIs (use filtered runs)
        successful_runs = len([r for r in filtered_runs if r.get('status') in ['completed', 'success']])
        success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0
        
        kpis = [
            KPI(name="Success Rate", value=f"{success_rate:.1f}%", trend="stable"),
            KPI(name="Avg Row Count", value=f"{avg_row_count:.0f}", trend="stable"),
            KPI(name="Total Tables", value=total_tables, trend="stable")
        ]
        
        # Run trend (last 30 days) - use filtered runs
        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)
        run_trend = []
        for i in range(30):
            date = thirty_days_ago + timedelta(days=i)
            count = len([r for r in filtered_runs 
                        if self._parse_datetime(r['profiled_at']).date() == date.date()])
            run_trend.append(TableMetricsTrend(timestamp=date, value=float(count)))
        
        # Drift trend
        drift_trend = []
        for i in range(30):
            date = thirty_days_ago + timedelta(days=i)
            count = len([e for e in self.drift_events_raw 
                        if self._parse_datetime(e['timestamp']).date() == date.date()])
            drift_trend.append(TableMetricsTrend(timestamp=date, value=float(count)))
        
        # Recent runs (apply same filters)
        recent_runs = await self.get_runs(warehouse=warehouse, start_date=start_date, limit=10, offset=0)
        
        # Recent drift
        recent_drift = await self.get_drift_alerts(limit=10, offset=0)
        
        # Validation metrics
        total_validations = len(self.validation_results_raw)
        passed_validations = len([v for v in self.validation_results_raw if v.get('passed')])
        validation_pass_rate = (passed_validations / total_validations * 100) if total_validations > 0 else None
        failed_validation_rules = total_validations - passed_validations
        
        # Validation trend
        validation_trend = []
        for i in range(30):
            date = thirty_days_ago + timedelta(days=i)
            day_validations = [v for v in self.validation_results_raw 
                              if self._parse_datetime(v['validated_at']).date() == date.date()]
            if day_validations:
                day_passed = len([v for v in day_validations if v.get('passed')])
                pass_rate = (day_passed / len(day_validations) * 100)
                validation_trend.append(TableMetricsTrend(timestamp=date, value=pass_rate))
        
        # System quality score (simple average)
        system_quality_score = validation_pass_rate if validation_pass_rate else 85.0
        quality_score_status = "healthy" if system_quality_score >= 80 else "warning" if system_quality_score >= 60 else "critical"
        
        return MetricsDashboardResponse(
            total_runs=total_runs,
            total_tables=total_tables,
            total_drift_events=total_drift_events,
            avg_row_count=avg_row_count,
            kpis=kpis,
            run_trend=run_trend,
            drift_trend=drift_trend,
            warehouse_breakdown=warehouse_breakdown,
            recent_runs=recent_runs,
            recent_drift=recent_drift,
            validation_pass_rate=validation_pass_rate,
            total_validation_rules=total_validations,
            failed_validation_rules=failed_validation_rules,
            active_alerts=total_drift_events,
            data_freshness_hours=None,
            stale_tables_count=0,
            validation_trend=validation_trend,
            system_quality_score=system_quality_score,
            quality_score_status=quality_score_status,
            quality_trend="stable"
        )
    
    async def get_warehouses(self) -> List[str]:
        """Get list of unique warehouses."""
        warehouses = set(r.get('warehouse_type') for r in self.runs_raw if r.get('warehouse_type'))
        return sorted(list(warehouses))
    
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
        """Get list of tables with pagination and filtering."""
        filtered = list(self.tables_raw)
        
        # Apply filters
        if warehouse:
            filtered = [t for t in filtered if t.get('warehouse_type') == warehouse]
        if schema:
            filtered = [t for t in filtered if t.get('schema_name') == schema]
        if search:
            search_lower = search.lower()
            filtered = [t for t in filtered 
                       if search_lower in t.get('table_name', '').lower() 
                       or search_lower in t.get('schema_name', '').lower()]
        if has_drift is not None:
            filtered = [t for t in filtered if t.get('has_recent_drift') == has_drift]
        if has_failed_validations is not None:
            filtered = [t for t in filtered if t.get('has_failed_validations') == has_failed_validations]
        
        total = len(filtered)
        
        # Sort
        filtered = self._sort_items(filtered, sort_by, sort_order)
        
        # Paginate (convert page/page_size to limit/offset)
        offset = (page - 1) * page_size
        limit = page_size
        paginated = self._paginate(filtered, offset, limit)
        
        # Convert to response models
        tables = [
            TableListItem(
                table_name=t['table_name'],
                schema_name=t.get('schema_name'),
                warehouse_type=t['warehouse_type'],
                last_profiled=self._parse_datetime(t['last_profiled']) if t.get('last_profiled') else None,
                row_count=t.get('row_count'),
                column_count=t.get('column_count'),
                total_runs=t.get('total_runs', 0),
                drift_count=t.get('drift_count', 0),
                validation_pass_rate=t.get('validation_pass_rate'),
                has_recent_drift=t.get('has_recent_drift', False),
                has_failed_validations=t.get('has_failed_validations', False)
            )
            for t in paginated
        ]
        
        return TableListResponse(
            tables=tables,
            total=total,
            page=offset // limit + 1 if limit > 0 else 1,
            page_size=limit
        )
    
    async def get_table_overview(
        self,
        table_name: str,
        schema: Optional[str] = None,
        warehouse: Optional[str] = None
    ) -> Optional[TableOverviewResponse]:
        """Get detailed table overview."""
        # Find table metadata
        table_meta = None
        for t in self.tables_raw:
            if t['table_name'] == table_name:
                if schema and t.get('schema_name') != schema:
                    continue
                if warehouse and t.get('warehouse_type') != warehouse:
                    continue
                table_meta = t
                break
        
        if not table_meta:
            return None
        
        # Get table metrics
        metrics_response = await self.get_table_metrics(table_name, schema, warehouse)
        if not metrics_response:
            return None
        
        # Get recent runs
        table_runs = await self.get_runs(table=table_name, schema=schema, limit=10)
        
        return TableOverviewResponse(
            table_name=table_name,
            schema_name=schema,
            warehouse_type=table_meta.get('warehouse_type', 'unknown'),
            last_profiled=metrics_response.last_profiled,
            row_count=metrics_response.row_count,
            column_count=metrics_response.column_count,
            total_runs=metrics_response.total_runs,
            drift_count=metrics_response.drift_count,
            validation_pass_rate=table_meta.get('validation_pass_rate'),
            total_validation_rules=0,
            failed_validation_rules=0,
            row_count_trend=metrics_response.row_count_trend,
            null_percent_trend=metrics_response.null_percent_trend,
            columns=metrics_response.columns,
            recent_runs=table_runs
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
        drift_events = await self.get_drift_alerts(table=table_name, schema=schema, limit=limit)
        
        summary = {
            "total_events": len(drift_events),
            "by_severity": {}
        }
        
        for event in drift_events:
            sev = event.severity
            summary["by_severity"][sev] = summary["by_severity"].get(sev, 0) + 1
        
        return TableDriftHistoryResponse(
            table_name=table_name,
            schema_name=schema,
            drift_events=drift_events,
            summary=summary
        )
    
    async def get_table_validation_results(
        self,
        table_name: str,
        schema: Optional[str] = None,
        limit: int = 100
    ) -> TableValidationResultsResponse:
        """Get validation results for a specific table."""
        filtered = [v for v in self.validation_results_raw if v.get('table_name') == table_name]
        if schema:
            filtered = [v for v in filtered if v.get('schema_name') == schema]
        
        # Limit results
        filtered = filtered[:limit]
        
        # Convert to response models
        results = [
            ValidationResultResponse(
                id=v['id'],
                run_id=v['run_id'],
                table_name=v['table_name'],
                schema_name=v.get('schema_name'),
                column_name=v.get('column_name'),
                rule_type=v['rule_type'],
                passed=v['passed'],
                failure_reason=v.get('failure_reason'),
                total_rows=v.get('total_rows'),
                failed_rows=v.get('failed_rows'),
                failure_rate=v.get('failure_rate'),
                severity=v.get('severity'),
                validated_at=self._parse_datetime(v['validated_at'])
            )
            for v in filtered
        ]
        
        # Calculate summary
        passed_count = len([v for v in filtered if v.get('passed')])
        failed_count = len(filtered) - passed_count
        pass_rate = (passed_count / len(filtered) * 100) if filtered else 0
        
        summary = {
            "total": len(filtered),
            "passed": passed_count,
            "failed": failed_count,
            "pass_rate": pass_rate
        }
        
        return TableValidationResultsResponse(
            table_name=table_name,
            schema_name=schema,
            validation_results=results,
            summary=summary
        )
    
    async def get_validation_summary(
        self,
        warehouse: Optional[str] = None,
        days: int = 30
    ) -> ValidationSummaryResponse:
        """Get validation summary statistics."""
        filtered = list(self.validation_results_raw)
        
        # Apply filters
        if warehouse:
            # Filter by warehouse through run lookup
            run_ids = set(r['run_id'] for r in self.runs_raw if r.get('warehouse_type') == warehouse)
            filtered = [v for v in filtered if v['run_id'] in run_ids]
        
        # Date range filter (last N days)
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered = self._filter_by_date_range(filtered, 'validated_at', cutoff_date, None)
        
        total_validations = len(filtered)
        passed_count = len([v for v in filtered if v.get('passed')])
        failed_count = total_validations - passed_count
        pass_rate = (passed_count / total_validations * 100) if total_validations > 0 else 0
        
        # Group by rule type
        by_rule_type = {}
        for v in filtered:
            rule_type = v.get('rule_type', 'unknown')
            by_rule_type[rule_type] = by_rule_type.get(rule_type, 0) + 1
        
        # Group by severity
        by_severity = {}
        for v in filtered:
            if not v.get('passed'):
                severity = v.get('severity', 'medium')
                by_severity[severity] = by_severity.get(severity, 0) + 1
        
        # Group by table
        by_table = {}
        for v in filtered:
            table = v.get('table_name', 'unknown')
            by_table[table] = by_table.get(table, 0) + 1
        
        # Trending (last 30 days)
        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)
        trending = []
        for i in range(30):
            date = thirty_days_ago + timedelta(days=i)
            day_validations = [v for v in filtered 
                              if self._parse_datetime(v['validated_at']).date() == date.date()]
            if day_validations:
                day_passed = len([v for v in day_validations if v.get('passed')])
                day_pass_rate = (day_passed / len(day_validations) * 100)
                trending.append(TableMetricsTrend(timestamp=date, value=day_pass_rate))
        
        return ValidationSummaryResponse(
            total_validations=total_validations,
            passed_count=passed_count,
            failed_count=failed_count,
            pass_rate=pass_rate,
            by_rule_type=by_rule_type,
            by_severity=by_severity,
            by_table=by_table,
            trending=trending,
            recent_runs=[]
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
    ) -> ValidationResultsListResponse:
        """Get list of validation results with filters."""
        filtered = list(self.validation_results_raw)
        
        # Date range filter (last N days)
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered = self._filter_by_date_range(filtered, 'validated_at', cutoff_date, None)
        
        # Apply filters
        if schema:
            filtered = [v for v in filtered if v.get('schema_name') == schema]
        if table:
            filtered = [v for v in filtered if v.get('table_name') == table]
        if rule_type:
            filtered = [v for v in filtered if v.get('rule_type') == rule_type]
        if passed is not None:
            filtered = [v for v in filtered if v.get('passed') == passed]
        if severity:
            filtered = [v for v in filtered if v.get('severity') == severity]
        
        total = len(filtered)
        
        # Sort by validated_at desc
        filtered = self._sort_items(filtered, 'validated_at', 'desc')
        
        # Paginate (convert page/page_size to limit/offset)
        offset = (page - 1) * page_size
        limit = page_size
        paginated = self._paginate(filtered, offset, limit)
        
        # Convert to response models
        results = [
            ValidationResultResponse(
                id=v['id'],
                run_id=v['run_id'],
                table_name=v['table_name'],
                schema_name=v.get('schema_name'),
                column_name=v.get('column_name'),
                rule_type=v['rule_type'],
                passed=v['passed'],
                failure_reason=v.get('failure_reason'),
                total_rows=v.get('total_rows'),
                failed_rows=v.get('failed_rows'),
                failure_rate=v.get('failure_rate'),
                severity=v.get('severity'),
                validated_at=self._parse_datetime(v['validated_at'])
            )
            for v in paginated
        ]
        
        return ValidationResultsListResponse(
            results=results,
            total=total,
            page=offset // limit + 1 if limit > 0 else 1,
            page_size=limit
        )
    
    async def get_validation_result_details(
        self,
        result_id: int
    ) -> Optional[ValidationResultDetailsResponse]:
        """Get detailed validation result with context."""
        # Find validation result
        result = None
        for v in self.validation_results_raw:
            if v.get('id') == result_id:
                result = v
                break
        
        if not result:
            return None
        
        result_response = ValidationResultResponse(
            id=result['id'],
            run_id=result['run_id'],
            table_name=result['table_name'],
            schema_name=result.get('schema_name'),
            column_name=result.get('column_name'),
            rule_type=result['rule_type'],
            passed=result['passed'],
            failure_reason=result.get('failure_reason'),
            total_rows=result.get('total_rows'),
            failed_rows=result.get('failed_rows'),
            failure_rate=result.get('failure_rate'),
            severity=result.get('severity'),
            validated_at=self._parse_datetime(result['validated_at'])
        )
        
        # Get run info
        run = self.runs_by_id.get(result['run_id'])
        run_info = {
            "run_id": run['run_id'],
            "profiled_at": run['profiled_at'],
            "status": run['status']
        } if run else None
        
        # Get historical results for same rule
        historical = [
            ValidationResultResponse(
                id=v['id'],
                run_id=v['run_id'],
                table_name=v['table_name'],
                schema_name=v.get('schema_name'),
                column_name=v.get('column_name'),
                rule_type=v['rule_type'],
                passed=v['passed'],
                failure_reason=v.get('failure_reason'),
                total_rows=v.get('total_rows'),
                failed_rows=v.get('failed_rows'),
                failure_rate=v.get('failure_rate'),
                severity=v.get('severity'),
                validated_at=self._parse_datetime(v['validated_at'])
            )
            for v in self.validation_results_raw
            if v.get('table_name') == result['table_name']
            and v.get('rule_type') == result['rule_type']
            and v.get('id') != result_id
        ][:10]
        
        return ValidationResultDetailsResponse(
            result=result_response,
            rule_config=None,
            run_info=run_info,
            historical_results=historical
        )
    
    async def get_validation_failure_samples(
        self,
        result_id: int,
        limit: int = 10
    ) -> Optional[ValidationFailureSamplesResponse]:
        """Get failure samples for a validation result."""
        # Find validation result
        result = None
        for v in self.validation_results_raw:
            if v.get('id') == result_id:
                result = v
                break
        
        if not result or result.get('passed'):
            return None
        
        # Generate sample failures (mock data)
        sample_failures = []
        failed_rows = result.get('failed_rows', 0)
        for i in range(min(limit, 10)):
            sample_failures.append({
                "row_number": i + 1,
                "column": result.get('column_name', 'unknown'),
                "value": f"invalid_value_{i}",
                "reason": result.get('failure_reason', 'Validation failed')
            })
        
        return ValidationFailureSamplesResponse(
            result_id=result_id,
            total_failures=failed_rows,
            sample_failures=sample_failures,
            failure_patterns=None
        )
    
    async def get_drift_summary(
        self,
        warehouse: Optional[str] = None,
        days: int = 30
    ) -> DriftSummaryResponse:
        """Get drift summary statistics."""
        filtered = list(self.drift_events_raw)
        
        # Apply filters
        if warehouse:
            filtered = [e for e in filtered if e.get('warehouse_type') == warehouse]
        
        # Date range filter (last N days)
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered = self._filter_by_date_range(filtered, 'timestamp', cutoff_date, None)
        
        total_events = len(filtered)
        
        # Group by severity
        by_severity = {}
        for e in filtered:
            severity = e.get('severity', 'unknown')
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        # Trending (last 30 days)
        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)
        trending = []
        for i in range(30):
            date = thirty_days_ago + timedelta(days=i)
            count = len([e for e in filtered 
                        if self._parse_datetime(e['timestamp']).date() == date.date()])
            trending.append(TableMetricsTrend(timestamp=date, value=float(count)))
        
        # Top affected tables
        table_drift_counts = {}
        for e in filtered:
            table = e.get('table_name', 'unknown')
            if table not in table_drift_counts:
                table_drift_counts[table] = {"count": 0, "by_severity": {}}
            table_drift_counts[table]["count"] += 1
            severity = e.get('severity', 'unknown')
            table_drift_counts[table]["by_severity"][severity] = \
                table_drift_counts[table]["by_severity"].get(severity, 0) + 1
        
        top_affected_tables = [
            TopAffectedTable(
                table_name=table,
                drift_count=data["count"],
                severity_breakdown=data["by_severity"]
            )
            for table, data in sorted(table_drift_counts.items(), 
                                     key=lambda x: x[1]["count"], reverse=True)[:10]
        ]
        
        # Warehouse breakdown
        warehouse_breakdown = {}
        for e in filtered:
            wh = e.get('warehouse_type', 'unknown')
            warehouse_breakdown[wh] = warehouse_breakdown.get(wh, 0) + 1
        
        # Recent activity
        recent_activity = await self.get_drift_alerts(limit=10)
        
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
    ) -> Optional[DriftDetailsResponse]:
        """Get detailed drift information for a specific event."""
        # Find drift event
        event = None
        for e in self.drift_events_raw:
            if e.get('event_id') == event_id:
                event = e
                break
        
        if not event:
            return None
        
        event_response = DriftAlertResponse(
            event_id=event['event_id'],
            run_id=event['run_id'],
            table_name=event['table_name'],
            column_name=event.get('column_name'),
            metric_name=event['metric_name'],
            baseline_value=event.get('baseline_value'),
            current_value=event.get('current_value'),
            change_percent=event.get('change_percent'),
            severity=event['severity'],
            timestamp=self._parse_datetime(event['timestamp']),
            warehouse_type=event['warehouse_type']
        )
        
        # Get baseline and current metrics
        baseline_metrics = {
            "metric_name": event['metric_name'],
            "value": event.get('baseline_value')
        }
        
        current_metrics = {
            "metric_name": event['metric_name'],
            "value": event.get('current_value')
        }
        
        # Get related events
        related_events = await self.get_drift_alerts(
            table=event['table_name'],
            limit=5
        )
        related_events = [e for e in related_events if e.event_id != event_id]
        
        return DriftDetailsResponse(
            event=event_response,
            baseline_metrics=baseline_metrics,
            current_metrics=current_metrics,
            statistical_tests=None,
            historical_values=[],
            related_events=related_events
        )
    
    async def get_drift_impact(
        self,
        event_id: str
    ) -> Optional[DriftImpactResponse]:
        """Get drift impact analysis."""
        # Find drift event
        event = None
        for e in self.drift_events_raw:
            if e.get('event_id') == event_id:
                event = e
                break
        
        if not event:
            return None
        
        # Get affected tables from lineage
        table_name = event['table_name']
        affected_tables = []
        
        # Look for downstream tables in lineage
        for edge in self.lineage_raw.get('edges', []):
            if table_name in edge.get('source', ''):
                target = edge.get('target', '')
                if '.' in target:
                    schema, table = target.split('.')
                    affected_tables.append(table)
        
        # Calculate impact score based on severity and affected tables
        severity_scores = {"low": 0.3, "medium": 0.6, "high": 0.9}
        base_score = severity_scores.get(event.get('severity', 'low'), 0.5)
        impact_score = min(base_score + (len(affected_tables) * 0.1), 1.0)
        
        # Generate recommendations
        recommendations = [
            f"Investigate {event['metric_name']} changes in {event['table_name']}",
            f"Check data quality in upstream sources",
            f"Review {len(affected_tables)} downstream tables for cascading issues"
        ]
        
        return DriftImpactResponse(
            event_id=event_id,
            affected_tables=affected_tables,
            affected_metrics=1,
            impact_score=impact_score,
            recommendations=recommendations
        )
    
    async def get_lineage_impact(
        self,
        table: str,
        schema: Optional[str] = None
    ) -> Optional[LineageImpactResponse]:
        """Get lineage-based impact analysis for a table."""
        # Build table reference
        table_ref = f"{schema}.{table}" if schema else table
        
        # Find affected tables (downstream)
        affected_tables = []
        for edge in self.lineage_raw.get('edges', []):
            source = edge.get('source', '')
            if table in source or table_ref == source:
                target = edge.get('target', '')
                if '.' in target:
                    target_schema, target_table = target.split('.')
                    affected_tables.append(TableInfoResponse(
                        schema=target_schema,
                        table=target_table,
                        database=None
                    ))
        
        # Calculate impact score
        impact_score = min(len(affected_tables) * 0.2, 1.0)
        
        # Count affected metrics (approximate)
        affected_metrics = len(affected_tables) * 5
        
        # Generate drift propagation path
        drift_propagation = [table]
        for t in affected_tables[:3]:
            drift_propagation.append(f"{t.schema}.{t.table}")
        
        # Generate recommendations
        recommendations = [
            f"Monitor {len(affected_tables)} downstream tables",
            "Review data transformations in pipeline",
            "Set up alerts for downstream quality checks"
        ]
        
        return LineageImpactResponse(
            table=table,
            schema=schema,
            affected_tables=affected_tables,
            impact_score=impact_score,
            affected_metrics=affected_metrics,
            drift_propagation=drift_propagation,
            recommendations=recommendations
        )

