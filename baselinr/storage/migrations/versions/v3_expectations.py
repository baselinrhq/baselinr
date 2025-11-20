"""
Migration v3: Add expectations table

Creates baselinr_expectations table for storing learned expectations
from historical profiling data, including expected statistics, control limits,
distributions, and categorical frequencies.
"""

from sqlalchemy import text

from ..manager import Migration


def create_expectations_table(conn):
    """Create expectations table with dialect-specific SQL."""
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
                CREATE TABLE IF NOT EXISTS baselinr_expectations (
                    id INTEGER AUTOINCREMENT PRIMARY KEY,
                    table_name VARCHAR(255) NOT NULL,
                    schema_name VARCHAR(255),
                    column_name VARCHAR(255) NOT NULL,
                    metric_name VARCHAR(100) NOT NULL,
                    column_type VARCHAR(100),

                    -- Expected statistics
                    expected_mean FLOAT,
                    expected_variance FLOAT,
                    expected_stddev FLOAT,
                    expected_min FLOAT,
                    expected_max FLOAT,

                    -- Control limits
                    lower_control_limit FLOAT,
                    upper_control_limit FLOAT,
                    lcl_method VARCHAR(50),
                    ucl_method VARCHAR(50),

                    -- EWMA
                    ewma_value FLOAT,
                    ewma_lambda FLOAT DEFAULT 0.2,

                    -- Distribution
                    distribution_type VARCHAR(50),
                    distribution_params TEXT,

                    -- Categorical
                    category_distribution TEXT,

                    -- Learning metadata
                    sample_size INTEGER,
                    learning_window_days INTEGER,
                    last_updated TIMESTAMP_NTZ NOT NULL,
                    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
                    expectation_version INTEGER DEFAULT 1,

                    UNIQUE (table_name, schema_name, column_name, metric_name)
                )
            """
            )
        )
        # Create indexes separately for Snowflake
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_expectations_table_column
                ON baselinr_expectations (table_name, schema_name, column_name)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_expectations_last_updated
                ON baselinr_expectations (last_updated DESC)
            """
            )
        )
    elif is_sqlite:
        # SQLite-specific DDL
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS baselinr_expectations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name VARCHAR(255) NOT NULL,
                    schema_name VARCHAR(255),
                    column_name VARCHAR(255) NOT NULL,
                    metric_name VARCHAR(100) NOT NULL,
                    column_type VARCHAR(100),

                    expected_mean FLOAT,
                    expected_variance FLOAT,
                    expected_stddev FLOAT,
                    expected_min FLOAT,
                    expected_max FLOAT,

                    lower_control_limit FLOAT,
                    upper_control_limit FLOAT,
                    lcl_method VARCHAR(50),
                    ucl_method VARCHAR(50),

                    ewma_value FLOAT,
                    ewma_lambda FLOAT DEFAULT 0.2,

                    distribution_type VARCHAR(50),
                    distribution_params TEXT,

                    category_distribution TEXT,

                    sample_size INTEGER,
                    learning_window_days INTEGER,
                    last_updated TIMESTAMP NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expectation_version INTEGER DEFAULT 1,

                    UNIQUE (table_name, schema_name, column_name, metric_name)
                )
            """
            )
        )
        # Create indexes separately for SQLite
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_expectations_table_column
                ON baselinr_expectations (table_name, schema_name, column_name)
            """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_expectations_last_updated
                ON baselinr_expectations (last_updated DESC)
            """
            )
        )
    else:
        # Generic SQL (PostgreSQL, MySQL, etc.)
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS baselinr_expectations (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    table_name VARCHAR(255) NOT NULL,
                    schema_name VARCHAR(255),
                    column_name VARCHAR(255) NOT NULL,
                    metric_name VARCHAR(100) NOT NULL,
                    column_type VARCHAR(100),

                    -- Expected statistics
                    expected_mean FLOAT,
                    expected_variance FLOAT,
                    expected_stddev FLOAT,
                    expected_min FLOAT,
                    expected_max FLOAT,

                    -- Control limits
                    lower_control_limit FLOAT,
                    upper_control_limit FLOAT,
                    lcl_method VARCHAR(50),
                    ucl_method VARCHAR(50),

                    -- EWMA
                    ewma_value FLOAT,
                    ewma_lambda FLOAT DEFAULT 0.2,

                    -- Distribution
                    distribution_type VARCHAR(50),
                    distribution_params TEXT,

                    -- Categorical
                    category_distribution TEXT,

                    -- Learning metadata
                    sample_size INTEGER,
                    learning_window_days INTEGER,
                    last_updated TIMESTAMP NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expectation_version INTEGER DEFAULT 1,

                    UNIQUE KEY unique_expectation (
                        table_name, schema_name, column_name, metric_name
                    ),
                    INDEX idx_table_column (table_name, schema_name, column_name),
                    INDEX idx_last_updated (last_updated DESC)
                )
            """
            )
        )


migration = Migration(
    version=3,
    description="Add expectations table for learned metric ranges and control limits",
    up_python=create_expectations_table,
    down_sql="DROP TABLE IF EXISTS baselinr_expectations",
)
