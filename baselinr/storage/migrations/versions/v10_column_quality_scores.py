"""
Migration v10: Add column quality scores table

Creates baselinr_column_quality_scores table for storing column-level data quality scores.
"""

from sqlalchemy import text

from ..manager import Migration


def create_column_quality_scores_table(conn):
    """Create column quality scores table with dialect-specific SQL."""
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
                CREATE TABLE IF NOT EXISTS baselinr_column_quality_scores (
                    id INTEGER AUTOINCREMENT PRIMARY KEY,
                    table_name VARCHAR(255) NOT NULL,
                    schema_name VARCHAR(255),
                    column_name VARCHAR(255) NOT NULL,
                    run_id VARCHAR(36),
                    overall_score FLOAT NOT NULL,
                    completeness_score FLOAT NOT NULL,
                    validity_score FLOAT NOT NULL,
                    consistency_score FLOAT NOT NULL,
                    freshness_score FLOAT NOT NULL,
                    uniqueness_score FLOAT NOT NULL,
                    accuracy_score FLOAT NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    calculated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
                    period_start TIMESTAMP_NTZ NOT NULL,
                    period_end TIMESTAMP_NTZ NOT NULL
                )
            """
            )
        )
        # Create indexes separately for Snowflake
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_quality_scores_table
                ON baselinr_column_quality_scores (table_name, schema_name, column_name)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_quality_scores_calculated_at
                ON baselinr_column_quality_scores (calculated_at DESC)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_quality_scores_run_id
                ON baselinr_column_quality_scores (run_id)
            """
            )
        )
    elif is_sqlite:
        # SQLite-specific DDL
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS baselinr_column_quality_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name VARCHAR(255) NOT NULL,
                    schema_name VARCHAR(255),
                    column_name VARCHAR(255) NOT NULL,
                    run_id VARCHAR(36),
                    overall_score FLOAT NOT NULL,
                    completeness_score FLOAT NOT NULL,
                    validity_score FLOAT NOT NULL,
                    consistency_score FLOAT NOT NULL,
                    freshness_score FLOAT NOT NULL,
                    uniqueness_score FLOAT NOT NULL,
                    accuracy_score FLOAT NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    calculated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    period_start TIMESTAMP NOT NULL,
                    period_end TIMESTAMP NOT NULL
                )
            """
            )
        )
        # Create indexes separately for SQLite
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_quality_scores_table
                ON baselinr_column_quality_scores (table_name, schema_name, column_name)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_quality_scores_calculated_at
                ON baselinr_column_quality_scores (calculated_at DESC)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_column_quality_scores_run_id
                ON baselinr_column_quality_scores (run_id)
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
                    CREATE TABLE IF NOT EXISTS baselinr_column_quality_scores (
                        id SERIAL PRIMARY KEY,
                        table_name VARCHAR(255) NOT NULL,
                        schema_name VARCHAR(255),
                        column_name VARCHAR(255) NOT NULL,
                        run_id VARCHAR(36),
                        overall_score FLOAT NOT NULL,
                        completeness_score FLOAT NOT NULL,
                        validity_score FLOAT NOT NULL,
                        consistency_score FLOAT NOT NULL,
                        freshness_score FLOAT NOT NULL,
                        uniqueness_score FLOAT NOT NULL,
                        accuracy_score FLOAT NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        calculated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        period_start TIMESTAMP NOT NULL,
                        period_end TIMESTAMP NOT NULL
                    )
                """
                )
            )
            # Create indexes separately for PostgreSQL
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_column_quality_scores_table
                    ON baselinr_column_quality_scores (table_name, schema_name, column_name)
                """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_column_quality_scores_calculated_at
                    ON baselinr_column_quality_scores (calculated_at DESC)
                """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_column_quality_scores_run_id
                    ON baselinr_column_quality_scores (run_id)
                """
                )
            )
        else:
            # MySQL and other databases
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS baselinr_column_quality_scores (
                        id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        table_name VARCHAR(255) NOT NULL,
                        schema_name VARCHAR(255),
                        column_name VARCHAR(255) NOT NULL,
                        run_id VARCHAR(36),
                        overall_score FLOAT NOT NULL,
                        completeness_score FLOAT NOT NULL,
                        validity_score FLOAT NOT NULL,
                        consistency_score FLOAT NOT NULL,
                        freshness_score FLOAT NOT NULL,
                        uniqueness_score FLOAT NOT NULL,
                        accuracy_score FLOAT NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        calculated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        period_start TIMESTAMP NOT NULL,
                        period_end TIMESTAMP NOT NULL,
                        INDEX idx_table (table_name, schema_name, column_name),
                        INDEX idx_calculated_at (calculated_at DESC),
                        INDEX idx_run_id (run_id)
                    )
                """
                )
            )


migration = Migration(
    version=10,
    description="Add column quality scores table for storing column-level data quality scores",
    up_python=create_column_quality_scores_table,
    down_sql="DROP TABLE IF EXISTS baselinr_column_quality_scores",
)
