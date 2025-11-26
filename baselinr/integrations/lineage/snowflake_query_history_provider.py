"""
Snowflake query history lineage provider.

Extracts lineage from SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .query_history_provider import QueryHistoryLineageProvider

logger = logging.getLogger(__name__)


class SnowflakeQueryHistoryProvider(QueryHistoryLineageProvider):
    """Lineage provider that extracts dependencies from Snowflake query history."""

    def __init__(
        self,
        source_engine: Optional[Engine] = None,
        config: Optional[Dict[str, Any]] = None,
        sync_tracker=None,
    ):
        """
        Initialize Snowflake query history provider.

        Args:
            source_engine: SQLAlchemy engine for Snowflake database
            config: Provider-specific configuration
            sync_tracker: Optional sync timestamp tracker
        """
        super().__init__(source_engine, config, sync_tracker)
        self.use_account_usage = (
            config.get("snowflake", {}).get("use_account_usage", True) if config else True
        )

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "snowflake_query_history"

    def is_available(self) -> bool:
        """
        Check if ACCESS_HISTORY is available.

        Returns:
            True if ACCESS_HISTORY can be queried
        """
        if not self.source_engine:
            return False

        try:
            if self.source_engine is None:
                return False
            with self.source_engine.connect() as conn:
                if self.use_account_usage:
                    conn.execute(
                        text("SELECT 1 FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY LIMIT 1")
                    )
                else:
                    conn.execute(text("SELECT 1 FROM INFORMATION_SCHEMA.ACCESS_HISTORY LIMIT 1"))
                return True
        except Exception as e:
            logger.debug(f"ACCESS_HISTORY not available: {e}")
            return False

    def _query_access_history(
        self, since_timestamp: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Query Snowflake's ACCESS_HISTORY.

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
                schema = (
                    "SNOWFLAKE.ACCOUNT_USAGE" if self.use_account_usage else "INFORMATION_SCHEMA"
                )

                if since_timestamp:
                    # Incremental query
                    query = text(
                        f"""
                        SELECT
                            QUERY_TEXT,
                            QUERY_START_TIME,
                            OBJECTS_MODIFIED,
                            OBJECTS_ACCESSED
                        FROM {schema}.ACCESS_HISTORY
                        WHERE QUERY_START_TIME >= :since_timestamp
                          AND QUERY_TEXT IS NOT NULL
                        ORDER BY QUERY_START_TIME DESC
                        """
                    )
                    result = conn.execute(query, {"since_timestamp": since_timestamp})
                else:
                    # Bulk query with lookback
                    lookback_timestamp = datetime.utcnow() - timedelta(days=self.lookback_days)
                    query = text(
                        f"""
                        SELECT
                            QUERY_TEXT,
                            QUERY_START_TIME,
                            OBJECTS_MODIFIED,
                            OBJECTS_ACCESSED
                        FROM {schema}.ACCESS_HISTORY
                        WHERE QUERY_START_TIME >= :lookback_timestamp
                          AND QUERY_TEXT IS NOT NULL
                        ORDER BY QUERY_START_TIME DESC
                        """
                    )
                    result = conn.execute(query, {"lookback_timestamp": lookback_timestamp})

                records = []
                for row in result:
                    records.append(
                        {
                            "query_text": row[0],
                            "query_start_time": row[1],
                            "objects_modified": row[2],
                            "objects_accessed": row[3],
                        }
                    )

                return records
        except Exception as e:
            logger.warning(f"Error querying Snowflake ACCESS_HISTORY: {e}")
            return []

    def _parse_query_result(
        self, query_record: Dict[str, Any]
    ) -> Tuple[str, datetime, List[Tuple[str, str, Optional[str]]]]:
        """
        Parse Snowflake query result.

        Args:
            query_record: Query history record from ACCESS_HISTORY

        Returns:
            Tuple of (query_text, query_timestamp, table_references)
        """
        query_text = query_record.get("query_text", "")
        query_timestamp = query_record.get("query_start_time", datetime.utcnow())

        # Extract table references from OBJECTS_MODIFIED and OBJECTS_ACCESSED
        table_refs = []

        # Parse OBJECTS_MODIFIED (JSON structure)
        objects_modified = query_record.get("objects_modified")
        if objects_modified:
            try:
                if isinstance(objects_modified, str):
                    objects_modified = json.loads(objects_modified)
                for obj in objects_modified:
                    if "objectName" in obj:
                        # Parse Snowflake object name: DATABASE.SCHEMA.TABLE
                        parts = obj["objectName"].split(".")
                        if len(parts) == 3:
                            table_refs.append(
                                (parts[1], parts[2], parts[0])
                            )  # (schema, table, database)
                        elif len(parts) == 2:
                            table_refs.append((parts[0], parts[1], None))  # (schema, table, None)
            except (json.JSONDecodeError, KeyError) as e:
                logger.debug(f"Error parsing OBJECTS_MODIFIED: {e}")

        # Parse OBJECTS_ACCESSED (JSON structure)
        objects_accessed = query_record.get("objects_accessed")
        if objects_accessed:
            try:
                if isinstance(objects_accessed, str):
                    objects_accessed = json.loads(objects_accessed)
                for obj in objects_accessed:
                    if "objectName" in obj:
                        # Parse Snowflake object name: DATABASE.SCHEMA.TABLE
                        parts = obj["objectName"].split(".")
                        if len(parts) == 3:
                            table_refs.append(
                                (parts[1], parts[2], parts[0])
                            )  # (schema, table, database)
                        elif len(parts) == 2:
                            table_refs.append((parts[0], parts[1], None))  # (schema, table, None)
            except (json.JSONDecodeError, KeyError) as e:
                logger.debug(f"Error parsing OBJECTS_ACCESSED: {e}")

        # Also parse query text as fallback
        query_table_refs = self.sql_provider.extract_table_references(query_text)
        table_refs.extend(query_table_refs)

        # Deduplicate
        table_refs = list(set(table_refs))

        return query_text, query_timestamp, table_refs
