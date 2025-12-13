"""
Migration v8: Add validation results table

Creates baselinr_validation_results table for storing validation rule execution results.
"""

from sqlalchemy import text

from ..manager import Migration


def create_validation_results_table(conn):
    """Create validation results table with dialect-specific SQL."""
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
                CREATE TABLE IF NOT EXISTS baselinr_validation_results (
                    id INTEGER AUTOINCREMENT PRIMARY KEY,
                    run_id VARCHAR(36) NOT NULL,
                    table_name VARCHAR(255) NOT NULL,
                    schema_name VARCHAR(255),
                    column_name VARCHAR(255),
                    rule_type VARCHAR(50) NOT NULL,
                    rule_config VARIANT,
                    passed BOOLEAN NOT NULL,
                    failure_reason TEXT,
                    total_rows INTEGER,
                    failed_rows INTEGER,
                    failure_rate FLOAT,
                    severity VARCHAR(20),
                    validated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
                    provider VARCHAR(50) NOT NULL DEFAULT 'builtin',
                    metadata VARIANT
                )
            """
            )
        )
        # Create indexes separately for Snowflake
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_validation_run_id
                ON baselinr_validation_results (run_id)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_validation_table
                ON baselinr_validation_results (table_name, schema_name)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_validation_column
                ON baselinr_validation_results (table_name, schema_name, column_name)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_validation_validated_at
                ON baselinr_validation_results (validated_at DESC)
            """
            )
        )
    elif is_sqlite:
        # SQLite-specific DDL
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS baselinr_validation_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id VARCHAR(36) NOT NULL,
                    table_name VARCHAR(255) NOT NULL,
                    schema_name VARCHAR(255),
                    column_name VARCHAR(255),
                    rule_type VARCHAR(50) NOT NULL,
                    rule_config TEXT,
                    passed BOOLEAN NOT NULL,
                    failure_reason TEXT,
                    total_rows INTEGER,
                    failed_rows INTEGER,
                    failure_rate FLOAT,
                    severity VARCHAR(20),
                    validated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    provider VARCHAR(50) NOT NULL DEFAULT 'builtin',
                    metadata TEXT
                )
            """
            )
        )
        # Create indexes separately for SQLite
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_validation_run_id
                ON baselinr_validation_results (run_id)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_validation_table
                ON baselinr_validation_results (table_name, schema_name)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_validation_column
                ON baselinr_validation_results (table_name, schema_name, column_name)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_validation_validated_at
                ON baselinr_validation_results (validated_at DESC)
            """
            )
        )
    else:
        # Generic SQL (PostgreSQL, MySQL, etc.)
        # Detect PostgreSQL vs MySQL
        is_postgres = "postgresql" in engine_url.lower() or "postgres" in engine_url.lower()

        if is_postgres:
            # PostgreSQL-specific DDL
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS baselinr_validation_results (
                        id SERIAL PRIMARY KEY,
                        run_id VARCHAR(36) NOT NULL,
                        table_name VARCHAR(255) NOT NULL,
                        schema_name VARCHAR(255),
                        column_name VARCHAR(255),
                        rule_type VARCHAR(50) NOT NULL,
                        rule_config TEXT,
                        passed BOOLEAN NOT NULL,
                        failure_reason TEXT,
                        total_rows INTEGER,
                        failed_rows INTEGER,
                        failure_rate FLOAT,
                        severity VARCHAR(20),
                        validated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        provider VARCHAR(50) NOT NULL DEFAULT 'builtin',
                        metadata TEXT
                    )
                """
                )
            )
            # Create indexes separately for PostgreSQL
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_validation_run_id
                    ON baselinr_validation_results (run_id)
                """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_validation_table
                    ON baselinr_validation_results (table_name, schema_name)
                """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_validation_column
                    ON baselinr_validation_results (table_name, schema_name, column_name)
                """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_validation_validated_at
                    ON baselinr_validation_results (validated_at DESC)
                """
                )
            )
        else:
            # MySQL and other databases
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS baselinr_validation_results (
                        id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        run_id VARCHAR(36) NOT NULL,
                        table_name VARCHAR(255) NOT NULL,
                        schema_name VARCHAR(255),
                        column_name VARCHAR(255),
                        rule_type VARCHAR(50) NOT NULL,
                        rule_config TEXT,
                        passed BOOLEAN NOT NULL,
                        failure_reason TEXT,
                        total_rows INTEGER,
                        failed_rows INTEGER,
                        failure_rate FLOAT,
                        severity VARCHAR(20),
                        validated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        provider VARCHAR(50) NOT NULL DEFAULT 'builtin',
                        metadata TEXT,
                        INDEX idx_run_id (run_id),
                        INDEX idx_table (table_name, schema_name),
                        INDEX idx_column (table_name, schema_name, column_name),
                        INDEX idx_validated_at (validated_at DESC)
                    )
                """
                )
            )


migration = Migration(
    version=8,
    description=(
        "Add validation results table for storing validation rule execution results "
        "from multiple providers"
    ),
    up_python=create_validation_results_table,
    down_sql="DROP TABLE IF EXISTS baselinr_validation_results",
)
