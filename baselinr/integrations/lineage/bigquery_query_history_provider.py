"""
BigQuery query history lineage provider.

Extracts lineage from INFORMATION_SCHEMA.JOBS_BY_PROJECT.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .query_history_provider import QueryHistoryLineageProvider

logger = logging.getLogger(__name__)


class BigQueryQueryHistoryProvider(QueryHistoryLineageProvider):
    """Lineage provider that extracts dependencies from BigQuery query history."""

    def __init__(
        self,
        source_engine: Optional[Engine] = None,
        config: Optional[Dict[str, Any]] = None,
        sync_tracker=None,
    ):
        """
        Initialize BigQuery query history provider.

        Args:
            source_engine: SQLAlchemy engine for BigQuery database
            config: Provider-specific configuration
            sync_tracker: Optional sync timestamp tracker
        """
        super().__init__(source_engine, config, sync_tracker)
        bigquery_config = config.get("bigquery", {}) if config else {}
        self.region = bigquery_config.get("region", "us")

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "bigquery_query_history"

    def is_available(self) -> bool:
        """
        Check if INFORMATION_SCHEMA.JOBS_BY_PROJECT is available.

        Returns:
            True if INFORMATION_SCHEMA can be queried
        """
        if not self.source_engine:
            return False

        try:
            if self.source_engine is None:
                return False
            with self.source_engine.connect() as conn:
                conn.execute(
                    text(
                        f"SELECT 1 FROM `region-{self.region}`."
                        f"INFORMATION_SCHEMA.JOBS_BY_PROJECT LIMIT 1"
                    )
                )
                return True
        except Exception as e:
            logger.debug(f"INFORMATION_SCHEMA.JOBS_BY_PROJECT not available: {e}")
            return False

    def _query_access_history(
        self, since_timestamp: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Query BigQuery's INFORMATION_SCHEMA.JOBS_BY_PROJECT.

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
                        f"""
                        SELECT
                            query,
                            creation_time,
                            destination_table,
                            referenced_tables
                        FROM `region-{self.region}`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
                        WHERE creation_time >= :since_timestamp
                          AND statement_type = 'SELECT'
                          AND query IS NOT NULL
                        ORDER BY creation_time DESC
                        """
                    )
                    result = conn.execute(query, {"since_timestamp": since_timestamp})
                else:
                    # Bulk query with lookback
                    lookback_timestamp = datetime.utcnow() - timedelta(days=self.lookback_days)
                    query = text(
                        f"""
                        SELECT
                            query,
                            creation_time,
                            destination_table,
                            referenced_tables
                        FROM `region-{self.region}`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
                        WHERE creation_time >= :lookback_timestamp
                          AND statement_type = 'SELECT'
                          AND query IS NOT NULL
                        ORDER BY creation_time DESC
                        """
                    )
                    result = conn.execute(query, {"lookback_timestamp": lookback_timestamp})

                records = []
                for row in result:
                    records.append(
                        {
                            "query": row[0],
                            "creation_time": row[1],
                            "destination_table": row[2],
                            "referenced_tables": row[3],
                        }
                    )

                return records
        except Exception as e:
            logger.warning(f"Error querying BigQuery INFORMATION_SCHEMA: {e}")
            return []

    def _parse_query_result(
        self, query_record: Dict[str, Any]
    ) -> Tuple[str, datetime, List[Tuple[str, str, Optional[str]]]]:
        """
        Parse BigQuery query result.

        Args:
            query_record: Query history record from INFORMATION_SCHEMA

        Returns:
            Tuple of (query_text, query_timestamp, table_references)
        """
        query_text = query_record.get("query", "")
        query_timestamp = query_record.get("creation_time", datetime.utcnow())

        table_refs = []

        # Parse destination_table (project.dataset.table format)
        destination_table = query_record.get("destination_table")
        if destination_table:
            parts = destination_table.split(".")
            if len(parts) == 3:
                table_refs.append((parts[1], parts[2], parts[0]))  # (dataset, table, project)

        # Parse referenced_tables array
        referenced_tables = query_record.get("referenced_tables")
        if referenced_tables:
            if isinstance(referenced_tables, str):
                # May be JSON string
                import json

                try:
                    referenced_tables = json.loads(referenced_tables)
                except json.JSONDecodeError:
                    pass

            if isinstance(referenced_tables, list):
                for ref_table in referenced_tables:
                    if isinstance(ref_table, dict):
                        # Format: {"projectId": "...", "datasetId": "...", "tableId": "..."}
                        project = ref_table.get("projectId")
                        dataset = ref_table.get("datasetId")
                        table = ref_table.get("tableId")
                        if project and dataset and table:
                            table_refs.append((dataset, table, project))
                    elif isinstance(ref_table, str):
                        # Format: "project.dataset.table"
                        parts = ref_table.split(".")
                        if len(parts) == 3:
                            table_refs.append((parts[1], parts[2], parts[0]))

        # Also parse query text as fallback
        query_table_refs = self.sql_provider.extract_table_references(query_text)
        table_refs.extend(query_table_refs)

        # Deduplicate
        table_refs = list(set(table_refs))

        return query_text, query_timestamp, table_refs
