"""
Redshift query history lineage provider.

Extracts lineage from STL_QUERY and STL_SCAN tables.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text

from .query_history_provider import QueryHistoryLineageProvider

logger = logging.getLogger(__name__)


class RedshiftQueryHistoryProvider(QueryHistoryLineageProvider):
    """Lineage provider that extracts dependencies from Redshift query history."""

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "redshift_query_history"

    def is_available(self) -> bool:
        """
        Check if STL_QUERY is available.

        Returns:
            True if STL_QUERY can be queried
        """
        if not self.source_engine:
            return False

        try:
            if self.source_engine is None:
                return False
            with self.source_engine.connect() as conn:
                conn.execute(text("SELECT 1 FROM stl_query LIMIT 1"))
                return True
        except Exception as e:
            logger.debug(f"STL_QUERY not available: {e}")
            return False

    def _query_access_history(
        self, since_timestamp: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Query Redshift's STL_QUERY and STL_SCAN tables.

        Args:
            since_timestamp: Optional timestamp to query only queries since this time

        Returns:
            List of query history records
        """
        if not self.is_available():
            return []

        if not self.source_engine:
            return []

        try:
            with self.source_engine.connect() as conn:
                if since_timestamp:
                    # Incremental query
                    query = text(
                        """
                        SELECT DISTINCT
                            q.query,
                            q.starttime,
                            q.querytxt,
                            s.schema,
                            s.table,
                            s.database
                        FROM stl_query q
                        LEFT JOIN stl_scan s ON q.query = s.query
                        WHERE q.starttime >= :since_timestamp
                          AND q.querytxt IS NOT NULL
                          AND q.aborted = 0
                        ORDER BY q.starttime DESC
                        """
                    )
                    result = conn.execute(query, {"since_timestamp": since_timestamp})
                else:
                    # Bulk query with lookback
                    lookback_timestamp = datetime.utcnow() - timedelta(days=self.lookback_days)
                    query = text(
                        """
                        SELECT DISTINCT
                            q.query,
                            q.starttime,
                            q.querytxt,
                            s.schema,
                            s.table,
                            s.database
                        FROM stl_query q
                        LEFT JOIN stl_scan s ON q.query = s.query
                        WHERE q.starttime >= :lookback_timestamp
                          AND q.querytxt IS NOT NULL
                          AND q.aborted = 0
                        ORDER BY q.starttime DESC
                        """
                    )
                    result = conn.execute(query, {"lookback_timestamp": lookback_timestamp})

                records = []
                current_query = None
                current_record = None

                for row in result:
                    query_id = row[0]
                    if query_id != current_query:
                        # New query - save previous record if exists
                        if current_record:
                            records.append(current_record)

                        # Start new record
                        current_query = query_id
                        current_record = {
                            "query": query_id,
                            "starttime": row[1],
                            "querytxt": row[2],
                            "tables": [],
                        }

                    # Add table reference from STL_SCAN
                    if row[3] and row[4] and current_record:  # schema and table are not None
                        table_ref = {
                            "schema": row[3],
                            "table": row[4],
                            "database": row[5],
                        }
                        if current_record and table_ref not in current_record["tables"]:
                            current_record["tables"].append(table_ref)

                # Add last record
                if current_record:
                    records.append(current_record)

                return records
        except Exception as e:
            logger.warning(f"Error querying Redshift STL_QUERY: {e}")
            return []

    def _parse_query_result(
        self, query_record: Dict[str, Any]
    ) -> Tuple[str, datetime, List[Tuple[str, str, Optional[str]]]]:
        """
        Parse Redshift query result.

        Args:
            query_record: Query history record from STL_QUERY/STL_SCAN

        Returns:
            Tuple of (query_text, query_timestamp, table_references)
        """
        query_text = query_record.get("querytxt", "")
        query_timestamp = query_record.get("starttime", datetime.utcnow())

        table_refs = []

        # Extract from STL_SCAN table references
        tables = query_record.get("tables", [])
        for table_info in tables:
            schema = table_info.get("schema", "")
            table = table_info.get("table", "")
            database = table_info.get("database")
            if schema and table:
                table_refs.append((schema, table, database))

        # Also parse query text as fallback
        query_table_refs = self.sql_provider.extract_table_references(query_text)
        table_refs.extend(query_table_refs)

        # Deduplicate
        table_refs = list(set(table_refs))

        return query_text, query_timestamp, table_refs
