"""
Migration v2: Add schema registry table

Creates baselinr_schema_registry table for tracking schema snapshots
and detecting schema changes over time.
"""

from sqlalchemy import text

from ..manager import Migration


def create_schema_registry_table(conn):
    """Create schema registry table with dialect-specific SQL."""
    # Get engine URL from connection
    # Connection object has a bind attribute that is the engine
    engine = conn.bind if hasattr(conn, "bind") else conn.engine
    engine_url = str(engine.url)
    is_snowflake = "snowflake" in engine_url.lower()
    is_sqlite = "sqlite" in engine_url.lower()

    if is_snowflake:
        # Snowflake-specific DDL
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS baselinr_schema_registry (
                    id INTEGER AUTOINCREMENT PRIMARY KEY,
                    table_name VARCHAR(255) NOT NULL,
                    schema_name VARCHAR(255),
                    column_name VARCHAR(255) NOT NULL,
                    column_type VARCHAR(100) NOT NULL,
                    column_hash VARCHAR(64) NOT NULL,
                    nullable BOOLEAN DEFAULT TRUE,
                    first_seen_at TIMESTAMP_NTZ NOT NULL,
                    last_seen_at TIMESTAMP_NTZ NOT NULL,
                    run_id VARCHAR(36) NOT NULL
                )
            """
            )
        )
        # Create indexes separately for Snowflake
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_schema_registry_table_schema
                ON baselinr_schema_registry (table_name, schema_name, run_id)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_schema_registry_table_column
                ON baselinr_schema_registry (table_name, schema_name, column_name)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_schema_registry_run_id
                ON baselinr_schema_registry (run_id)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_schema_registry_last_seen
                ON baselinr_schema_registry (last_seen_at DESC)
            """
            )
        )
    elif is_sqlite:
        # SQLite-specific DDL
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS baselinr_schema_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name VARCHAR(255) NOT NULL,
                    schema_name VARCHAR(255),
                    column_name VARCHAR(255) NOT NULL,
                    column_type VARCHAR(100) NOT NULL,
                    column_hash VARCHAR(64) NOT NULL,
                    nullable BOOLEAN DEFAULT TRUE,
                    first_seen_at TIMESTAMP NOT NULL,
                    last_seen_at TIMESTAMP NOT NULL,
                    run_id VARCHAR(36) NOT NULL
                )
            """
            )
        )
        # Create indexes separately for SQLite
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_schema_registry_table_schema
                ON baselinr_schema_registry (table_name, schema_name, run_id)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_schema_registry_table_column
                ON baselinr_schema_registry (table_name, schema_name, column_name)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_schema_registry_run_id
                ON baselinr_schema_registry (run_id)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_schema_registry_last_seen
                ON baselinr_schema_registry (last_seen_at DESC)
            """
            )
        )
    else:
        # Generic SQL (PostgreSQL, MySQL, etc.)
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS baselinr_schema_registry (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    table_name VARCHAR(255) NOT NULL,
                    schema_name VARCHAR(255),
                    column_name VARCHAR(255) NOT NULL,
                    column_type VARCHAR(100) NOT NULL,
                    column_hash VARCHAR(64) NOT NULL,
                    nullable BOOLEAN DEFAULT TRUE,
                    first_seen_at TIMESTAMP NOT NULL,
                    last_seen_at TIMESTAMP NOT NULL,
                    run_id VARCHAR(36) NOT NULL,
                    INDEX idx_table_schema (table_name, schema_name, run_id),
                    INDEX idx_table_column (table_name, schema_name, column_name),
                    INDEX idx_run_id (run_id),
                    INDEX idx_last_seen (last_seen_at DESC)
                )
            """
            )
        )


migration = Migration(
    version=2,
    description="Add schema registry table for schema change detection",
    up_python=create_schema_registry_table,
    down_sql="DROP TABLE IF EXISTS baselinr_schema_registry",
)
