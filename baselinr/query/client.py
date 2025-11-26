"""Client for querying Baselinr metadata from storage."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass
class RunSummary:
    """Summary of a profiling run."""

    run_id: str
    dataset_name: str
    schema_name: Optional[str]
    profiled_at: datetime
    environment: Optional[str]
    status: Optional[str]
    row_count: Optional[int]
    column_count: Optional[int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "dataset_name": self.dataset_name,
            "schema_name": self.schema_name,
            "profiled_at": (
                (
                    self.profiled_at.isoformat()
                    if isinstance(self.profiled_at, datetime)
                    else self.profiled_at
                )
                if self.profiled_at
                else None
            ),
            "environment": self.environment,
            "status": self.status,
            "row_count": self.row_count,
            "column_count": self.column_count,
        }


@dataclass
class DriftEvent:
    """Drift detection event."""

    event_id: str
    event_type: str  # Required field, but we handle None in construction
    table_name: Optional[str]
    column_name: Optional[str]
    metric_name: Optional[str]
    baseline_value: Optional[float]
    current_value: Optional[float]
    change_percent: Optional[float]
    drift_severity: Optional[str]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "metric_name": self.metric_name,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
            "change_percent": self.change_percent,
            "drift_severity": self.drift_severity,
            "timestamp": (
                (
                    self.timestamp.isoformat()
                    if isinstance(self.timestamp, datetime)
                    else self.timestamp
                )
                if self.timestamp
                else None
            ),
        }


class MetadataQueryClient:
    """Client for querying Baselinr metadata."""

    def __init__(
        self,
        engine: Engine,
        runs_table: str = "baselinr_runs",
        results_table: str = "baselinr_results",
        events_table: str = "baselinr_events",
        warn_stale_days: Optional[int] = None,
    ):
        self.engine = engine
        self.runs_table = runs_table
        self.results_table = results_table
        self.events_table = events_table
        self.warn_stale_days = warn_stale_days

    def query_runs(
        self,
        schema: Optional[str] = None,
        table: Optional[str] = None,
        status: Optional[str] = None,
        environment: Optional[str] = None,
        days: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[RunSummary]:
        """
        Query profiling runs with filters.

        Args:
            schema: Filter by schema name
            table: Filter by table name
            status: Filter by status
            environment: Filter by environment
            days: Number of days to look back
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            List of RunSummary objects
        """
        conditions = []
        params: Dict[str, Any] = {}

        if schema:
            conditions.append("schema_name = :schema")
            params["schema"] = schema

        if table:
            conditions.append("dataset_name = :table")
            params["table"] = table

        if status:
            conditions.append("status = :status")
            params["status"] = status

        if environment:
            conditions.append("environment = :environment")
            params["environment"] = environment

        if days:
            conditions.append("profiled_at > :start_date")
            params["start_date"] = datetime.utcnow() - timedelta(days=days)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = text(
            f"""
            SELECT run_id, dataset_name, schema_name, profiled_at,
                   environment, status, row_count, column_count
            FROM {self.runs_table}
            WHERE {where_clause}
            ORDER BY profiled_at DESC
            LIMIT :limit OFFSET :offset
        """
        )

        params["limit"] = limit
        params["offset"] = offset

        with self.engine.connect() as conn:
            results = conn.execute(query, params).fetchall()
            summaries = []
            for row in results:
                profiled_at_val: datetime
                if isinstance(row[3], str):
                    profiled_at_val = datetime.fromisoformat(row[3])
                elif isinstance(row[3], datetime):
                    profiled_at_val = row[3]
                else:
                    continue  # Skip invalid rows
                summaries.append(
                    RunSummary(
                        run_id=str(row[0]),
                        dataset_name=str(row[1]),
                        schema_name=str(row[2]) if row[2] else None,
                        profiled_at=profiled_at_val,
                        environment=str(row[4]) if row[4] else None,
                        status=str(row[5]) if row[5] else None,
                        row_count=int(row[6]) if row[6] is not None else None,
                        column_count=int(row[7]) if row[7] is not None else None,
                    )
                )
            return summaries

    def query_run_details(
        self, run_id: str, dataset_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed results for a specific run.

        Args:
            run_id: Run ID to query
            dataset_name: Optional dataset name (required if run has multiple tables)

        Returns:
            Dictionary with run metadata and metrics, or None if not found
        """
        # Get run metadata
        run_query = text(
            f"""
            SELECT run_id, dataset_name, schema_name, profiled_at,
                   environment, status, row_count, column_count
            FROM {self.runs_table}
            WHERE run_id = :run_id
            {"AND dataset_name = :dataset_name" if dataset_name else ""}
            LIMIT 1
        """
        )

        params = {"run_id": run_id}
        if dataset_name:
            params["dataset_name"] = dataset_name

        with self.engine.connect() as conn:
            run_result = conn.execute(run_query, params).fetchone()

            if not run_result:
                return None

            # Get metrics
            metrics_query = text(
                f"""
                SELECT column_name, column_type, metric_name, metric_value
                FROM {self.results_table}
                WHERE run_id = :run_id
                {"AND dataset_name = :dataset_name" if dataset_name else ""}
                ORDER BY column_name, metric_name
            """
            )

            metrics_results = conn.execute(metrics_query, params).fetchall()

            # Organize metrics by column
            columns = {}
            for row in metrics_results:
                col_name = row[0]
                if col_name not in columns:
                    columns[col_name] = {
                        "column_name": col_name,
                        "column_type": row[1],
                        "metrics": {},
                    }
                columns[col_name]["metrics"][row[2]] = row[3]

            return {
                "run_id": run_result[0],
                "dataset_name": run_result[1],
                "schema_name": run_result[2],
                "profiled_at": (
                    (
                        run_result[3].isoformat()
                        if isinstance(run_result[3], datetime)
                        else run_result[3]
                    )
                    if run_result[3]
                    else None
                ),
                "environment": run_result[4],
                "status": run_result[5],
                "row_count": run_result[6],
                "column_count": run_result[7],
                "columns": list(columns.values()),
            }

    def query_drift_events(
        self,
        table: Optional[str] = None,
        severity: Optional[str] = None,
        days: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DriftEvent]:
        """
        Query drift detection events.

        Args:
            table: Filter by table name
            severity: Filter by severity (low/medium/high)
            days: Number of days to look back
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of DriftEvent objects
        """
        conditions = []
        params: Dict[str, Any] = {}

        if table:
            conditions.append("table_name = :table")
            params["table"] = table

        if severity:
            conditions.append("drift_severity = :severity")
            params["severity"] = severity

        if days:
            conditions.append("timestamp > :start_date")
            params["start_date"] = datetime.utcnow() - timedelta(days=days)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = text(
            f"""
            SELECT event_id, event_type, table_name, column_name, metric_name,
                   baseline_value, current_value, change_percent, drift_severity, timestamp
            FROM {self.events_table}
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT :limit OFFSET :offset
        """
        )

        params["limit"] = limit
        params["offset"] = offset

        with self.engine.connect() as conn:
            results = conn.execute(query, params).fetchall()
            events = []
            for row in results:
                timestamp_val: datetime
                if isinstance(row[9], str):
                    timestamp_val = datetime.fromisoformat(row[9])
                elif isinstance(row[9], datetime):
                    timestamp_val = row[9]
                else:
                    continue  # Skip invalid rows
                events.append(
                    DriftEvent(
                        event_id=str(row[0]),
                        event_type=str(row[1]) if row[1] else "drift_detected",
                        table_name=str(row[2]) if row[2] else None,
                        column_name=str(row[3]) if row[3] else None,
                        metric_name=str(row[4]) if row[4] else None,
                        baseline_value=float(row[5]) if row[5] is not None else None,
                        current_value=float(row[6]) if row[6] is not None else None,
                        change_percent=float(row[7]) if row[7] is not None else None,
                        drift_severity=str(row[8]) if row[8] else None,
                        timestamp=timestamp_val,
                    )
                )
            return events

    def query_table_history(
        self, table_name: str, schema_name: Optional[str] = None, days: Optional[int] = 30
    ) -> Dict[str, Any]:
        """
        Get historical profiling data for a specific table.

        Args:
            table_name: Table to query
            schema_name: Optional schema name
            days: Number of days of history

        Returns:
            Dictionary with run history and trends
        """
        conditions = ["dataset_name = :table"]
        params: Dict[str, Any] = {"table": table_name}

        if schema_name:
            conditions.append("schema_name = :schema")
            params["schema"] = schema_name

        if days:
            conditions.append("profiled_at > :start_date")
            params["start_date"] = datetime.utcnow() - timedelta(days=days)

        where_clause = " AND ".join(conditions)

        # Get run history
        runs_query = text(
            f"""
            SELECT run_id, profiled_at, status, row_count, column_count
            FROM {self.runs_table}
            WHERE {where_clause}
            ORDER BY profiled_at DESC
        """
        )

        with self.engine.connect() as conn:
            runs = conn.execute(runs_query, params).fetchall()

            return {
                "table_name": table_name,
                "schema_name": schema_name,
                "run_count": len(runs),
                "runs": [
                    {
                        "run_id": row[0],
                        "profiled_at": (
                            (row[1].isoformat() if isinstance(row[1], datetime) else str(row[1]))
                            if row[1]
                            else None
                        ),
                        "status": str(row[2]) if row[2] else None,
                        "row_count": int(row[3]) if row[3] is not None else None,
                        "column_count": int(row[4]) if row[4] is not None else None,
                    }
                    for row in runs
                ],
            }

    def query_run_events(
        self, run_id: str, event_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query events for a specific run.

        Args:
            run_id: Run ID to query events for
            event_types: Optional list of event types to filter by
                        (e.g., ["ProfilingCompleted", "AnomalyDetected"])

        Returns:
            List of event dictionaries with all event fields
        """
        conditions = ["run_id = :run_id"]
        params: Dict[str, Any] = {"run_id": run_id}

        if event_types:
            placeholders = ", ".join([f":event_type_{i}" for i in range(len(event_types))])
            conditions.append(f"event_type IN ({placeholders})")
            for i, event_type in enumerate(event_types):
                params[f"event_type_{i}"] = event_type

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT event_id, event_type, run_id, table_name, column_name, metric_name,
                   baseline_value, current_value, change_percent, drift_severity,
                   timestamp, metadata
            FROM {self.events_table}
            WHERE {where_clause}
            ORDER BY timestamp DESC
        """
        )

        with self.engine.connect() as conn:
            results = conn.execute(query, params).fetchall()
            events = []
            for row in results:
                timestamp_val: datetime
                if isinstance(row[10], str):
                    timestamp_val = datetime.fromisoformat(row[10])
                elif isinstance(row[10], datetime):
                    timestamp_val = row[10]
                else:
                    continue  # Skip invalid rows

                # Parse metadata if it's a JSON string
                metadata = row[11] if row[11] else {}
                if isinstance(metadata, str):
                    try:
                        import json

                        metadata = json.loads(metadata)
                    except (json.JSONDecodeError, ValueError):
                        metadata = {}

                events.append(
                    {
                        "event_id": str(row[0]),
                        "event_type": str(row[1]) if row[1] else None,
                        "run_id": str(row[2]) if row[2] else None,
                        "table_name": str(row[3]) if row[3] else None,
                        "column_name": str(row[4]) if row[4] else None,
                        "metric_name": str(row[5]) if row[5] else None,
                        "baseline_value": float(row[6]) if row[6] is not None else None,
                        "current_value": float(row[7]) if row[7] is not None else None,
                        "change_percent": float(row[8]) if row[8] is not None else None,
                        "drift_severity": str(row[9]) if row[9] else None,
                        "timestamp": timestamp_val,
                        "metadata": metadata,
                    }
                )
            return events

    def query_active_drift_summary(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Query active drift summary grouped by table.

        Args:
            days: Number of days to look back for drift events

        Returns:
            List of drift summary dictionaries, one per table with active drift
        """
        # Get all drift events in the time window
        drift_events = self.query_drift_events(days=days, limit=10000)

        if not drift_events:
            return []

        # Group by table_name
        table_drifts: Dict[str, List[DriftEvent]] = {}
        for event in drift_events:
            if not event.table_name:
                continue
            if event.table_name not in table_drifts:
                table_drifts[event.table_name] = []
            table_drifts[event.table_name].append(event)

        # Build summary for each table
        summary = []
        for table_name, events in table_drifts.items():
            # Determine highest severity (high > medium > low)
            severity_priority = {"high": 3, "medium": 2, "low": 1, "none": 0}
            highest_severity = "none"
            highest_priority = 0

            # Find earliest timestamp (when drift started)
            earliest_timestamp: Optional[datetime] = None

            # Infer drift type from metric names
            drift_types = set()

            for event in events:
                # Track severity
                if event.drift_severity:
                    priority = severity_priority.get(event.drift_severity.lower(), 0)
                    if priority > highest_priority:
                        highest_priority = priority
                        highest_severity = event.drift_severity.lower()

                # Track earliest timestamp
                if event.timestamp:
                    if earliest_timestamp is None or event.timestamp < earliest_timestamp:
                        earliest_timestamp = event.timestamp

                # Infer drift type from metric_name
                if event.metric_name:
                    metric_lower = event.metric_name.lower()
                    if "schema" in metric_lower or "column" in metric_lower:
                        drift_types.add("schema")
                    elif "count" in metric_lower or "row" in metric_lower:
                        drift_types.add("volume")
                    elif (
                        "mean" in metric_lower
                        or "stddev" in metric_lower
                        or "distribution" in metric_lower
                    ):
                        drift_types.add("distribution")
                    elif "profiled_at" in metric_lower or "freshness" in metric_lower:
                        drift_types.add("freshness")

            # Determine primary drift type (prefer schema > volume > distribution > freshness)
            drift_type = "unknown"
            if "schema" in drift_types:
                drift_type = "schema"
            elif "volume" in drift_types:
                drift_type = "volume"
            elif "distribution" in drift_types:
                drift_type = "distribution"
            elif "freshness" in drift_types:
                drift_type = "freshness"

            summary.append(
                {
                    "table_name": table_name,
                    "severity": highest_severity if highest_severity != "none" else "low",
                    "drift_type": drift_type,
                    "started_at": earliest_timestamp.isoformat() if earliest_timestamp else None,
                    "event_count": len(events),
                }
            )

        # Sort by severity (high first) then by table name
        severity_order: Dict[str, int] = {"high": 3, "medium": 2, "low": 1, "none": 0}
        summary.sort(
            key=lambda x: (
                severity_order.get(str(x.get("severity", "none")), 0),
                str(x.get("table_name", "")),
            ),
            reverse=True,
        )

        return summary

    def query_lineage_upstream(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        max_depth: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query upstream lineage for a table.

        Args:
            table_name: Name of the table
            schema_name: Optional schema name
            max_depth: Maximum depth to traverse

        Returns:
            List of upstream tables with depth information
        """
        from .lineage_client import LineageQueryClient

        lineage_client = LineageQueryClient(self.engine, warn_stale_days=self.warn_stale_days)
        return lineage_client.get_upstream_tables(table_name, schema_name, max_depth)

    def query_lineage_downstream(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        max_depth: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query downstream lineage for a table.

        Args:
            table_name: Name of the table
            schema_name: Optional schema name
            max_depth: Maximum depth to traverse

        Returns:
            List of downstream tables with depth information
        """
        from .lineage_client import LineageQueryClient

        lineage_client = LineageQueryClient(self.engine, warn_stale_days=self.warn_stale_days)
        return lineage_client.get_downstream_tables(table_name, schema_name, max_depth)

    def query_lineage_path(
        self,
        from_table: str,
        to_table: str,
        from_schema: Optional[str] = None,
        to_schema: Optional[str] = None,
        max_depth: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query lineage path between two tables.

        Args:
            from_table: Source table name
            to_table: Target table name
            from_schema: Optional source schema
            to_schema: Optional target schema
            max_depth: Maximum depth to search

        Returns:
            List of tables in the path
        """
        from .lineage_client import LineageQueryClient

        lineage_client = LineageQueryClient(self.engine, warn_stale_days=self.warn_stale_days)
        return lineage_client.get_lineage_path(
            from_table, to_table, from_schema, to_schema, max_depth
        )

    def query_lineage_by_provider(self, provider: str) -> Dict[str, List[str]]:
        """
        Query lineage filtered by provider.

        Args:
            provider: Provider name (e.g., 'dbt', 'sql_parser')

        Returns:
            Dictionary mapping downstream tables to lists of upstream tables
        """
        from .lineage_client import LineageQueryClient

        lineage_client = LineageQueryClient(self.engine, warn_stale_days=self.warn_stale_days)
        return lineage_client.get_lineage_by_provider(provider)

    def query_column_lineage_upstream(
        self,
        table_name: str,
        column_name: str,
        schema_name: Optional[str] = None,
        max_depth: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query upstream column lineage for a specific column.

        Args:
            table_name: Name of the table
            column_name: Name of the column
            schema_name: Optional schema name
            max_depth: Maximum depth to traverse

        Returns:
            List of upstream columns with depth information
        """
        from .lineage_client import LineageQueryClient

        lineage_client = LineageQueryClient(self.engine, warn_stale_days=self.warn_stale_days)
        return lineage_client.get_upstream_columns(table_name, column_name, schema_name, max_depth)

    def query_column_lineage_downstream(
        self,
        table_name: str,
        column_name: str,
        schema_name: Optional[str] = None,
        max_depth: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query downstream column lineage for a specific column.

        Args:
            table_name: Name of the table
            column_name: Name of the column
            schema_name: Optional schema name
            max_depth: Maximum depth to traverse

        Returns:
            List of downstream columns with depth information
        """
        from .lineage_client import LineageQueryClient

        lineage_client = LineageQueryClient(self.engine, warn_stale_days=self.warn_stale_days)
        return lineage_client.get_downstream_columns(
            table_name, column_name, schema_name, max_depth
        )

    def query_column_lineage_path(
        self,
        from_table: str,
        from_column: str,
        to_table: str,
        to_column: str,
        from_schema: Optional[str] = None,
        to_schema: Optional[str] = None,
        max_depth: Optional[int] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Query column lineage path between two columns.

        Args:
            from_table: Source table name
            from_column: Source column name
            to_table: Target table name
            to_column: Target column name
            from_schema: Optional source schema
            to_schema: Optional target schema
            max_depth: Maximum depth to search

        Returns:
            List of columns in the path, or None if no path found
        """
        from .lineage_client import LineageQueryClient

        lineage_client = LineageQueryClient(self.engine, warn_stale_days=self.warn_stale_days)
        return lineage_client.get_column_lineage_path(
            from_table, from_column, to_table, to_column, from_schema, to_schema, max_depth
        )
