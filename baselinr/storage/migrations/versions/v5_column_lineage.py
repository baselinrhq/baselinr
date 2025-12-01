"""
Migration v5: Add column-level lineage table

Creates baselinr_column_lineage table for storing column-level lineage relationships
extracted from various providers (dbt, SQL parsing, query history, etc.).
"""

from sqlalchemy import text

from ..manager import Migration


def create_column_lineage_table(conn):
    """Create column lineage table with dialect-specific SQL."""
    # Get engine URL from connection
    engine = conn.bind if hasattr(conn, "bind") else conn.engine
    engine_url = str(engine.url)
    is_snowflake = "snowflake" in engine_url.lower()
    is_sqlite = "sqlite" in engine_url.lower()
    is_postgres = "postgres" in engine_url.lower()
    is_mysql = "mysql" in engine_url.lower()

    if is_snowflake:
        # Snowflake-specific DDL
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS baselinr_column_lineage (
                    id INTEGER AUTOINCREMENT PRIMARY KEY,
                    downstream_database VARCHAR(255),
                    downstream_schema VARCHAR(255) NOT NULL,
                    downstream_table VARCHAR(255) NOT NULL,
                    downstream_column VARCHAR(255) NOT NULL,
                    upstream_database VARCHAR(255),
                    upstream_schema VARCHAR(255) NOT NULL,
                    upstream_table VARCHAR(255) NOT NULL,
                    upstream_column VARCHAR(255) NOT NULL,
                    lineage_type VARCHAR(50) NOT NULL,
                    provider VARCHAR(50) NOT NULL,
                    confidence_score FLOAT DEFAULT 1.0,
                    transformation_expression VARCHAR(5000),
                    first_seen_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
                    last_seen_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
                    metadata VARIANT,

                    UNIQUE (
                        downstream_database, downstream_schema, downstream_table,
                        downstream_column, upstream_database, upstream_schema,
                        upstream_table, upstream_column, provider
                    )
                )
            """
            )
        )
        # Create indexes separately for Snowflake
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_lineage_downstream
                ON baselinr_column_lineage (
                    downstream_database, downstream_schema, downstream_table, downstream_column
                )
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_lineage_upstream
                ON baselinr_column_lineage (
                    upstream_database, upstream_schema, upstream_table, upstream_column
                )
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_lineage_provider
                ON baselinr_column_lineage (provider)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_lineage_last_seen
                ON baselinr_column_lineage (last_seen_at DESC)
            """
            )
        )
    elif is_sqlite:
        # SQLite-specific DDL
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS baselinr_column_lineage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    downstream_database VARCHAR(255),
                    downstream_schema VARCHAR(255) NOT NULL,
                    downstream_table VARCHAR(255) NOT NULL,
                    downstream_column VARCHAR(255) NOT NULL,
                    upstream_database VARCHAR(255),
                    upstream_schema VARCHAR(255) NOT NULL,
                    upstream_table VARCHAR(255) NOT NULL,
                    upstream_column VARCHAR(255) NOT NULL,
                    lineage_type VARCHAR(50) NOT NULL,
                    provider VARCHAR(50) NOT NULL,
                    confidence_score FLOAT DEFAULT 1.0,
                    transformation_expression TEXT,
                    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,

                    UNIQUE (
                        downstream_database, downstream_schema, downstream_table,
                        downstream_column, upstream_database, upstream_schema,
                        upstream_table, upstream_column, provider
                    )
                )
            """
            )
        )
        # Create indexes separately for SQLite
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_lineage_downstream
                ON baselinr_column_lineage (
                    downstream_database, downstream_schema, downstream_table, downstream_column
                )
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_lineage_upstream
                ON baselinr_column_lineage (
                    upstream_database, upstream_schema, upstream_table, upstream_column
                )
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_lineage_provider
                ON baselinr_column_lineage (provider)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_lineage_last_seen
                ON baselinr_column_lineage (last_seen_at DESC)
            """
            )
        )
    elif is_postgres:
        # PostgreSQL-specific DDL
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS baselinr_column_lineage (
                    id SERIAL PRIMARY KEY,
                    downstream_database VARCHAR(255),
                    downstream_schema VARCHAR(255) NOT NULL,
                    downstream_table VARCHAR(255) NOT NULL,
                    downstream_column VARCHAR(255) NOT NULL,
                    upstream_database VARCHAR(255),
                    upstream_schema VARCHAR(255) NOT NULL,
                    upstream_table VARCHAR(255) NOT NULL,
                    upstream_column VARCHAR(255) NOT NULL,
                    lineage_type VARCHAR(50) NOT NULL,
                    provider VARCHAR(50) NOT NULL,
                    confidence_score FLOAT DEFAULT 1.0,
                    transformation_expression TEXT,
                    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,

                    UNIQUE (
                        downstream_database, downstream_schema, downstream_table,
                        downstream_column, upstream_database, upstream_schema,
                        upstream_table, upstream_column, provider
                    )
                )
            """
            )
        )
        # Create indexes separately for PostgreSQL
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_lineage_downstream
                ON baselinr_column_lineage (
                    downstream_database, downstream_schema, downstream_table, downstream_column
                )
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_lineage_upstream
                ON baselinr_column_lineage (
                    upstream_database, upstream_schema, upstream_table, upstream_column
                )
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_lineage_provider
                ON baselinr_column_lineage (provider)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_lineage_last_seen
                ON baselinr_column_lineage (last_seen_at DESC)
            """
            )
        )
    elif is_mysql:
        # MySQL-specific DDL
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS baselinr_column_lineage (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    downstream_database VARCHAR(255),
                    downstream_schema VARCHAR(255) NOT NULL,
                    downstream_table VARCHAR(255) NOT NULL,
                    downstream_column VARCHAR(255) NOT NULL,
                    upstream_database VARCHAR(255),
                    upstream_schema VARCHAR(255) NOT NULL,
                    upstream_table VARCHAR(255) NOT NULL,
                    upstream_column VARCHAR(255) NOT NULL,
                    lineage_type VARCHAR(50) NOT NULL,
                    provider VARCHAR(50) NOT NULL,
                    confidence_score FLOAT DEFAULT 1.0,
                    transformation_expression TEXT,
                    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,

                    UNIQUE KEY unique_column_lineage (
                        downstream_database, downstream_schema, downstream_table,
                        downstream_column, upstream_database, upstream_schema,
                        upstream_table, upstream_column, provider
                    ),
                    INDEX idx_downstream (
                        downstream_database, downstream_schema, downstream_table, downstream_column
                    ),
                    INDEX idx_upstream (
                        upstream_database, upstream_schema, upstream_table, upstream_column
                    ),
                    INDEX idx_provider (provider),
                    INDEX idx_last_seen (last_seen_at DESC)
                )
            """
            )
        )
    else:
        # Generic SQL (fallback)
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS baselinr_column_lineage (
                    id SERIAL PRIMARY KEY,
                    downstream_database VARCHAR(255),
                    downstream_schema VARCHAR(255) NOT NULL,
                    downstream_table VARCHAR(255) NOT NULL,
                    downstream_column VARCHAR(255) NOT NULL,
                    upstream_database VARCHAR(255),
                    upstream_schema VARCHAR(255) NOT NULL,
                    upstream_table VARCHAR(255) NOT NULL,
                    upstream_column VARCHAR(255) NOT NULL,
                    lineage_type VARCHAR(50) NOT NULL,
                    provider VARCHAR(50) NOT NULL,
                    confidence_score FLOAT DEFAULT 1.0,
                    transformation_expression TEXT,
                    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,

                    UNIQUE (
                        downstream_database, downstream_schema, downstream_table,
                        downstream_column, upstream_database, upstream_schema,
                        upstream_table, upstream_column, provider
                    )
                )
            """
            )
        )
        # Create indexes separately
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_lineage_downstream
                ON baselinr_column_lineage (
                    downstream_database, downstream_schema, downstream_table, downstream_column
                )
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_lineage_upstream
                ON baselinr_column_lineage (
                    upstream_database, upstream_schema, upstream_table, upstream_column
                )
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_lineage_provider
                ON baselinr_column_lineage (provider)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_lineage_last_seen
                ON baselinr_column_lineage (last_seen_at DESC)
            """
            )
        )


migration = Migration(
    version=5,
    description=(
        "Add column-level lineage table for column-to-column dependency relationships "
        "from multiple providers with transformation expression support"
    ),
    up_python=create_column_lineage_table,
    down_sql="DROP TABLE IF EXISTS baselinr_column_lineage",
)
