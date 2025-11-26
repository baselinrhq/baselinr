"""
Base query history lineage provider for Baselinr.

Provides common functionality for extracting lineage from warehouse query history.
"""

import logging
import re
from abc import abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.engine import Engine

from .base import ColumnLineageEdge, LineageEdge, LineageProvider
from .sql_provider import SQLLineageProvider

logger = logging.getLogger(__name__)


class QueryHistoryLineageProvider(LineageProvider):
    """
    Abstract base class for query history lineage providers.

    Provides common functionality for extracting lineage from warehouse query history,
    including SQL parsing, sync timestamp tracking, and incremental updates.
    """

    def __init__(
        self,
        source_engine: Optional[Engine] = None,
        config: Optional[Dict[str, Any]] = None,
        sync_tracker=None,
    ):
        """
        Initialize query history provider.

        Args:
            source_engine: SQLAlchemy engine for source database
            config: Provider-specific configuration
            sync_tracker: Optional sync timestamp tracker
        """
        self.source_engine = source_engine
        self.config = config or {}
        self.sync_tracker = sync_tracker
        self.sql_provider = SQLLineageProvider(engine=source_engine)

        # Configuration defaults
        self.lookback_days = self.config.get("lookback_days", 30)
        self.incremental = self.config.get("incremental", True)
        self.min_query_count = self.config.get("min_query_count", 1)
        self.exclude_patterns = self.config.get("exclude_patterns", [])

    @abstractmethod
    def _query_access_history(
        self, since_timestamp: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Query warehouse-specific query history.

        Args:
            since_timestamp: Optional timestamp to query only queries since this time

        Returns:
            List of query history records (warehouse-specific format)
        """
        pass

    @abstractmethod
    def _parse_query_result(
        self, query_record: Dict[str, Any]
    ) -> Tuple[str, datetime, List[Tuple[str, str, Optional[str]]]]:
        """
        Parse warehouse-specific query result format.

        Args:
            query_record: Single query history record

        Returns:
            Tuple of (query_text, query_timestamp, table_references)
            where table_references is list of (schema, table, database) tuples
        """
        pass

    def _get_last_sync_timestamp(self) -> Optional[datetime]:
        """
        Get last sync timestamp from sync tracker.

        Returns:
            Last sync timestamp or None if never synced
        """
        if self.sync_tracker:
            timestamp = self.sync_tracker.get_last_sync(self.get_provider_name())
            if isinstance(timestamp, datetime):
                return timestamp
        return None

    def _update_sync_timestamp(
        self, timestamp: datetime, query_count: int = 0, edge_count: int = 0
    ):
        """
        Update last sync timestamp in sync tracker.

        Args:
            timestamp: Sync timestamp
            query_count: Number of queries processed
            edge_count: Number of edges extracted
        """
        if self.sync_tracker:
            self.sync_tracker.update_sync(
                self.get_provider_name(), timestamp, query_count, edge_count
            )

    def _should_exclude_query(self, query_text: str) -> bool:
        """
        Check if query should be excluded based on patterns.

        Args:
            query_text: Query text to check

        Returns:
            True if query should be excluded
        """
        if not self.exclude_patterns:
            return False

        for pattern in self.exclude_patterns:
            try:
                if re.search(pattern, query_text, re.IGNORECASE):
                    return True
            except re.error:
                logger.warning(f"Invalid regex pattern: {pattern}")
        return False

    def _extract_lineage_from_queries(self, queries: List[Dict[str, Any]]) -> List[LineageEdge]:
        """
        Extract lineage edges from list of query records.

        Args:
            queries: List of query history records

        Returns:
            List of LineageEdge objects
        """
        edges = []
        query_relationships: Dict[Tuple[str, str, Optional[str], str, str, Optional[str]], int] = {}

        for query_record in queries:
            try:
                query_text, query_timestamp, table_refs = self._parse_query_result(query_record)

                if self._should_exclude_query(query_text):
                    continue

                if len(table_refs) < 2:
                    # Need at least 2 tables for a relationship
                    continue

                # Extract relationships: downstream is typically the first table (destination),
                # upstream tables are sources
                # For now, we'll create relationships between all pairs
                # More sophisticated logic can be added per warehouse
                for i, downstream_ref in enumerate(table_refs):
                    for upstream_ref in table_refs[i + 1 :]:
                        # Create edge: downstream -> upstream
                        key = (
                            downstream_ref[0],  # downstream_schema
                            downstream_ref[1],  # downstream_table
                            downstream_ref[2],  # downstream_database
                            upstream_ref[0],  # upstream_schema
                            upstream_ref[1],  # upstream_table
                            upstream_ref[2],  # upstream_database
                        )
                        query_relationships[key] = query_relationships.get(key, 0) + 1

            except Exception as e:
                logger.debug(f"Error processing query record: {e}")
                continue

        # Create edges for relationships that meet min_query_count threshold
        for (
            down_schema,
            down_table,
            down_db,
            up_schema,
            up_table,
            up_db,
        ), count in query_relationships.items():
            if count >= self.min_query_count:
                edge = LineageEdge(
                    downstream_schema=down_schema or "",
                    downstream_table=down_table,
                    upstream_schema=up_schema or "",
                    upstream_table=up_table,
                    downstream_database=down_db,
                    upstream_database=up_db,
                    lineage_type="query_history",
                    provider=self.get_provider_name(),
                    confidence_score=0.95,  # Query history has high confidence
                    metadata={"query_count": count, "last_seen_at": datetime.utcnow().isoformat()},
                )
                edges.append(edge)

        return edges

    def extract_lineage(self, table_name: str, schema: Optional[str] = None) -> List[LineageEdge]:
        """
        Extract lineage incrementally (queries only since last sync).

        Args:
            table_name: Name of the table (not used for query history, but required by interface)
            schema: Optional schema name (not used for query history, but required by interface)

        Returns:
            List of LineageEdge objects
        """
        if not self.incremental:
            # If incremental is disabled, return empty (use get_all_lineage instead)
            return []

        last_sync = self._get_last_sync_timestamp()

        if last_sync:
            # Query only queries since last sync
            queries = self._query_access_history(since_timestamp=last_sync)
        else:
            # First run: query full lookback window
            since_timestamp = datetime.utcnow() - timedelta(days=self.lookback_days)
            queries = self._query_access_history(since_timestamp=since_timestamp)

        if not queries:
            return []

        edges = self._extract_lineage_from_queries(queries)

        # Update sync timestamp after successful extraction
        if edges:
            self._update_sync_timestamp(datetime.utcnow(), len(queries), len(edges))

        return edges

    def get_all_lineage(self) -> Dict[str, List[LineageEdge]]:
        """
        Extract all lineage from query history (bulk operation).

        Queries full lookback window, ignoring last sync timestamp.

        Returns:
            Dictionary mapping table identifiers to lists of LineageEdge objects
        """
        # Query full lookback window
        since_timestamp = datetime.utcnow() - timedelta(days=self.lookback_days)
        queries = self._query_access_history(since_timestamp=since_timestamp)

        if not queries:
            return {}

        edges = self._extract_lineage_from_queries(queries)

        # Group edges by downstream table
        result: Dict[str, List[LineageEdge]] = {}
        for edge in edges:
            table_key = (
                f"{edge.downstream_database or ''}.{edge.downstream_schema}.{edge.downstream_table}"
            )
            if table_key not in result:
                result[table_key] = []
            result[table_key].append(edge)

        # Update sync timestamp to current time (marks as fully synced)
        self._update_sync_timestamp(datetime.utcnow(), len(queries), len(edges))

        return result

    def _extract_column_lineage_from_queries(
        self, queries: List[Dict[str, Any]]
    ) -> List[ColumnLineageEdge]:
        """
        Extract column-level lineage edges from list of query records.

        Args:
            queries: List of query history records

        Returns:
            List of ColumnLineageEdge objects
        """
        column_edges: List[ColumnLineageEdge] = []

        for query_record in queries:
            try:
                query_text, query_timestamp, table_refs = self._parse_query_result(query_record)

                if self._should_exclude_query(query_text):
                    continue

                if len(table_refs) < 1:
                    # Need at least 1 table for column lineage
                    continue

                # Use SQL provider to extract column-level lineage from query
                # We'll try to infer the output table from the query
                # For INSERT/SELECT INTO, the output table is the target
                # For CREATE TABLE AS SELECT, the output table is the created table
                # For now, we'll extract column mappings from SELECT statements
                try:
                    # Parse query to extract column mappings
                    # Use SQL provider's column extraction
                    column_mappings = self.sql_provider.extract_column_references(
                        query_text,
                        default_database=query_record.get("database"),
                        default_schema="public",
                    )

                    # Group columns by table to infer relationships
                    # This is a simplified approach - a more complete implementation
                    # would parse the full SELECT statement to map output to input columns
                    for schema, table, column, database in column_mappings:
                        # For now, create relationships between columns in the same query
                        # A more sophisticated approach would parse SELECT expressions
                        # This is a placeholder - full implementation would use
                        # extract_column_lineage_from_sql from SQL provider
                        pass

                except Exception as e:
                    logger.debug(f"Error extracting column lineage from query: {e}")
                    continue

            except Exception as e:
                logger.debug(f"Error processing query record for column lineage: {e}")
                continue

        # For now, return empty list
        # Full implementation would parse SELECT statements to extract column mappings
        # This requires more sophisticated SQL parsing to map output columns to input columns
        return column_edges

    def extract_column_lineage(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[ColumnLineageEdge]:
        """
        Extract column-level lineage incrementally (queries only since last sync).

        Args:
            table_name: Name of the table (not used for query history, but required by interface)
            schema: Optional schema name (not used for query history, but required by interface)

        Returns:
            List of ColumnLineageEdge objects
        """
        # For now, return empty list
        # Column-level lineage from query history requires more sophisticated
        # SQL parsing to map output columns to input columns from SELECT statements
        # This can be enhanced in the future
        return []
