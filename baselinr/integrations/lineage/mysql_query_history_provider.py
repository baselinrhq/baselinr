"""
MySQL query history lineage provider.

Extracts lineage from performance_schema.events_statements_history_long.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .query_history_provider import QueryHistoryLineageProvider

logger = logging.getLogger(__name__)


class MySQLQueryHistoryProvider(QueryHistoryLineageProvider):
    """Lineage provider that extracts dependencies from MySQL query history."""

    def __init__(
        self,
        source_engine: Optional[Engine] = None,
        config: Optional[Dict[str, Any]] = None,
        sync_tracker=None,
    ):
        """
        Initialize MySQL query history provider.

        Args:
            source_engine: SQLAlchemy engine for MySQL database
            config: Provider-specific configuration
            sync_tracker: Optional sync timestamp tracker
        """
        super().__init__(source_engine, config, sync_tracker)
        self._performance_schema_available: Optional[bool] = None

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "mysql_query_history"

    def is_available(self) -> bool:
        """
        Check if performance_schema is enabled and available.

        Returns:
            True if performance_schema is enabled
        """
        if self._performance_schema_available is not None:
            return self._performance_schema_available

        if not self.source_engine:
            return False

        try:
            if self.source_engine is None:
                return False
            with self.source_engine.connect() as conn:
                result = conn.execute(
                    text(
                        """
                        SELECT VARIABLE_VALUE
                        FROM performance_schema.global_variables
                        WHERE VARIABLE_NAME = 'performance_schema'
                        """
                    )
                )
                value = result.scalar()
                self._performance_schema_available = value == "ON"
                return self._performance_schema_available
        except Exception as e:
            logger.debug(f"Error checking performance_schema: {e}")
            self._performance_schema_available = False
            return False

    def _query_access_history(
        self, since_timestamp: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Query MySQL's performance_schema.events_statements_history_long.

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
                # Get current database name for context
                db_result = conn.execute(text("SELECT DATABASE()"))
                current_db = db_result.scalar()

                if since_timestamp:
                    # Incremental query
                    # Note: timer_start is in picoseconds, need to convert
                    # We'll use a simpler approach: query recent entries
                    query = text(
                        """
                        SELECT
                            sql_text,
                            timer_start,
                            timer_end,
                            schema_name,
                            object_schema,
                            object_name
                        FROM performance_schema.events_statements_history_long
                        WHERE timer_start >= :since_timestamp_pico
                          AND sql_text IS NOT NULL
                          AND sql_text NOT LIKE '%performance_schema%'
                        ORDER BY timer_start DESC
                        """
                    )
                    # Convert datetime to picoseconds (approximate)
                    # timer_start is in picoseconds since server start
                    # For simplicity, we'll query recent entries by limiting results
                    result = conn.execute(
                        text(
                            """
                            SELECT
                                sql_text,
                                timer_start,
                                timer_end,
                                schema_name,
                                object_schema,
                                object_name
                            FROM performance_schema.events_statements_history_long
                            WHERE sql_text IS NOT NULL
                              AND sql_text NOT LIKE '%performance_schema%'
                            ORDER BY timer_start DESC
                            LIMIT 10000
                            """
                        )
                    )
                else:
                    # Bulk query - get recent entries
                    query = text(
                        """
                        SELECT
                            sql_text,
                            timer_start,
                            timer_end,
                            schema_name,
                            object_schema,
                            object_name
                        FROM performance_schema.events_statements_history_long
                        WHERE sql_text IS NOT NULL
                          AND sql_text NOT LIKE '%performance_schema%'
                        ORDER BY timer_start DESC
                        LIMIT 10000
                        """
                    )
                    result = conn.execute(query)

                records = []
                for row in result:
                    records.append(
                        {
                            "sql_text": row[0],
                            "timer_start": row[1],
                            "timer_end": row[2],
                            "schema_name": row[3],
                            "object_schema": row[4],
                            "object_name": row[5],
                            "database": current_db,
                        }
                    )

                return records
        except Exception as e:
            logger.warning(f"Error querying MySQL performance_schema: {e}")
            return []

    def _parse_query_result(
        self, query_record: Dict[str, Any]
    ) -> Tuple[str, datetime, List[Tuple[str, str, Optional[str]]]]:
        """
        Parse MySQL query result.

        Args:
            query_record: Query history record from performance_schema

        Returns:
            Tuple of (query_text, query_timestamp, table_references)
        """
        query_text = query_record.get("sql_text", "")
        database = query_record.get("database")

        # Use SQL provider to extract table references
        # In MySQL, schema = database
        table_refs = self.sql_provider.extract_table_references(
            query_text,
            default_database=database,
            default_schema=database,  # MySQL: schema = database
        )

        # Use timer_start if available, otherwise use current time
        # Note: timer_start is in picoseconds, we'll use current time as approximation
        query_timestamp = datetime.utcnow()

        # Also check object_schema and object_name if available
        object_schema = query_record.get("object_schema")
        object_name = query_record.get("object_name")
        if object_schema and object_name:
            table_refs.append((object_schema, object_name, database))

        # Deduplicate
        table_refs = list(set(table_refs))

        return query_text, query_timestamp, table_refs
