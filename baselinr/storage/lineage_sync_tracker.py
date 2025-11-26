"""
Sync timestamp tracker for query history lineage providers.

Tracks last sync timestamps per provider to enable incremental updates.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class LineageSyncTracker:
    """Tracks sync timestamps for query history lineage providers."""

    def __init__(self, engine: Engine):
        """
        Initialize sync tracker.

        Args:
            engine: SQLAlchemy engine for storage database
        """
        self.engine = engine
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Ensure baselinr_lineage_sync table exists."""

        # Get engine URL to determine dialect
        engine_url = str(self.engine.url)
        is_snowflake = "snowflake" in engine_url.lower()
        is_sqlite = "sqlite" in engine_url.lower()

        if is_snowflake:
            # Snowflake-specific DDL
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS baselinr_lineage_sync (
                    provider_name VARCHAR(50) PRIMARY KEY,
                    last_sync_timestamp TIMESTAMP_NTZ NOT NULL,
                    last_sync_query_count INTEGER,
                    last_sync_edge_count INTEGER,
                    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
                )
            """
        elif is_sqlite:
            # SQLite-specific DDL
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS baselinr_lineage_sync (
                    provider_name VARCHAR(50) PRIMARY KEY,
                    last_sync_timestamp TIMESTAMP NOT NULL,
                    last_sync_query_count INTEGER,
                    last_sync_edge_count INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
        else:
            # Generic SQL (PostgreSQL, MySQL, etc.)
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS baselinr_lineage_sync (
                    provider_name VARCHAR(50) PRIMARY KEY,
                    last_sync_timestamp TIMESTAMP NOT NULL,
                    last_sync_query_count INTEGER,
                    last_sync_edge_count INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """

        with self.engine.connect() as conn:
            conn.execute(text(create_table_sql))
            conn.commit()

    def get_last_sync(self, provider_name: str) -> Optional[datetime]:
        """
        Get last sync timestamp for a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            Last sync timestamp or None if never synced
        """
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT last_sync_timestamp
                    FROM baselinr_lineage_sync
                    WHERE provider_name = :provider_name
                    """
                ),
                {"provider_name": provider_name},
            )
            row = result.fetchone()
            if row:
                timestamp = row[0]
                if isinstance(timestamp, datetime):
                    return timestamp
            return None

    def update_sync(
        self,
        provider_name: str,
        timestamp: datetime,
        query_count: int = 0,
        edge_count: int = 0,
    ):
        """
        Update sync timestamp for a provider.

        Args:
            provider_name: Name of the provider
            timestamp: Sync timestamp
            query_count: Number of queries processed
            edge_count: Number of edges extracted
        """
        with self.engine.connect() as conn:
            # Get engine URL to determine dialect
            engine_url = str(self.engine.url)
            is_snowflake = "snowflake" in engine_url.lower()

            if is_snowflake:
                # Snowflake uses MERGE
                conn.execute(
                    text(
                        """
                        MERGE INTO baselinr_lineage_sync AS target
                        USING (
                            SELECT :provider_name AS provider_name,
                                   :timestamp AS last_sync_timestamp,
                                   :query_count AS last_sync_query_count,
                                   :edge_count AS last_sync_edge_count,
                                   CURRENT_TIMESTAMP() AS updated_at
                        ) AS source
                        ON target.provider_name = source.provider_name
                        WHEN MATCHED THEN
                            UPDATE SET
                                last_sync_timestamp = source.last_sync_timestamp,
                                last_sync_query_count = source.last_sync_query_count,
                                last_sync_edge_count = source.last_sync_edge_count,
                                updated_at = source.updated_at
                        WHEN NOT MATCHED THEN
                            INSERT (
                                provider_name, last_sync_timestamp, last_sync_query_count,
                                last_sync_edge_count, updated_at
                            )
                            VALUES (
                                source.provider_name, source.last_sync_timestamp,
                                source.last_sync_query_count, source.last_sync_edge_count,
                                source.updated_at
                            )
                        """
                    ),
                    {
                        "provider_name": provider_name,
                        "timestamp": timestamp,
                        "query_count": query_count,
                        "edge_count": edge_count,
                    },
                )
            else:
                # Use INSERT ... ON CONFLICT for PostgreSQL/SQLite
                # or ON DUPLICATE KEY UPDATE for MySQL
                is_postgres = "postgres" in engine_url.lower() or "postgresql" in engine_url.lower()
                is_mysql = "mysql" in engine_url.lower() or "mariadb" in engine_url.lower()

                if "sqlite" in engine_url.lower():
                    # SQLite
                    conn.execute(
                        text(
                            """
                            INSERT INTO baselinr_lineage_sync
                            (provider_name, last_sync_timestamp, last_sync_query_count,
                             last_sync_edge_count, updated_at)
                            VALUES (:provider_name, :timestamp, :query_count, :edge_count,
                                    CURRENT_TIMESTAMP)
                            ON CONFLICT(provider_name) DO UPDATE SET
                                last_sync_timestamp = :timestamp,
                                last_sync_query_count = :query_count,
                                last_sync_edge_count = :edge_count,
                                updated_at = CURRENT_TIMESTAMP
                            """
                        ),
                        {
                            "provider_name": provider_name,
                            "timestamp": timestamp,
                            "query_count": query_count,
                            "edge_count": edge_count,
                        },
                    )
                elif is_postgres:
                    # PostgreSQL uses ON CONFLICT ... DO UPDATE
                    conn.execute(
                        text(
                            """
                            INSERT INTO baselinr_lineage_sync
                            (provider_name, last_sync_timestamp, last_sync_query_count,
                             last_sync_edge_count, updated_at)
                            VALUES (:provider_name, :timestamp, :query_count, :edge_count,
                                    CURRENT_TIMESTAMP)
                            ON CONFLICT(provider_name) DO UPDATE SET
                                last_sync_timestamp = :timestamp,
                                last_sync_query_count = :query_count,
                                last_sync_edge_count = :edge_count,
                                updated_at = CURRENT_TIMESTAMP
                            """
                        ),
                        {
                            "provider_name": provider_name,
                            "timestamp": timestamp,
                            "query_count": query_count,
                            "edge_count": edge_count,
                        },
                    )
                elif is_mysql:
                    # MySQL uses ON DUPLICATE KEY UPDATE
                    conn.execute(
                        text(
                            """
                            INSERT INTO baselinr_lineage_sync
                            (provider_name, last_sync_timestamp, last_sync_query_count,
                             last_sync_edge_count, updated_at)
                            VALUES (:provider_name, :timestamp, :query_count, :edge_count,
                                    CURRENT_TIMESTAMP)
                            ON DUPLICATE KEY UPDATE
                                last_sync_timestamp = :timestamp,
                                last_sync_query_count = :query_count,
                                last_sync_edge_count = :edge_count,
                                updated_at = CURRENT_TIMESTAMP
                            """
                        ),
                        {
                            "provider_name": provider_name,
                            "timestamp": timestamp,
                            "query_count": query_count,
                            "edge_count": edge_count,
                        },
                    )
                else:
                    # Default to PostgreSQL syntax (ON CONFLICT) for unknown databases
                    conn.execute(
                        text(
                            """
                            INSERT INTO baselinr_lineage_sync
                            (provider_name, last_sync_timestamp, last_sync_query_count,
                             last_sync_edge_count, updated_at)
                            VALUES (:provider_name, :timestamp, :query_count, :edge_count,
                                    CURRENT_TIMESTAMP)
                            ON CONFLICT(provider_name) DO UPDATE SET
                                last_sync_timestamp = :timestamp,
                                last_sync_query_count = :query_count,
                                last_sync_edge_count = :edge_count,
                                updated_at = CURRENT_TIMESTAMP
                            """
                        ),
                        {
                            "provider_name": provider_name,
                            "timestamp": timestamp,
                            "query_count": query_count,
                            "edge_count": edge_count,
                        },
                    )
            conn.commit()
