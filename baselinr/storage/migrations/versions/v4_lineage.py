"""
Migration v4: Add lineage table

Creates baselinr_lineage table for storing data lineage relationships
extracted from various providers (dbt, SQL parsing, Dagster, etc.).
"""

from sqlalchemy import text

from ..manager import Migration


def create_lineage_table(conn):
    """Create lineage table with dialect-specific SQL."""
    # Get engine URL from connection
    engine = conn.bind if hasattr(conn, "bind") else conn.engine
    engine_url = str(engine.url)
    is_snowflake = "snowflake" in engine_url.lower()
    is_sqlite = "sqlite" in engine_url.lower()

    if is_snowflake:
        # Snowflake-specific DDL
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS baselinr_lineage (
                    id INTEGER AUTOINCREMENT PRIMARY KEY,
                    downstream_database VARCHAR(255),
                    downstream_schema VARCHAR(255) NOT NULL,
                    downstream_table VARCHAR(255) NOT NULL,
                    upstream_database VARCHAR(255),
                    upstream_schema VARCHAR(255) NOT NULL,
                    upstream_table VARCHAR(255) NOT NULL,
                    lineage_type VARCHAR(50) NOT NULL,
                    provider VARCHAR(50) NOT NULL,
                    confidence_score FLOAT DEFAULT 1.0,
                    first_seen_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
                    last_seen_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
                    metadata VARIANT,

                    UNIQUE (
                        downstream_database, downstream_schema, downstream_table,
                        upstream_database, upstream_schema, upstream_table, provider
                    )
                )
            """
            )
        )
        # Create indexes separately for Snowflake
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_lineage_downstream
                ON baselinr_lineage (downstream_database, downstream_schema, downstream_table)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_lineage_upstream
                ON baselinr_lineage (upstream_database, upstream_schema, upstream_table)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_lineage_provider
                ON baselinr_lineage (provider)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_lineage_last_seen
                ON baselinr_lineage (last_seen_at DESC)
            """
            )
        )
    elif is_sqlite:
        # SQLite-specific DDL
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS baselinr_lineage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    downstream_database VARCHAR(255),
                    downstream_schema VARCHAR(255) NOT NULL,
                    downstream_table VARCHAR(255) NOT NULL,
                    upstream_database VARCHAR(255),
                    upstream_schema VARCHAR(255) NOT NULL,
                    upstream_table VARCHAR(255) NOT NULL,
                    lineage_type VARCHAR(50) NOT NULL,
                    provider VARCHAR(50) NOT NULL,
                    confidence_score FLOAT DEFAULT 1.0,
                    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,

                    UNIQUE (
                        downstream_database, downstream_schema, downstream_table,
                        upstream_database, upstream_schema, upstream_table, provider
                    )
                )
            """
            )
        )
        # Create indexes separately for SQLite
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_lineage_downstream
                ON baselinr_lineage (downstream_database, downstream_schema, downstream_table)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_lineage_upstream
                ON baselinr_lineage (upstream_database, upstream_schema, upstream_table)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_lineage_provider
                ON baselinr_lineage (provider)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_lineage_last_seen
                ON baselinr_lineage (last_seen_at DESC)
            """
            )
        )
    else:
        # Generic SQL (PostgreSQL, MySQL, etc.)
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS baselinr_lineage (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    downstream_database VARCHAR(255),
                    downstream_schema VARCHAR(255) NOT NULL,
                    downstream_table VARCHAR(255) NOT NULL,
                    upstream_database VARCHAR(255),
                    upstream_schema VARCHAR(255) NOT NULL,
                    upstream_table VARCHAR(255) NOT NULL,
                    lineage_type VARCHAR(50) NOT NULL,
                    provider VARCHAR(50) NOT NULL,
                    confidence_score FLOAT DEFAULT 1.0,
                    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,

                    UNIQUE KEY unique_lineage (
                        downstream_database, downstream_schema, downstream_table,
                        upstream_database, upstream_schema, upstream_table, provider
                    ),
                    INDEX idx_downstream (downstream_database, downstream_schema, downstream_table),
                    INDEX idx_upstream (upstream_database, upstream_schema, upstream_table),
                    INDEX idx_provider (provider),
                    INDEX idx_last_seen (last_seen_at DESC)
                )
            """
            )
        )


migration = Migration(
    version=4,
    description=(
        "Add lineage table for data dependency relationships from multiple providers "
        "with database, schema, and table support"
    ),
    up_python=create_lineage_table,
    down_sql="DROP TABLE IF EXISTS baselinr_lineage",
)
