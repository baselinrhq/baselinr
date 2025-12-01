"""
Lineage-based analyzer for RCA.

Uses the existing lineage graph to trace upstream anomalies
and calculate blast radius for downstream impact.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ..models import ImpactAnalysis, UpstreamAnomalyCause

logger = logging.getLogger(__name__)


class LineageAnalyzer:
    """
    Analyzes lineage relationships to find root causes.

    Traces upstream in the lineage graph to find earlier anomalies
    that may have propagated downstream.
    """

    def __init__(
        self,
        engine: Engine,
        max_depth: int = 5,
        lookback_window_hours: int = 24,
    ):
        """
        Initialize lineage analyzer.

        Args:
            engine: SQLAlchemy engine for querying
            max_depth: Maximum depth to traverse in lineage graph
            lookback_window_hours: Time window for finding anomalies
        """
        self.engine = engine
        self.max_depth = max_depth
        self.lookback_window_hours = lookback_window_hours

    def find_upstream_anomalies(
        self,
        table_name: str,
        database_name: Optional[str],
        schema_name: Optional[str],
        anomaly_timestamp: datetime,
        column_name: Optional[str] = None,
        metric_name: Optional[str] = None,
    ) -> List[UpstreamAnomalyCause]:
        """
        Find anomalies in upstream tables that may have caused this anomaly.

        Args:
            table_name: Name of affected table
            schema_name: Schema name
            anomaly_timestamp: When the anomaly occurred
            column_name: Affected column (if known)
            metric_name: Affected metric (if known)

        Returns:
            List of UpstreamAnomalyCause objects
        """
        # Get upstream tables from lineage
        upstream_tables = self._get_upstream_tables(table_name, database_name, schema_name)

        if not upstream_tables:
            logger.debug(f"No upstream tables found for {schema_name}.{table_name}")
            return []

        # Find anomalies in upstream tables
        causes = []
        time_window_start = anomaly_timestamp - timedelta(hours=self.lookback_window_hours)

        for upstream_table, distance in upstream_tables:
            upstream_schema, upstream_table_name = self._parse_table_identifier(upstream_table)

            # Query for anomalies in this upstream table
            upstream_anomalies = self._find_anomalies_in_table(
                upstream_table_name,
                upstream_schema,
                time_window_start,
                anomaly_timestamp,
            )

            for anomaly in upstream_anomalies:
                # Calculate confidence based on:
                # - Lineage distance (closer = higher confidence)
                # - Temporal proximity
                # - Column/metric match

                distance_score = self._calculate_distance_score(distance)
                temporal_score = self._calculate_temporal_score(
                    anomaly["timestamp"], anomaly_timestamp
                )

                # Column matching bonus
                column_match_score = 0.0
                if column_name and column_name == anomaly.get("column_name"):
                    column_match_score = 0.2

                # Metric matching bonus
                metric_match_score = 0.0
                if metric_name and metric_name == anomaly.get("metric_name"):
                    metric_match_score = 0.2

                confidence = (
                    (distance_score * 0.4)
                    + (temporal_score * 0.4)
                    + column_match_score
                    + metric_match_score
                )
                confidence = min(1.0, confidence)

                # Build description
                time_diff = (anomaly_timestamp - anomaly["timestamp"]).total_seconds() / 60
                description = (
                    f"Upstream anomaly in '{upstream_table_name}' "
                    f"({distance} hops away) detected {time_diff:.1f} minutes earlier"
                )

                if anomaly.get("column_name"):
                    description += f" in column '{anomaly['column_name']}'"
                if anomaly.get("metric_name"):
                    description += f" for metric '{anomaly['metric_name']}'"

                cause = UpstreamAnomalyCause(
                    cause_type="upstream_anomaly",
                    cause_id=anomaly.get("event_id", "unknown"),
                    upstream_table=upstream_table_name,
                    upstream_column=anomaly.get("column_name"),
                    upstream_metric=anomaly.get("metric_name"),
                    confidence_score=confidence,
                    lineage_distance=distance,
                    description=description,
                    affected_assets=[upstream_table],
                    suggested_action=(
                        f"Investigate anomaly in upstream table '{upstream_table_name}' "
                        f"which may have propagated to '{table_name}'"
                    ),
                    evidence={
                        "distance_score": distance_score,
                        "temporal_score": temporal_score,
                        "lineage_distance": distance,
                        "time_before_anomaly_minutes": time_diff,
                        "upstream_severity": anomaly.get("severity", "unknown"),
                    },
                )

                causes.append(cause)

        # Sort by confidence
        causes.sort(key=lambda c: c.confidence_score, reverse=True)
        return causes[:10]  # Return top 10

    def calculate_impact_analysis(
        self,
        table_name: str,
        database_name: Optional[str],
        schema_name: Optional[str],
    ) -> ImpactAnalysis:
        """
        Calculate impact/blast radius of an anomaly.

        Args:
            table_name: Name of affected table
            schema_name: Schema name

        Returns:
            ImpactAnalysis with upstream and downstream affected tables
        """
        # Get upstream tables
        upstream_tables = self._get_upstream_tables(table_name, database_name, schema_name)
        upstream_affected = [table for table, _ in upstream_tables]

        # Get downstream tables
        downstream_tables = self._get_downstream_tables(table_name, database_name, schema_name)
        downstream_affected = [table for table, _ in downstream_tables]

        # Calculate blast radius score
        # Based on number of affected downstream tables
        # and depth of dependency tree
        # total_affected = len(upstream_affected) + len(downstream_affected)  # Not used
        max_downstream_depth = max([depth for _, depth in downstream_tables], default=0)

        # Normalize to 0-1 scale
        # More downstream tables = higher blast radius
        blast_radius = min(1.0, (len(downstream_affected) * 0.1) + (max_downstream_depth * 0.1))

        return ImpactAnalysis(
            upstream_affected=upstream_affected,
            downstream_affected=downstream_affected,
            blast_radius_score=blast_radius,
        )

    def find_common_ancestors(
        self, table_names: List[str], schema_name: Optional[str]
    ) -> List[Tuple[str, int]]:
        """
        Find common upstream ancestors for multiple anomalous tables.

        Useful when multiple tables are anomalous - find their common root cause.

        Args:
            table_names: List of table names with anomalies
            schema_name: Schema name

        Returns:
            List of (table_name, distance) tuples for common ancestors
        """
        if not table_names:
            return []

        # Get upstream tables for each anomalous table
        all_upstream: List[Set[str]] = []

        for table_name in table_names:
            upstream = self._get_upstream_tables(table_name, None, schema_name)
            upstream_set = {table for table, _ in upstream}
            all_upstream.append(upstream_set)

        # Find intersection (common ancestors)
        if not all_upstream:
            return []

        common = all_upstream[0]
        for upstream_set in all_upstream[1:]:
            common = common.intersection(upstream_set)

        # Get distances for common ancestors (use minimum distance)
        common_with_distance = []
        for table in common:
            min_distance = float("inf")
            for table_name in table_names:
                upstream = self._get_upstream_tables(table_name, None, schema_name)
                for upstream_table, distance in upstream:
                    if upstream_table == table:
                        min_distance = min(min_distance, distance)
            common_with_distance.append((table, int(min_distance)))

        # Sort by distance (closest first)
        common_with_distance.sort(key=lambda x: x[1])

        return common_with_distance

    def _get_upstream_tables(
        self,
        table_name: str,
        database_name: Optional[str],
        schema_name: Optional[str],
    ) -> List[Tuple[str, int]]:
        """
        Get upstream tables from lineage (recursive).

        Args:
            table_name: Table name
            database_name: Database name (optional, for future use)
            schema_name: Schema name

        Returns:
            List of (table_identifier, distance) tuples
        """
        visited = set()
        upstream = []

        def traverse(current_table: str, current_schema: Optional[str], depth: int):
            if depth > self.max_depth:
                return

            table_id = f"{current_schema}.{current_table}" if current_schema else current_table
            if table_id in visited:
                return
            visited.add(table_id)

            # Query lineage table
            query = text(
                """
                SELECT DISTINCT upstream_schema, upstream_table
                FROM baselinr_lineage
                WHERE downstream_table = :table_name
                AND (downstream_schema = :schema_name OR :schema_name IS NULL)
            """
            )

            try:
                with self.engine.connect() as conn:
                    result = conn.execute(
                        query, {"table_name": current_table, "schema_name": current_schema}
                    )
                    rows = result.fetchall()

                    for row in rows:
                        upstream_schema = row[0]
                        upstream_table = row[1]
                        upstream_id = (
                            f"{upstream_schema}.{upstream_table}"
                            if upstream_schema
                            else upstream_table
                        )

                        if upstream_id not in visited:
                            upstream.append((upstream_id, depth))
                            traverse(upstream_table, upstream_schema, depth + 1)

            except Exception as e:
                logger.debug(f"Error querying lineage: {e}")

        traverse(table_name, schema_name, 1)
        return upstream

    def _get_downstream_tables(
        self,
        table_name: str,
        database_name: Optional[str],
        schema_name: Optional[str],
    ) -> List[Tuple[str, int]]:
        """
        Get downstream tables from lineage (recursive).

        Args:
            table_name: Table name
            database_name: Database name (optional, for future use)
            schema_name: Schema name

        Returns:
            List of (table_identifier, distance) tuples
        """
        visited = set()
        downstream = []

        def traverse(current_table: str, current_schema: Optional[str], depth: int):
            if depth > self.max_depth:
                return

            table_id = f"{current_schema}.{current_table}" if current_schema else current_table
            if table_id in visited:
                return
            visited.add(table_id)

            # Query lineage table
            query = text(
                """
                SELECT DISTINCT downstream_schema, downstream_table
                FROM baselinr_lineage
                WHERE upstream_table = :table_name
                AND (upstream_schema = :schema_name OR :schema_name IS NULL)
            """
            )

            try:
                with self.engine.connect() as conn:
                    result = conn.execute(
                        query, {"table_name": current_table, "schema_name": current_schema}
                    )
                    rows = result.fetchall()

                    for row in rows:
                        downstream_schema = row[0]
                        downstream_table = row[1]
                        downstream_id = (
                            f"{downstream_schema}.{downstream_table}"
                            if downstream_schema
                            else downstream_table
                        )

                        if downstream_id not in visited:
                            downstream.append((downstream_id, depth))
                            traverse(downstream_table, downstream_schema, depth + 1)

            except Exception as e:
                logger.debug(f"Error querying lineage: {e}")

        traverse(table_name, schema_name, 1)
        return downstream

    def _find_anomalies_in_table(
        self,
        table_name: str,
        schema_name: Optional[str],
        start_time: datetime,
        end_time: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Find anomalies in a specific table within time window.

        Args:
            table_name: Table name
            schema_name: Schema name
            start_time: Start of time window
            end_time: End of time window

        Returns:
            List of anomaly dictionaries
        """
        query = text(
            """
            SELECT event_id, event_type, table_name, column_name, metric_name,
                   current_value, drift_severity, timestamp
            FROM baselinr_events
            WHERE event_type = 'AnomalyDetected'
            AND table_name = :table_name
            AND (:schema_name IS NULL OR metadata LIKE :schema_pattern)
            AND timestamp >= :start_time
            AND timestamp <= :end_time
            ORDER BY timestamp ASC
        """
        )

        anomalies = []

        try:
            with self.engine.connect() as conn:
                schema_pattern = f"%{schema_name}%" if schema_name else "%"
                result = conn.execute(
                    query,
                    {
                        "table_name": table_name,
                        "schema_name": schema_name,
                        "schema_pattern": schema_pattern,
                        "start_time": start_time,
                        "end_time": end_time,
                    },
                )
                rows = result.fetchall()

                for row in rows:
                    anomalies.append(
                        {
                            "event_id": row[0],
                            "event_type": row[1],
                            "table_name": row[2],
                            "column_name": row[3],
                            "metric_name": row[4],
                            "current_value": row[5],
                            "severity": row[6],
                            "timestamp": row[7],
                        }
                    )

        except Exception as e:
            logger.error(f"Error finding anomalies in table {table_name}: {e}")

        return anomalies

    def _calculate_distance_score(self, distance: int) -> float:
        """
        Calculate score based on lineage distance.

        Closer tables get higher scores.

        Args:
            distance: Number of hops in lineage graph

        Returns:
            Score between 0 and 1
        """
        # Exponential decay with distance
        if distance <= 0:
            return 1.0

        # Direct parent (distance=1) gets high score
        # Each additional hop reduces score
        return 1.0 / (1 + distance * 0.5)

    def _calculate_temporal_score(
        self, upstream_time: datetime, downstream_time: datetime
    ) -> float:
        """
        Calculate temporal score for upstream anomaly.

        Upstream anomalies that occurred shortly before are more likely causes.

        Args:
            upstream_time: When upstream anomaly occurred
            downstream_time: When downstream anomaly occurred

        Returns:
            Score between 0 and 1
        """
        time_diff_hours = (downstream_time - upstream_time).total_seconds() / 3600

        # Upstream anomaly should be earlier
        if time_diff_hours < 0:
            return 0.0

        # Too long ago (beyond lookback window)
        if time_diff_hours > self.lookback_window_hours:
            return 0.0

        # Score decreases with time
        # Peak score for anomalies 0-2 hours before
        if time_diff_hours <= 2:
            return 1.0
        else:
            # Decay after 2 hours
            return max(0.0, 1.0 - ((time_diff_hours - 2) / self.lookback_window_hours))

    @staticmethod
    def _parse_table_identifier(table_id: str) -> Tuple[Optional[str], str]:
        """
        Parse table identifier into schema and table name.

        Args:
            table_id: Table identifier (schema.table or just table)

        Returns:
            Tuple of (schema_name, table_name)
        """
        if "." in table_id:
            parts = table_id.split(".", 1)
            return parts[0], parts[1]
        else:
            return None, table_id
