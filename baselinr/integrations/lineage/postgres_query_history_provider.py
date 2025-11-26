"""
PostgreSQL query history lineage provider.

Extracts lineage from pg_stat_statements extension.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .query_history_provider import QueryHistoryLineageProvider

logger = logging.getLogger(__name__)


class PostgresQueryHistoryProvider(QueryHistoryLineageProvider):
    """Lineage provider that extracts dependencies from PostgreSQL query history."""

    def __init__(
        self,
        source_engine: Optional[Engine] = None,
        config: Optional[Dict[str, Any]] = None,
        sync_tracker=None,
    ):
        """
        Initialize PostgreSQL query history provider.

        Args:
            source_engine: SQLAlchemy engine for PostgreSQL database
            config: Provider-specific configuration
            sync_tracker: Optional sync timestamp tracker
        """
        super().__init__(source_engine, config, sync_tracker)
        self._extension_available: Optional[bool] = None

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "postgres_query_history"

    def is_available(self) -> bool:
        """
        Check if pg_stat_statements extension is available.

        Returns:
            True if extension is installed and available
        """
        if self._extension_available is not None:
            return self._extension_available

        if not self.source_engine:
            return False

        try:
            if self.source_engine is None:
                return False
            with self.source_engine.connect() as conn:
                result = conn.execute(
                    text(
                        """
                        SELECT EXISTS (
                            SELECT 1
                            FROM pg_extension
                            WHERE extname = 'pg_stat_statements'
                        )
                        """
                    )
                )
                value = result.scalar()
                self._extension_available = bool(value) if value is not None else False
                return self._extension_available
        except Exception as e:
            logger.debug(f"Error checking pg_stat_statements extension: {e}")
            self._extension_available = False
            return False

    def _query_access_history(
        self, since_timestamp: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Query PostgreSQL's pg_stat_statements.

        Note: pg_stat_statements doesn't track individual query timestamps,
        only aggregate statistics. We query all statements and use current time
        as a proxy timestamp. True incremental sync based on timestamps is not
        possible with pg_stat_statements alone.

        Args:
            since_timestamp: Optional timestamp (not used, as pg_stat_statements
                           doesn't support timestamp filtering)

        Returns:
            List of query history records
        """
        if not self.is_available():
            return []

        if not self.source_engine:
            return []

        try:
            with self.source_engine.connect() as conn:
                # Get current database name for context
                db_result = conn.execute(text("SELECT current_database()"))
                current_db = db_result.scalar()

                # Query pg_stat_statements
                # Note: pg_stat_statements doesn't track individual query timestamps,
                # only aggregate statistics. We'll use current time as proxy.
                query = text(
                    """
                    SELECT
                        query,
                        calls,
                        mean_exec_time,
                        max_exec_time,
                        total_exec_time
                    FROM pg_stat_statements
                    WHERE query IS NOT NULL
                      AND query NOT LIKE '%pg_stat_statements%'
                      AND calls > 0
                    ORDER BY calls DESC
                    """
                )

                result = conn.execute(query)
                records = []
                # Use current time as proxy since pg_stat_statements doesn't track timestamps
                current_time = datetime.utcnow()
                for row in result:
                    records.append(
                        {
                            "query": row[0],
                            "calls": row[1],
                            "mean_exec_time": row[2],
                            "max_exec_time": row[3],
                            "total_exec_time": row[4],
                            "query_timestamp": current_time,  # Use current time as proxy
                            "database": current_db,
                        }
                    )

                return records
        except Exception as e:
            logger.warning(f"Error querying pg_stat_statements: {e}")
            return []

    def _parse_query_result(
        self, query_record: Dict[str, Any]
    ) -> Tuple[str, datetime, List[Tuple[str, str, Optional[str]]]]:
        """
        Parse PostgreSQL query result.

        Args:
            query_record: Query history record from pg_stat_statements

        Returns:
            Tuple of (query_text, query_timestamp, table_references)
        """
        query_text = query_record.get("query", "")
        database = query_record.get("database")

        # Use SQL provider to extract table references
        table_refs = self.sql_provider.extract_table_references(
            query_text,
            default_database=database,
            default_schema="public",  # PostgreSQL default schema
        )

        # Use query_timestamp from record (set to current time when querying)
        query_timestamp = query_record.get("query_timestamp", datetime.utcnow())
        if not isinstance(query_timestamp, datetime):
            query_timestamp = datetime.utcnow()

        return query_text, query_timestamp, table_refs
