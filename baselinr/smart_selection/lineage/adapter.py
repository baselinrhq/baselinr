"""
Adapter to interface with baselinr's existing lineage system.

Provides a clean interface for querying lineage data and building
dependency graphs for impact analysis.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def _parse_metadata(metadata: Any) -> Dict[str, Any]:
    """
    Parse metadata from database, handling both JSON strings and dicts.

    Args:
        metadata: Metadata value from database (can be str, dict, or None)

    Returns:
        Parsed metadata as dict, or empty dict if parsing fails
    """
    if metadata is None:
        return {}
    if isinstance(metadata, dict):
        return metadata
    if isinstance(metadata, str):
        try:
            return json.loads(metadata) if metadata else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


@dataclass
class TableInfo:
    """Information about a table in the lineage graph."""

    table: str
    schema: Optional[str] = None
    database: Optional[str] = None
    node_type: str = "unknown"  # source, staging, intermediate, mart, exposure
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def fully_qualified_name(self) -> str:
        """Get fully qualified table name."""
        parts = []
        if self.database:
            parts.append(self.database)
        if self.schema:
            parts.append(self.schema)
        parts.append(self.table)
        return ".".join(parts)


@dataclass
class ExposureInfo:
    """Information about a downstream exposure (dashboard, report, etc.)."""

    name: str
    exposure_type: str  # dashboard, notebook, report, ml_model, application
    owner: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class LineageAdapter:
    """
    Adapter to baselinr's existing lineage system.

    Provides operations for querying lineage relationships and building
    dependency graphs for smart selection prioritization.
    """

    def __init__(
        self,
        engine: Engine,
        lineage_table: str = "baselinr_lineage",
        cache_ttl_hours: int = 24,
        max_depth: int = 10,
    ):
        """
        Initialize lineage adapter.

        Args:
            engine: SQLAlchemy engine for querying lineage data
            lineage_table: Name of the lineage table
            cache_ttl_hours: Cache time-to-live in hours
            max_depth: Maximum depth for recursive queries
        """
        self.engine = engine
        self.lineage_table = lineage_table
        self.cache_ttl_hours = cache_ttl_hours
        self.max_depth = max_depth

        # In-memory cache for computed metrics
        self._cache: Dict[str, Any] = {}
        self._cache_timestamp: Optional[datetime] = None

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cache_timestamp is None:
            return False
        ttl = timedelta(hours=self.cache_ttl_hours)
        return datetime.now(timezone.utc) - self._cache_timestamp < ttl

    def _invalidate_cache(self) -> None:
        """Invalidate the cache."""
        self._cache = {}
        self._cache_timestamp = None

    def refresh_cache(self) -> None:
        """Manually refresh the cache by invalidating it."""
        self._invalidate_cache()
        logger.info("Lineage cache invalidated")

    def has_lineage_data(self, table: str, schema: Optional[str] = None) -> bool:
        """
        Check if lineage data exists for a table.

        Args:
            table: Table name
            schema: Optional schema name

        Returns:
            True if lineage data exists
        """
        if schema:
            query = text(
                f"""
                SELECT 1 FROM {self.lineage_table}
                WHERE (downstream_table = :table AND downstream_schema = :schema)
                   OR (upstream_table = :table AND upstream_schema = :schema)
                LIMIT 1
            """
            )
            params = {"table": table, "schema": schema}
        else:
            query = text(
                f"""
                SELECT 1 FROM {self.lineage_table}
                WHERE downstream_table = :table OR upstream_table = :table
                LIMIT 1
            """
            )
            params = {"table": table}

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params)
                return result.fetchone() is not None
        except Exception as e:
            logger.debug(f"Error checking lineage data: {e}")
            return False

    def get_upstream_tables(
        self,
        table: str,
        schema: Optional[str] = None,
        recursive: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get all upstream dependencies for a table.

        Args:
            table: Table name
            schema: Optional schema name
            recursive: If True, get all transitive upstream dependencies

        Returns:
            List of upstream tables with depth information
        """
        if not recursive:
            return self._get_direct_upstream(table, schema)

        visited: Set[Tuple[Optional[str], str]] = set()
        result: List[Dict[str, Any]] = []

        def traverse(current_table: str, current_schema: Optional[str], depth: int):
            if depth > self.max_depth:
                return

            key = (current_schema or "", current_table)
            if key in visited:
                return
            visited.add(key)

            upstream = self._get_direct_upstream(current_table, current_schema)
            for item in upstream:
                item["depth"] = depth
                result.append(item)
                traverse(item["table"], item.get("schema"), depth + 1)

        traverse(table, schema, 1)
        return result

    def _get_direct_upstream(
        self, table: str, schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get direct upstream dependencies (non-recursive)."""
        if schema:
            query = text(
                f"""
                SELECT upstream_schema, upstream_table, upstream_database,
                       lineage_type, provider, confidence_score, metadata
                FROM {self.lineage_table}
                WHERE downstream_table = :table
                AND (downstream_schema = :schema OR downstream_schema IS NULL)
            """
            )
            params = {"table": table, "schema": schema}
        else:
            query = text(
                f"""
                SELECT upstream_schema, upstream_table, upstream_database,
                       lineage_type, provider, confidence_score, metadata
                FROM {self.lineage_table}
                WHERE downstream_table = :table
            """
            )
            params = {"table": table}

        result = []
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(query, params).fetchall()

            for row in rows:
                result.append(
                    {
                        "schema": row[0] or "",
                        "table": row[1],
                        "database": row[2],
                        "lineage_type": row[3],
                        "provider": row[4],
                        "confidence_score": float(row[5]) if row[5] else 1.0,
                        "metadata": _parse_metadata(row[6]),
                        "depth": 0,
                    }
                )
        except Exception as e:
            logger.debug(f"Error getting upstream tables: {e}")

        return result

    def get_downstream_tables(
        self,
        table: str,
        schema: Optional[str] = None,
        recursive: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get all downstream dependencies for a table.

        Args:
            table: Table name
            schema: Optional schema name
            recursive: If True, get all transitive downstream dependencies

        Returns:
            List of downstream tables with depth information
        """
        if not recursive:
            return self._get_direct_downstream(table, schema)

        visited: Set[Tuple[Optional[str], str]] = set()
        result: List[Dict[str, Any]] = []

        def traverse(current_table: str, current_schema: Optional[str], depth: int):
            if depth > self.max_depth:
                return

            key = (current_schema or "", current_table)
            if key in visited:
                return
            visited.add(key)

            downstream = self._get_direct_downstream(current_table, current_schema)
            for item in downstream:
                item["depth"] = depth
                result.append(item)
                traverse(item["table"], item.get("schema"), depth + 1)

        traverse(table, schema, 1)
        return result

    def _get_direct_downstream(
        self, table: str, schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get direct downstream dependencies (non-recursive)."""
        if schema:
            query = text(
                f"""
                SELECT downstream_schema, downstream_table, downstream_database,
                       lineage_type, provider, confidence_score, metadata
                FROM {self.lineage_table}
                WHERE upstream_table = :table
                AND (upstream_schema = :schema OR upstream_schema IS NULL)
            """
            )
            params = {"table": table, "schema": schema}
        else:
            query = text(
                f"""
                SELECT downstream_schema, downstream_table, downstream_database,
                       lineage_type, provider, confidence_score, metadata
                FROM {self.lineage_table}
                WHERE upstream_table = :table
            """
            )
            params = {"table": table}

        result = []
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(query, params).fetchall()

            for row in rows:
                result.append(
                    {
                        "schema": row[0] or "",
                        "table": row[1],
                        "database": row[2],
                        "lineage_type": row[3],
                        "provider": row[4],
                        "confidence_score": float(row[5]) if row[5] else 1.0,
                        "metadata": _parse_metadata(row[6]),
                        "depth": 0,
                    }
                )
        except Exception as e:
            logger.debug(f"Error getting downstream tables: {e}")

        return result

    def get_table_metadata(self, table: str, schema: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metadata about a table from the lineage system.

        Args:
            table: Table name
            schema: Optional schema name

        Returns:
            Dictionary of metadata
        """
        # Aggregate metadata from all lineage edges involving this table
        if schema:
            query = text(
                f"""
                SELECT metadata, lineage_type, provider
                FROM {self.lineage_table}
                WHERE (downstream_table = :table AND downstream_schema = :schema)
                   OR (upstream_table = :table AND upstream_schema = :schema)
            """
            )
            params = {"table": table, "schema": schema}
        else:
            query = text(
                f"""
                SELECT metadata, lineage_type, provider
                FROM {self.lineage_table}
                WHERE downstream_table = :table OR upstream_table = :table
            """
            )
            params = {"table": table}

        metadata: Dict[str, Any] = {
            "lineage_types": set(),
            "providers": set(),
        }

        try:
            with self.engine.connect() as conn:
                rows = conn.execute(query, params).fetchall()

            for row in rows:
                if row[0]:
                    # Merge metadata from edges
                    if isinstance(row[0], dict):
                        for key, value in row[0].items():
                            if key not in metadata:
                                metadata[key] = value
                if row[1]:
                    metadata["lineage_types"].add(row[1])
                if row[2]:
                    metadata["providers"].add(row[2])

            # Convert sets to lists for JSON serialization
            metadata["lineage_types"] = list(metadata["lineage_types"])
            metadata["providers"] = list(metadata["providers"])

        except Exception as e:
            logger.debug(f"Error getting table metadata: {e}")

        return metadata

    def get_all_tables_with_lineage(self) -> List[Dict[str, Any]]:
        """
        Get all tables that have lineage information.

        Returns:
            List of table identifiers with basic info
        """
        cache_key = "all_tables_with_lineage"
        if self._is_cache_valid() and cache_key in self._cache:
            result: List[Dict[str, Any]] = self._cache[cache_key]
            return result

        query = text(
            f"""
            SELECT DISTINCT schema_name, table_name, database_name
            FROM (
                SELECT downstream_schema AS schema_name,
                       downstream_table AS table_name,
                       downstream_database AS database_name
                FROM {self.lineage_table}
                UNION
                SELECT upstream_schema AS schema_name,
                       upstream_table AS table_name,
                       upstream_database AS database_name
                FROM {self.lineage_table}
            ) AS all_tables
            ORDER BY schema_name, table_name
        """
        )

        result = []
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(query).fetchall()

            for row in rows:
                result.append(
                    {
                        "schema": row[0] or "",
                        "table": row[1],
                        "database": row[2],
                    }
                )

            # Update cache
            self._cache[cache_key] = result
            if self._cache_timestamp is None:
                self._cache_timestamp = datetime.now(timezone.utc)

        except Exception as e:
            logger.debug(f"Error getting all tables with lineage: {e}")

        return result

    def get_exposures(self, table: str, schema: Optional[str] = None) -> List[ExposureInfo]:
        """
        Get downstream exposures (dashboards, reports) for a table.

        Exposures are identified from lineage metadata where the node_type
        indicates a BI tool, dashboard, or report destination.

        Args:
            table: Table name
            schema: Optional schema name

        Returns:
            List of ExposureInfo objects
        """
        # Get all downstream tables recursively
        downstream = self.get_downstream_tables(table, schema, recursive=True)

        exposures = []
        exposure_types = {"dashboard", "notebook", "report", "ml_model", "application", "exposure"}

        for item in downstream:
            metadata = item.get("metadata", {})
            lineage_type = item.get("lineage_type", "")
            node_type = metadata.get("node_type", "").lower()

            # Check if this is an exposure
            if node_type in exposure_types or lineage_type in exposure_types:
                exposure = ExposureInfo(
                    name=f"{item.get('schema', '')}.{item['table']}",
                    exposure_type=node_type or lineage_type or "exposure",
                    owner=metadata.get("owner"),
                    url=metadata.get("url"),
                    description=metadata.get("description"),
                    depends_on=[f"{schema}.{table}" if schema else table],
                    metadata=metadata,
                )
                exposures.append(exposure)

        return exposures

    def get_lineage_subgraph(
        self,
        table: str,
        schema: Optional[str] = None,
        depth: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get a subgraph of lineage centered on a specific table.

        Args:
            table: Table name
            schema: Optional schema name
            depth: Maximum depth to traverse (None = use adapter's max_depth)

        Returns:
            Dictionary containing nodes and edges of the subgraph
        """
        actual_depth = depth or self.max_depth

        # Temporarily adjust max_depth for this query
        original_max_depth = self.max_depth
        self.max_depth = actual_depth

        try:
            upstream = self.get_upstream_tables(table, schema, recursive=True)
            downstream = self.get_downstream_tables(table, schema, recursive=True)
        finally:
            self.max_depth = original_max_depth

        # Build node and edge lists
        nodes: Dict[str, Dict[str, Any]] = {}
        edges: List[Dict[str, str]] = []

        # Add center node
        center_key = f"{schema}.{table}" if schema else table
        nodes[center_key] = {
            "table": table,
            "schema": schema or "",
            "is_center": True,
            "depth": 0,
        }

        # Add upstream nodes
        for item in upstream:
            key = f"{item.get('schema', '')}.{item['table']}"
            if key not in nodes:
                nodes[key] = {
                    "table": item["table"],
                    "schema": item.get("schema", ""),
                    "is_upstream": True,
                    "depth": -item["depth"],  # Negative depth for upstream
                    "metadata": item.get("metadata", {}),
                }
            edges.append({"from": key, "to": center_key})

        # Add downstream nodes
        for item in downstream:
            key = f"{item.get('schema', '')}.{item['table']}"
            if key not in nodes:
                nodes[key] = {
                    "table": item["table"],
                    "schema": item.get("schema", ""),
                    "is_downstream": True,
                    "depth": item["depth"],
                    "metadata": item.get("metadata", {}),
                }
            edges.append({"from": center_key, "to": key})

        return {
            "center": center_key,
            "nodes": nodes,
            "edges": edges,
            "upstream_count": len(upstream),
            "downstream_count": len(downstream),
        }

    def get_all_edges(self) -> List[Dict[str, Any]]:
        """
        Get all lineage edges for graph construction.

        Returns:
            List of edge dictionaries
        """
        cache_key = "all_edges"
        if self._is_cache_valid() and cache_key in self._cache:
            result: List[Dict[str, Any]] = self._cache[cache_key]
            return result

        query = text(
            f"""
            SELECT downstream_schema, downstream_table, downstream_database,
                   upstream_schema, upstream_table, upstream_database,
                   lineage_type, provider, confidence_score, metadata
            FROM {self.lineage_table}
        """
        )

        result = []
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(query).fetchall()

            for row in rows:
                result.append(
                    {
                        "downstream_schema": row[0] or "",
                        "downstream_table": row[1],
                        "downstream_database": row[2],
                        "upstream_schema": row[3] or "",
                        "upstream_table": row[4],
                        "upstream_database": row[5],
                        "lineage_type": row[6],
                        "provider": row[7],
                        "confidence_score": float(row[8]) if row[8] else 1.0,
                        "metadata": _parse_metadata(row[9]),
                    }
                )

            # Update cache
            self._cache[cache_key] = result
            if self._cache_timestamp is None:
                self._cache_timestamp = datetime.now(timezone.utc)

        except Exception as e:
            logger.debug(f"Error getting all edges: {e}")

        return result

    def get_lineage_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the lineage data.

        Returns:
            Dictionary with lineage statistics
        """
        cache_key = "lineage_stats"
        if self._is_cache_valid() and cache_key in self._cache:
            cached_stats: Dict[str, Any] = self._cache[cache_key]
            return cached_stats

        # Count edges
        edge_query = text(f"SELECT COUNT(*) FROM {self.lineage_table}")

        # Count distinct tables
        table_query = text(
            f"""
            SELECT COUNT(DISTINCT table_id) FROM (
                SELECT downstream_schema || '.' || downstream_table AS table_id
                FROM {self.lineage_table}
                UNION
                SELECT upstream_schema || '.' || upstream_table AS table_id
                FROM {self.lineage_table}
            ) AS t
        """
        )

        # Count by provider
        provider_query = text(
            f"""
            SELECT provider, COUNT(*) AS cnt
            FROM {self.lineage_table}
            GROUP BY provider
        """
        )

        stats: Dict[str, Any] = {
            "total_edges": 0,
            "total_tables": 0,
            "edges_by_provider": {},
        }

        try:
            with self.engine.connect() as conn:
                # Edge count
                result = conn.execute(edge_query)
                row = result.fetchone()
                if row:
                    stats["total_edges"] = row[0]

                # Table count
                try:
                    result = conn.execute(table_query)
                    row = result.fetchone()
                    if row:
                        stats["total_tables"] = row[0]
                except Exception:
                    # Fallback for databases that don't support this syntax
                    tables = self.get_all_tables_with_lineage()
                    stats["total_tables"] = len(tables)

                # Provider counts
                result = conn.execute(provider_query)
                for row in result:
                    stats["edges_by_provider"][row[0] or "unknown"] = row[1]

            # Update cache
            self._cache[cache_key] = stats
            if self._cache_timestamp is None:
                self._cache_timestamp = datetime.now(timezone.utc)

        except Exception as e:
            logger.debug(f"Error getting lineage stats: {e}")

        return stats
