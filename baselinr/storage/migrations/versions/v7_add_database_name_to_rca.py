"""
Migration v7: Add database_name column to baselinr_rca_results table

Adds database_name column to support fully qualified table names in modern warehouses.
"""

from ..manager import Migration


def up_migration(conn):
    """Apply migration - add database_name column."""
    import logging

    from sqlalchemy import text

    logger = logging.getLogger(__name__)

    # Check database type for syntax differences
    try:
        result = conn.execute(text("SELECT VERSION()"))
        db_version = str(result.fetchone()[0]).lower()
        is_snowflake = "snowflake" in db_version
        is_sqlite = "sqlite" in db_version
        is_postgres = "postgresql" in db_version or "postgres" in db_version
    except Exception:
        is_snowflake = False
        is_sqlite = False
        is_postgres = False

    # First, check if table exists
    if is_postgres or is_snowflake:
        check_table = text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_name = 'baselinr_rca_results')"
        )
    elif is_sqlite:
        check_table = text(
            "SELECT EXISTS (SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='baselinr_rca_results')"
        )
    else:
        # MySQL/Generic - try information_schema
        check_table = text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_name = 'baselinr_rca_results')"
        )

    try:
        table_exists = conn.execute(check_table).fetchone()[0]
    except Exception:
        # If we can't check, assume table exists and try to add column
        table_exists = True

    if not table_exists:
        logger.warning(
            "baselinr_rca_results table does not exist. "
            "Creating it now (v6 should have created it)."
        )
        # Create the table with database_name included
        # (v6 should have done this, but if it didn't, we'll do it now)
        if is_snowflake:
            create_table = """
                CREATE TABLE IF NOT EXISTS baselinr_rca_results (
                    id INTEGER AUTOINCREMENT PRIMARY KEY,
                    anomaly_id VARCHAR(255) NOT NULL,
                    database_name VARCHAR(255),
                    table_name VARCHAR(255) NOT NULL,
                    schema_name VARCHAR(255),
                    column_name VARCHAR(255),
                    metric_name VARCHAR(100),
                    analyzed_at TIMESTAMP_NTZ NOT NULL,
                    rca_status VARCHAR(50) DEFAULT 'analyzed',
                    probable_causes VARIANT,
                    impact_analysis VARIANT,
                    metadata VARIANT,
                    UNIQUE (anomaly_id)
                )
            """
        elif is_sqlite:
            create_table = """
                CREATE TABLE IF NOT EXISTS baselinr_rca_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    anomaly_id VARCHAR(255) NOT NULL UNIQUE,
                    database_name VARCHAR(255),
                    table_name VARCHAR(255) NOT NULL,
                    schema_name VARCHAR(255),
                    column_name VARCHAR(255),
                    metric_name VARCHAR(100),
                    analyzed_at TIMESTAMP NOT NULL,
                    rca_status VARCHAR(50) DEFAULT 'analyzed',
                    probable_causes TEXT,
                    impact_analysis TEXT,
                    metadata TEXT
                )
            """
        else:
            # PostgreSQL/MySQL/Generic
            create_table = """
                CREATE TABLE IF NOT EXISTS baselinr_rca_results (
                    id SERIAL PRIMARY KEY,
                    anomaly_id VARCHAR(255) NOT NULL UNIQUE,
                    database_name VARCHAR(255),
                    table_name VARCHAR(255) NOT NULL,
                    schema_name VARCHAR(255),
                    column_name VARCHAR(255),
                    metric_name VARCHAR(100),
                    analyzed_at TIMESTAMP NOT NULL,
                    rca_status VARCHAR(50) DEFAULT 'analyzed',
                    probable_causes TEXT,
                    impact_analysis TEXT,
                    metadata TEXT
                )
            """
        conn.execute(text(create_table))
        logger.info("Created baselinr_rca_results table with database_name column")
        # Create indexes
        indexes = [
            (
                "CREATE INDEX IF NOT EXISTS idx_rca_results_table_name "
                "ON baselinr_rca_results (table_name, schema_name)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_rca_results_analyzed_at "
                "ON baselinr_rca_results (analyzed_at DESC)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_rca_results_status "
                "ON baselinr_rca_results (rca_status)"
            ),
        ]
        for idx_sql in indexes:
            try:
                conn.execute(text(idx_sql))
            except Exception as e:
                logger.debug(f"Index creation skipped: {e}")
        return

    # Check if column already exists (v6 might have already created it with the column)
    if is_postgres or is_snowflake:
        check_column = text(
            "SELECT EXISTS (SELECT FROM information_schema.columns "
            "WHERE table_name = 'baselinr_rca_results' AND column_name = 'database_name')"
        )
    elif is_sqlite:
        # SQLite doesn't have information_schema, check pragma
        check_column = text("PRAGMA table_info(baselinr_rca_results)")
        try:
            columns = conn.execute(check_column).fetchall()
            column_exists = any(col[1] == "database_name" for col in columns)
            if column_exists:
                logger.info("database_name column already exists in baselinr_rca_results table")
                return
        except Exception:
            # If we can't check, try to add it
            pass
    else:
        # MySQL/Generic
        check_column = text(
            "SELECT EXISTS (SELECT FROM information_schema.columns "
            "WHERE table_name = 'baselinr_rca_results' AND column_name = 'database_name')"
        )

    if not is_sqlite:
        try:
            column_exists = conn.execute(check_column).fetchone()[0]
            if column_exists:
                logger.info("database_name column already exists in baselinr_rca_results table")
                return
        except Exception:
            # If we can't check, try to add it
            pass

    # Add database_name column
    if is_snowflake:
        alter_table = """
            ALTER TABLE baselinr_rca_results
            ADD COLUMN IF NOT EXISTS database_name VARCHAR(255)
        """
    elif is_sqlite:
        # SQLite doesn't support ALTER TABLE ADD COLUMN IF NOT EXISTS
        # We'll try to add it and ignore if it already exists
        try:
            alter_table = """
                ALTER TABLE baselinr_rca_results
                ADD COLUMN database_name VARCHAR(255)
            """
            conn.execute(text(alter_table))
        except Exception as e:
            # Column might already exist, that's ok
            logger.debug(f"database_name column may already exist: {e}")
            return
    else:
        # PostgreSQL/MySQL/Generic
        # PostgreSQL doesn't support IF NOT EXISTS in ALTER TABLE ADD COLUMN
        # So we'll try without it and catch the error
        try:
            alter_table = """
                ALTER TABLE baselinr_rca_results
                ADD COLUMN database_name VARCHAR(255)
            """
            conn.execute(text(alter_table))
        except Exception as e:
            # Column might already exist, that's ok
            error_str = str(e).lower()
            if "already exists" in error_str or "duplicate column" in error_str:
                logger.info("database_name column already exists in baselinr_rca_results table")
                return
            else:
                # Re-raise if it's a different error
                raise

    logger.info("Added database_name column to baselinr_rca_results table")


migration = Migration(
    version=7,
    description="Add database_name column to baselinr_rca_results table",
    up_python=up_migration,
    down_sql="ALTER TABLE baselinr_rca_results DROP COLUMN IF EXISTS database_name",
)
