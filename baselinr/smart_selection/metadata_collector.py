"""
Database metadata collection for smart table selection.

Queries database-specific system tables to collect usage statistics,
query frequency, table sizes, and other relevant metadata.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ..config.schema import DatabaseType

logger = logging.getLogger(__name__)


@dataclass
class TableMetadata:
    """Metadata about a table for smart selection."""

    database: str
    schema: str
    table: str

    # Query statistics
    query_count: int = 0
    queries_per_day: float = 0.0
    last_query_time: Optional[datetime] = None
    days_since_last_query: Optional[int] = None

    # Table characteristics
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None
    last_modified_time: Optional[datetime] = None
    days_since_modified: Optional[int] = None
    created_time: Optional[datetime] = None

    # Additional metadata
    table_type: Optional[str] = None  # table, view, materialized_view
    has_partitions: bool = False
    partition_key: Optional[str] = None

    # Raw metadata for debugging
    raw_metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Calculate derived fields."""
        if self.raw_metadata is None:
            self.raw_metadata = {}

        # Calculate days since last query
        if self.last_query_time:
            # Normalize timezone-aware/naive datetime for comparison
            query_time = self.last_query_time
            if hasattr(query_time, "tzinfo") and query_time.tzinfo is not None:
                query_time = query_time.replace(tzinfo=None)
            now = datetime.now()
            self.days_since_last_query = (now - query_time).days

        # Calculate days since modified
        if self.last_modified_time:
            # Normalize timezone-aware/naive datetime for comparison
            modified_time = self.last_modified_time
            if hasattr(modified_time, "tzinfo") and modified_time.tzinfo is not None:
                modified_time = modified_time.replace(tzinfo=None)
            now = datetime.now()
            self.days_since_modified = (now - modified_time).days


class MetadataCollector:
    """Collects table metadata from database-specific system tables."""

    def __init__(
        self,
        engine: Engine,
        database_type: DatabaseType,
        lookback_days: int = 30,
    ):
        """
        Initialize metadata collector.

        Args:
            engine: SQLAlchemy engine for querying metadata
            database_type: Type of database (snowflake, bigquery, postgres, etc.)
            lookback_days: Number of days to look back for query statistics
        """
        self.engine = engine
        self.database_type = database_type
        self.lookback_days = lookback_days

        # Map database types to collection methods
        self._collectors = {
            DatabaseType.SNOWFLAKE: self._collect_snowflake,
            DatabaseType.BIGQUERY: self._collect_bigquery,
            DatabaseType.POSTGRES: self._collect_postgres,
            DatabaseType.REDSHIFT: self._collect_redshift,
            DatabaseType.MYSQL: self._collect_mysql,
            DatabaseType.SQLITE: self._collect_sqlite,
        }

    def collect_metadata(
        self,
        schema: Optional[str] = None,
        tables: Optional[List[str]] = None,
    ) -> List[TableMetadata]:
        """
        Collect metadata for tables.

        Args:
            schema: Optional schema filter
            tables: Optional list of specific tables to collect metadata for

        Returns:
            List of TableMetadata objects

        Raises:
            ValueError: If database type is not supported
        """
        collector = self._collectors.get(self.database_type)
        if not collector:
            raise ValueError(
                f"Smart selection not supported for database type: {self.database_type}"
            )

        logger.info(
            f"Collecting metadata for {self.database_type} " f"(lookback_days={self.lookback_days})"
        )

        try:
            return collector(schema=schema, tables=tables)
        except Exception as e:
            logger.error(f"Failed to collect metadata: {e}")
            # Return empty list on error - graceful degradation
            return []

    def _collect_snowflake(
        self,
        schema: Optional[str] = None,
        tables: Optional[List[str]] = None,
    ) -> List[TableMetadata]:
        """Collect metadata from Snowflake ACCOUNT_USAGE and INFORMATION_SCHEMA."""
        results = []

        # Calculate lookback date
        lookback_date = datetime.now() - timedelta(days=self.lookback_days)

        # Query for table metadata with usage statistics
        # Note: ACCOUNT_USAGE views require ACCOUNTADMIN or USAGE privileges
        query = text(
            """
        WITH query_stats AS (
            SELECT
                qh.database_name,
                qh.schema_name,
                REGEXP_SUBSTR(qh.query_text, 'FROM\\s+([^\\s,;()]+)', 1, 1, 'ie', 1) as table_name,
                COUNT(*) as query_count,
                MAX(qh.start_time) as last_query_time
            FROM snowflake.account_usage.query_history qh
            WHERE qh.start_time >= :lookback_date
                AND qh.execution_status = 'SUCCESS'
                AND LOWER(qh.query_text) LIKE '%from%'
                AND qh.query_type IN ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'MERGE')
            GROUP BY qh.database_name, qh.schema_name, table_name
        ),
        table_storage AS (
            SELECT
                ts.table_catalog as database_name,
                ts.table_schema as schema_name,
                ts.table_name,
                ts.row_count,
                ts.bytes,
                ts.last_altered as last_modified_time
            FROM snowflake.account_usage.table_storage_metrics ts
            WHERE ts.deleted IS NULL
        )
        SELECT
            COALESCE(qs.database_name, ts.database_name) as database_name,
            COALESCE(qs.schema_name, ts.schema_name) as schema_name,
            COALESCE(qs.table_name, ts.table_name) as table_name,
            COALESCE(qs.query_count, 0) as query_count,
            qs.last_query_time,
            ts.row_count,
            ts.bytes as size_bytes,
            ts.last_modified_time
        FROM query_stats qs
        FULL OUTER JOIN table_storage ts
            ON UPPER(qs.database_name) = UPPER(ts.database_name)
            AND UPPER(qs.schema_name) = UPPER(ts.schema_name)
            AND UPPER(qs.table_name) = UPPER(ts.table_name)
        WHERE 1=1
            AND (
                :schema IS NULL OR
                UPPER(COALESCE(qs.schema_name, ts.schema_name)) = UPPER(:schema)
            )
        ORDER BY COALESCE(qs.query_count, 0) DESC
        """
        )

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, {"lookback_date": lookback_date, "schema": schema})

                for row in result:
                    # Filter by table names if specified
                    if tables and row.table_name not in tables:
                        continue

                    queries_per_day = (
                        row.query_count / self.lookback_days if row.query_count else 0.0
                    )

                    metadata = TableMetadata(
                        database=row.database_name,
                        schema=row.schema_name,
                        table=row.table_name,
                        query_count=row.query_count or 0,
                        queries_per_day=queries_per_day,
                        last_query_time=row.last_query_time,
                        row_count=row.row_count,
                        size_bytes=row.size_bytes,
                        last_modified_time=row.last_modified_time,
                    )
                    results.append(metadata)

                logger.info(f"Collected metadata for {len(results)} Snowflake tables")

        except Exception as e:
            logger.warning(
                f"Failed to query Snowflake ACCOUNT_USAGE (requires privileges): {e}. "
                "Falling back to INFORMATION_SCHEMA only."
            )
            # Fallback to basic INFORMATION_SCHEMA
            results = self._collect_snowflake_fallback(schema, tables)

        return results

    def _collect_snowflake_fallback(
        self,
        schema: Optional[str] = None,
        tables: Optional[List[str]] = None,
    ) -> List[TableMetadata]:
        """Fallback Snowflake collection using only INFORMATION_SCHEMA."""
        results = []

        query = text(
            """
        SELECT
            table_catalog as database_name,
            table_schema as schema_name,
            table_name,
            row_count,
            bytes as size_bytes,
            last_altered as last_modified_time,
            created as created_time,
            table_type
        FROM information_schema.tables
        WHERE table_schema != 'INFORMATION_SCHEMA'
            AND (:schema IS NULL OR UPPER(table_schema) = UPPER(:schema))
        ORDER BY row_count DESC NULLS LAST
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(query, {"schema": schema})

            for row in result:
                if tables and row.table_name not in tables:
                    continue

                metadata = TableMetadata(
                    database=row.database_name,
                    schema=row.schema_name,
                    table=row.table_name,
                    row_count=row.row_count,
                    size_bytes=row.size_bytes,
                    last_modified_time=row.last_modified_time,
                    created_time=row.created_time,
                    table_type=row.table_type,
                )
                results.append(metadata)

        logger.info(f"Collected fallback metadata for {len(results)} Snowflake tables")
        return results

    def _collect_bigquery(
        self,
        schema: Optional[str] = None,
        tables: Optional[List[str]] = None,
    ) -> List[TableMetadata]:
        """Collect metadata from BigQuery INFORMATION_SCHEMA."""
        # BigQuery uses project.dataset.table naming
        # schema parameter maps to dataset
        # Note: This is a stub implementation - full BigQuery query logic
        # would use lookback_date and query variables when implemented
        # The query structure is preserved in comments for future implementation:
        #
        # lookback_date = datetime.now() - timedelta(days=self.lookback_days)
        # query = text("""
        #     WITH query_stats AS (
        #         SELECT
        #             referenced_tables.project_id as project_name,
        #             referenced_tables.dataset_id as dataset_name,
        #             referenced_tables.table_id as table_name,
        #             COUNT(*) as query_count,
        #             MAX(creation_time) as last_query_time
        #         FROM `region-{region}.INFORMATION_SCHEMA.JOBS_BY_PROJECT`,
        #             UNNEST(referenced_tables) as referenced_tables
        #         WHERE creation_time >= @lookback_date
        #             AND state = 'DONE'
        #             AND error_result IS NULL
        #         GROUP BY project_name, dataset_name, table_name
        #     ),
        #     table_storage AS (
        #         SELECT
        #             table_catalog as project_name,
        #             table_schema as dataset_name,
        #             table_name,
        #             CAST(row_count AS INT64) as row_count,
        #             size_bytes,
        #             TIMESTAMP_MILLIS(creation_time) as created_time,
        #             TIMESTAMP_MILLIS(COALESCE(
        #                 GREATEST(last_modified_time, last_alter_time),
        #                 last_modified_time,
        #                 last_alter_time
        #             )) as last_modified_time,
        #             table_type
        #         FROM `{project}.{dataset}.INFORMATION_SCHEMA.TABLES`
        #         WHERE table_type IN ('BASE TABLE', 'VIEW', 'MATERIALIZED VIEW')
        #     )
        #     SELECT
        #         COALESCE(qs.project_name, ts.project_name) as project_name,
        #         COALESCE(qs.dataset_name, ts.dataset_name) as dataset_name,
        #         COALESCE(qs.table_name, ts.table_name) as table_name,
        #         COALESCE(qs.query_count, 0) as query_count,
        #         qs.last_query_time,
        #         ts.row_count,
        #         ts.size_bytes,
        #         ts.last_modified_time,
        #         ts.created_time,
        #         ts.table_type
        #     FROM query_stats qs
        #     FULL OUTER JOIN table_storage ts
        #         ON qs.project_name = ts.project_name
        #         AND qs.dataset_name = ts.dataset_name
        #         AND qs.table_name = ts.table_name
        #     WHERE (
        #         @schema IS NULL OR
        #         LOWER(COALESCE(qs.dataset_name, ts.dataset_name)) = LOWER(@schema)
        #     )
        #     ORDER BY COALESCE(qs.query_count, 0) DESC
        # """)

        # BigQuery implementation would go here
        # For now, return empty list with a note
        logger.warning(
            "BigQuery metadata collection requires project/dataset-specific queries. "
            "Using INFORMATION_SCHEMA fallback."
        )
        return self._collect_bigquery_fallback(schema, tables)

    def _collect_bigquery_fallback(
        self,
        schema: Optional[str] = None,
        tables: Optional[List[str]] = None,
    ) -> List[TableMetadata]:
        """Fallback BigQuery collection using INFORMATION_SCHEMA.TABLES."""
        results = []

        # Use simpler query for basic table information
        query = text(
            """
        SELECT
            table_catalog as project_name,
            table_schema as dataset_name,
            table_name,
            CAST(row_count AS INT64) as row_count,
            size_bytes,
            TIMESTAMP_MILLIS(creation_time) as created_time,
            table_type
        FROM INFORMATION_SCHEMA.TABLES
        WHERE table_type IN ('BASE TABLE', 'VIEW', 'MATERIALIZED VIEW')
            AND (:schema IS NULL OR LOWER(table_schema) = LOWER(:schema))
        ORDER BY row_count DESC NULLS LAST
        """
        )

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, {"schema": schema})

                for row in result:
                    if tables and row.table_name not in tables:
                        continue

                    metadata = TableMetadata(
                        database=row.project_name,
                        schema=row.dataset_name,
                        table=row.table_name,
                        row_count=row.row_count,
                        size_bytes=row.size_bytes,
                        created_time=row.created_time,
                        table_type=row.table_type,
                    )
                    results.append(metadata)

            logger.info(f"Collected fallback metadata for {len(results)} BigQuery tables")
        except Exception as e:
            logger.error(f"Failed to collect BigQuery metadata: {e}")

        return results

    def _collect_postgres(
        self,
        schema: Optional[str] = None,
        tables: Optional[List[str]] = None,
    ) -> List[TableMetadata]:
        """Collect metadata from PostgreSQL pg_stat_user_tables."""
        results = []

        query = text(
            """
        SELECT
            current_database() as database_name,
            st.schemaname as schema_name,
            st.relname as table_name,
            -- Query statistics from pg_stat_user_tables
            st.seq_scan + st.idx_scan as total_scans,
            GREATEST(
                st.last_vacuum, st.last_autovacuum,
                st.last_analyze, st.last_autoanalyze
            ) as last_maintenance,
            st.n_tup_ins + st.n_tup_upd + st.n_tup_del as write_operations,
            -- Table size information
            pg_total_relation_size(st.relid) as size_bytes,
            -- Row count estimate from pg_class (use relid to avoid regclass issues)
            COALESCE(c.reltuples::bigint, 0) as row_count
        FROM pg_stat_user_tables st
        LEFT JOIN pg_class c ON c.oid = st.relid
        WHERE (:schema IS NULL OR st.schemaname = :schema)
        ORDER BY total_scans DESC
        """
        )

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, {"schema": schema})

                for row in result:
                    if tables and row.table_name not in tables:
                        continue

                    # PostgreSQL doesn't track individual queries easily
                    # Use scan count as proxy for usage
                    query_count = row.total_scans or 0

                    # Handle timezone-aware/naive datetime issues
                    last_modified = row.last_maintenance
                    if last_modified:
                        # Make timezone-naive if needed for comparison
                        if hasattr(last_modified, "tzinfo") and last_modified.tzinfo is not None:
                            # Convert to naive (remove timezone info)
                            last_modified = last_modified.replace(tzinfo=None)

                    metadata = TableMetadata(
                        database=row.database_name,
                        schema=row.schema_name,
                        table=row.table_name,
                        query_count=query_count,
                        queries_per_day=query_count / self.lookback_days if query_count else 0.0,
                        row_count=row.row_count,
                        size_bytes=row.size_bytes,
                        last_modified_time=last_modified,
                        raw_metadata={
                            "write_operations": row.write_operations,
                        },
                    )
                    results.append(metadata)

            logger.info(f"Collected metadata for {len(results)} PostgreSQL tables")
        except Exception as e:
            logger.error(f"Failed to collect PostgreSQL metadata: {e}")

        return results

    def _collect_redshift(
        self,
        schema: Optional[str] = None,
        tables: Optional[List[str]] = None,
    ) -> List[TableMetadata]:
        """Collect metadata from Redshift STL_QUERY and SVV_TABLE_INFO."""
        results = []

        lookback_date = datetime.now() - timedelta(days=self.lookback_days)

        query = text(
            """
        WITH query_stats AS (
            SELECT
                database,
                "schema",
                "table",
                COUNT(*) as query_count,
                MAX(starttime) as last_query_time
            FROM stl_scan
            WHERE starttime >= :lookback_date
            GROUP BY database, "schema", "table"
        ),
        table_info AS (
            SELECT
                database,
                "schema",
                "table",
                size * 1024 * 1024 as size_bytes,  -- size is in MB
                tbl_rows as row_count,
                max_varchar,
                unsorted
            FROM svv_table_info
        )
        SELECT
            COALESCE(qs.database, ti.database) as database_name,
            COALESCE(qs."schema", ti."schema") as schema_name,
            COALESCE(qs."table", ti."table") as table_name,
            COALESCE(qs.query_count, 0) as query_count,
            qs.last_query_time,
            ti.row_count,
            ti.size_bytes,
            ti.unsorted
        FROM query_stats qs
        FULL OUTER JOIN table_info ti
            ON qs.database = ti.database
            AND qs."schema" = ti."schema"
            AND qs."table" = ti."table"
        WHERE (:schema IS NULL OR LOWER(COALESCE(qs."schema", ti."schema")) = LOWER(:schema))
        ORDER BY COALESCE(qs.query_count, 0) DESC
        """
        )

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, {"lookback_date": lookback_date, "schema": schema})

                for row in result:
                    if tables and row.table_name not in tables:
                        continue

                    queries_per_day = (
                        row.query_count / self.lookback_days if row.query_count else 0.0
                    )

                    metadata = TableMetadata(
                        database=row.database_name,
                        schema=row.schema_name,
                        table=row.table_name,
                        query_count=row.query_count or 0,
                        queries_per_day=queries_per_day,
                        last_query_time=row.last_query_time,
                        row_count=row.row_count,
                        size_bytes=row.size_bytes,
                        raw_metadata={
                            "unsorted": row.unsorted,
                        },
                    )
                    results.append(metadata)

            logger.info(f"Collected metadata for {len(results)} Redshift tables")
        except Exception as e:
            logger.error(f"Failed to collect Redshift metadata: {e}")

        return results

    def _collect_mysql(
        self,
        schema: Optional[str] = None,
        tables: Optional[List[str]] = None,
    ) -> List[TableMetadata]:
        """Collect metadata from MySQL INFORMATION_SCHEMA."""
        results = []

        # MySQL doesn't have built-in query history tracking
        # Use table stats from INFORMATION_SCHEMA
        query = text(
            """
        SELECT
            table_schema as schema_name,
            table_name,
            table_rows as row_count,
            data_length + index_length as size_bytes,
            create_time as created_time,
            update_time as last_modified_time,
            table_type
        FROM information_schema.tables
        WHERE table_schema NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
            AND (:schema IS NULL OR table_schema = :schema)
        ORDER BY table_rows DESC
        """
        )

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, {"schema": schema})

                for row in result:
                    if tables and row.table_name not in tables:
                        continue

                    # Get current database name
                    db_result = conn.execute(text("SELECT DATABASE()"))
                    database_name = db_result.scalar() or "unknown"

                    metadata = TableMetadata(
                        database=database_name,
                        schema=row.schema_name,
                        table=row.table_name,
                        row_count=row.row_count,
                        size_bytes=row.size_bytes,
                        created_time=row.created_time,
                        last_modified_time=row.last_modified_time,
                        table_type=row.table_type,
                    )
                    results.append(metadata)

            logger.info(f"Collected metadata for {len(results)} MySQL tables")
        except Exception as e:
            logger.error(f"Failed to collect MySQL metadata: {e}")

        return results

    def _collect_sqlite(
        self,
        schema: Optional[str] = None,
        tables: Optional[List[str]] = None,
    ) -> List[TableMetadata]:
        """Collect metadata from SQLite sqlite_master."""
        results = []

        # SQLite has very limited metadata
        query = text(
            """
        SELECT
            name as table_name,
            type as table_type
        FROM sqlite_master
        WHERE type IN ('table', 'view')
            AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
        )

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query)

                for row in result:
                    if tables and row.table_name not in tables:
                        continue

                    # Try to get row count
                    try:
                        count_result = conn.execute(text(f"SELECT COUNT(*) FROM {row.table_name}"))
                        row_count = count_result.scalar()
                    except Exception:
                        row_count = None

                    metadata = TableMetadata(
                        database="main",
                        schema="main",
                        table=row.table_name,
                        row_count=row_count,
                        table_type=row.table_type,
                    )
                    results.append(metadata)

            logger.info(f"Collected metadata for {len(results)} SQLite tables")
        except Exception as e:
            logger.error(f"Failed to collect SQLite metadata: {e}")

        return results
