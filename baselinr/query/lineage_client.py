"""
Client for querying data lineage from storage.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class LineageQueryClient:
    """Client for querying lineage relationships."""

    def __init__(
        self,
        engine: Engine,
        lineage_table: str = "baselinr_lineage",
        warn_stale_days: Optional[int] = None,
    ):
        """
        Initialize lineage query client.

        Args:
            engine: SQLAlchemy engine
            lineage_table: Name of lineage table
            warn_stale_days: Days after which to warn about stale edges (default: 90)
        """
        self.engine = engine
        self.lineage_table = lineage_table
        self.warn_stale_days = warn_stale_days or 90

    def _check_staleness(self, edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Check for stale edges and add staleness metadata.

        Args:
            edges: List of edge dictionaries

        Returns:
            List of edges with staleness metadata added
        """
        if not edges:
            return edges

        stale_edges = []
        cutoff_date = datetime.utcnow() - timedelta(days=self.warn_stale_days)

        for edge in edges:
            # Check if this is a query history edge (has last_seen_at)
            last_seen_at = edge.get("last_seen_at")
            if last_seen_at:
                if isinstance(last_seen_at, str):
                    try:
                        last_seen_at = datetime.fromisoformat(last_seen_at.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        continue
                elif not isinstance(last_seen_at, datetime):
                    continue

                if last_seen_at < cutoff_date:
                    edge["is_stale"] = True
                    stale_edges.append(edge)
                else:
                    edge["is_stale"] = False
            else:
                # Not a query history edge, not considered stale
                edge["is_stale"] = False

        if stale_edges:
            logger.warning(
                f"Found {len(stale_edges)} stale lineage edges "
                f"(not seen in query history for >{self.warn_stale_days} days). "
                f"Consider running 'baselinr lineage sync' to refresh or "
                f"'baselinr lineage cleanup' to remove stale edges."
            )

        return edges

    def get_upstream_tables(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        max_depth: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get upstream dependencies for a table (recursive).

        Args:
            table_name: Name of the table
            schema_name: Optional schema name
            max_depth: Maximum depth to traverse (None = unlimited)

        Returns:
            List of upstream tables with depth information
        """
        visited = set()
        result = []

        def traverse_upstream(
            current_table: str, current_schema: Optional[str], current_depth: int
        ):
            if max_depth is not None and current_depth > max_depth:
                return

            key = (current_schema or "", current_table)
            if key in visited:
                return  # Avoid cycles
            visited.add(key)

            # Get direct upstream dependencies
            # Handle NULL schemas properly
            if current_schema:
                query = text(
                    f"""
                    SELECT upstream_schema, upstream_table, lineage_type, provider,
                           confidence_score, metadata, last_seen_at
                    FROM {self.lineage_table}
                    WHERE downstream_table = :table_name
                    AND (downstream_schema = :schema_name OR downstream_schema IS NULL)
                """
                )
                params = {"table_name": current_table, "schema_name": current_schema}
            else:
                query = text(
                    f"""
                    SELECT upstream_schema, upstream_table, lineage_type, provider,
                           confidence_score, metadata, last_seen_at
                    FROM {self.lineage_table}
                    WHERE downstream_table = :table_name
                    AND (downstream_schema IS NULL OR downstream_schema = '')
                """
                )
                params = {"table_name": current_table}

            with self.engine.connect() as conn:
                rows = conn.execute(query, params).fetchall()

            for row in rows:
                (
                    upstream_schema,
                    upstream_table,
                    lineage_type,
                    provider,
                    confidence,
                    metadata,
                    last_seen_at,
                ) = row

                upstream_info = {
                    "schema": upstream_schema or "",
                    "table": upstream_table,
                    "depth": current_depth,
                    "lineage_type": lineage_type,
                    "provider": provider,
                    "confidence_score": float(confidence) if confidence else 1.0,
                    "metadata": (
                        json.loads(metadata)
                        if metadata and isinstance(metadata, str)
                        else (metadata or {})
                    ),
                    "last_seen_at": last_seen_at,
                }
                result.append(upstream_info)

                # Recursively traverse upstream
                traverse_upstream(upstream_table, upstream_schema, current_depth + 1)

        traverse_upstream(table_name, schema_name, 0)
        result = self._check_staleness(result)
        return result

    def get_downstream_tables(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        max_depth: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get downstream dependencies for a table (recursive).

        Args:
            table_name: Name of the table
            schema_name: Optional schema name
            max_depth: Maximum depth to traverse (None = unlimited)

        Returns:
            List of downstream tables with depth information
        """
        visited = set()
        result = []

        def traverse_downstream(
            current_table: str, current_schema: Optional[str], current_depth: int
        ):
            if max_depth is not None and current_depth > max_depth:
                return

            key = (current_schema or "", current_table)
            if key in visited:
                return  # Avoid cycles
            visited.add(key)

            # Get direct downstream dependencies
            # Handle NULL schemas properly
            if current_schema:
                query = text(
                    f"""
                    SELECT downstream_schema, downstream_table, lineage_type, provider,
                           confidence_score, metadata, last_seen_at
                    FROM {self.lineage_table}
                    WHERE upstream_table = :table_name
                    AND (upstream_schema = :schema_name OR upstream_schema IS NULL)
                """
                )
                params = {"table_name": current_table, "schema_name": current_schema}
            else:
                query = text(
                    f"""
                    SELECT downstream_schema, downstream_table, lineage_type, provider,
                           confidence_score, metadata, last_seen_at
                    FROM {self.lineage_table}
                    WHERE upstream_table = :table_name
                    AND (upstream_schema IS NULL OR upstream_schema = '')
                """
                )
                params = {"table_name": current_table}

            with self.engine.connect() as conn:
                rows = conn.execute(query, params).fetchall()

            for row in rows:
                (
                    downstream_schema,
                    downstream_table,
                    lineage_type,
                    provider,
                    confidence,
                    metadata,
                    last_seen_at,
                ) = row

                downstream_info = {
                    "schema": downstream_schema or "",
                    "table": downstream_table,
                    "depth": current_depth,
                    "lineage_type": lineage_type,
                    "provider": provider,
                    "confidence_score": float(confidence) if confidence else 1.0,
                    "metadata": (
                        json.loads(metadata)
                        if metadata and isinstance(metadata, str)
                        else (metadata or {})
                    ),
                    "last_seen_at": last_seen_at,
                }
                result.append(downstream_info)

                # Recursively traverse downstream
                traverse_downstream(downstream_table, downstream_schema, current_depth + 1)

        traverse_downstream(table_name, schema_name, 0)
        result = self._check_staleness(result)
        return result

    def get_lineage_path(
        self,
        from_table: str,
        to_table: str,
        from_schema: Optional[str] = None,
        to_schema: Optional[str] = None,
        max_depth: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find path between two tables.

        Args:
            from_table: Source table name
            to_table: Target table name
            from_schema: Optional source schema
            to_schema: Optional target schema
            max_depth: Maximum depth to search (None = unlimited)

        Returns:
            List of tables in the path, or empty list if no path found
        """
        # Use BFS to find shortest path
        from collections import deque

        queue: deque = deque([(from_table, from_schema, [])])
        visited = set()

        while queue:
            current_table, current_schema, path = queue.popleft()

            if max_depth is not None and len(path) >= max_depth:
                continue

            key = (current_schema or "", current_table)
            if key in visited:
                continue
            visited.add(key)

            # Check if we reached the target
            if current_table == to_table and (to_schema is None or current_schema == to_schema):
                result_path: List[Dict[str, Any]] = path + [
                    {"schema": current_schema or "", "table": current_table}
                ]
                return result_path

            # Get downstream tables
            # Handle NULL schemas properly
            if current_schema:
                query = text(
                    f"""
                    SELECT downstream_schema, downstream_table, lineage_type, provider
                    FROM {self.lineage_table}
                    WHERE upstream_table = :table_name
                    AND (upstream_schema = :schema_name OR upstream_schema IS NULL)
                """
                )
                params = {"table_name": current_table, "schema_name": current_schema}
            else:
                query = text(
                    f"""
                    SELECT downstream_schema, downstream_table, lineage_type, provider
                    FROM {self.lineage_table}
                    WHERE upstream_table = :table_name
                    AND (upstream_schema IS NULL OR upstream_schema = '')
                """
                )
                params = {"table_name": current_table}

            with self.engine.connect() as conn:
                rows = conn.execute(query, params).fetchall()

            for row in rows:
                downstream_schema, downstream_table, lineage_type, provider = row
                queue.append(
                    (
                        downstream_table,
                        downstream_schema,
                        path + [{"schema": current_schema or "", "table": current_table}],
                    )
                )

        return []  # No path found

    def get_all_lineage(self) -> Dict[str, List[str]]:
        """
        Get complete lineage graph.

        Returns:
            Dictionary mapping downstream tables to lists of upstream tables
        """
        query = text(
            f"""
            SELECT downstream_schema, downstream_table, upstream_schema, upstream_table
            FROM {self.lineage_table}
            ORDER BY downstream_schema, downstream_table
        """
        )

        result: Dict[str, List[str]] = {}
        with self.engine.connect() as conn:
            rows = conn.execute(query).fetchall()

        for row in rows:
            downstream_schema, downstream_table, upstream_schema, upstream_table = row
            downstream_key = f"{downstream_schema or ''}.{downstream_table}"
            upstream_key = f"{upstream_schema or ''}.{upstream_table}"

            if downstream_key not in result:
                result[downstream_key] = []
            result[downstream_key].append(upstream_key)

        return result

    def get_lineage_by_provider(self, provider: str) -> Dict[str, List[str]]:
        """
        Get lineage filtered by provider.

        Args:
            provider: Provider name (e.g., 'dbt', 'sql_parser')

        Returns:
            Dictionary mapping downstream tables to lists of upstream tables
        """
        query = text(
            f"""
            SELECT downstream_schema, downstream_table, upstream_schema, upstream_table
            FROM {self.lineage_table}
            WHERE provider = :provider
            ORDER BY downstream_schema, downstream_table
        """
        )

        result: Dict[str, List[str]] = {}
        with self.engine.connect() as conn:
            rows = conn.execute(query, {"provider": provider}).fetchall()

        for row in rows:
            downstream_schema, downstream_table, upstream_schema, upstream_table = row
            downstream_key = f"{downstream_schema or ''}.{downstream_table}"
            upstream_key = f"{upstream_schema or ''}.{upstream_table}"

            if downstream_key not in result:
                result[downstream_key] = []
            result[downstream_key].append(upstream_key)

        return result
