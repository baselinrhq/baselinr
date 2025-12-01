"""
Migration v6: Add RCA (Root Cause Analysis) tables

Adds tables for pipeline runs, code deployments, and extends anomalies
table with RCA-related fields.
"""

from ..manager import Migration


def up_migration(conn):
    """Apply migration - create RCA tables."""
    import logging

    logger = logging.getLogger(__name__)

    # Check database type for syntax differences
    from sqlalchemy import text

    try:
        # Try to detect database type from connection
        result = conn.execute(text("SELECT VERSION()"))
        db_version = str(result.fetchone()[0]).lower()
        is_snowflake = "snowflake" in db_version
        is_sqlite = "sqlite" in db_version
    except Exception:
        # Fallback: assume generic SQL
        is_snowflake = False
        is_sqlite = False

    # Create pipeline_runs table
    if is_snowflake:
        create_pipeline_runs = """
            CREATE TABLE IF NOT EXISTS baselinr_pipeline_runs (
                run_id VARCHAR(255) PRIMARY KEY,
                pipeline_name VARCHAR(255) NOT NULL,
                pipeline_type VARCHAR(100),
                started_at TIMESTAMP_NTZ NOT NULL,
                completed_at TIMESTAMP_NTZ,
                duration_seconds FLOAT,
                status VARCHAR(50) NOT NULL,
                input_row_count BIGINT,
                output_row_count BIGINT,
                git_commit_sha VARCHAR(255),
                git_branch VARCHAR(255),
                affected_tables VARIANT,
                metadata VARIANT,
                created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
            )
        """
    elif is_sqlite:
        create_pipeline_runs = """
            CREATE TABLE IF NOT EXISTS baselinr_pipeline_runs (
                run_id VARCHAR(255) PRIMARY KEY,
                pipeline_name VARCHAR(255) NOT NULL,
                pipeline_type VARCHAR(100),
                started_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                duration_seconds REAL,
                status VARCHAR(50) NOT NULL,
                input_row_count INTEGER,
                output_row_count INTEGER,
                git_commit_sha VARCHAR(255),
                git_branch VARCHAR(255),
                affected_tables TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
    else:
        # PostgreSQL/MySQL/Generic
        create_pipeline_runs = """
            CREATE TABLE IF NOT EXISTS baselinr_pipeline_runs (
                run_id VARCHAR(255) PRIMARY KEY,
                pipeline_name VARCHAR(255) NOT NULL,
                pipeline_type VARCHAR(100),
                started_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                duration_seconds FLOAT,
                status VARCHAR(50) NOT NULL,
                input_row_count BIGINT,
                output_row_count BIGINT,
                git_commit_sha VARCHAR(255),
                git_branch VARCHAR(255),
                affected_tables TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """

    conn.execute(text(create_pipeline_runs))
    logger.info("Created baselinr_pipeline_runs table")

    # Create code_deployments table
    if is_snowflake:
        create_code_deployments = """
            CREATE TABLE IF NOT EXISTS baselinr_code_deployments (
                deployment_id VARCHAR(255) PRIMARY KEY,
                deployed_at TIMESTAMP_NTZ NOT NULL,
                git_commit_sha VARCHAR(255),
                git_branch VARCHAR(255),
                changed_files VARIANT,
                deployment_type VARCHAR(50),
                affected_pipelines VARIANT,
                metadata VARIANT,
                created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
            )
        """
    elif is_sqlite:
        create_code_deployments = """
            CREATE TABLE IF NOT EXISTS baselinr_code_deployments (
                deployment_id VARCHAR(255) PRIMARY KEY,
                deployed_at TIMESTAMP NOT NULL,
                git_commit_sha VARCHAR(255),
                git_branch VARCHAR(255),
                changed_files TEXT,
                deployment_type VARCHAR(50),
                affected_pipelines TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
    else:
        # PostgreSQL/MySQL/Generic
        create_code_deployments = """
            CREATE TABLE IF NOT EXISTS baselinr_code_deployments (
                deployment_id VARCHAR(255) PRIMARY KEY,
                deployed_at TIMESTAMP NOT NULL,
                git_commit_sha VARCHAR(255),
                git_branch VARCHAR(255),
                changed_files TEXT,
                deployment_type VARCHAR(50),
                affected_pipelines TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """

    conn.execute(text(create_code_deployments))
    logger.info("Created baselinr_code_deployments table")

    # Create RCA results table
    if is_snowflake:
        create_rca_results = """
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
        create_rca_results = """
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
        create_rca_results = """
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

    conn.execute(text(create_rca_results))
    logger.info("Created baselinr_rca_results table")

    # Create indexes for pipeline_runs
    pipeline_run_indexes = [
        (
            "CREATE INDEX IF NOT EXISTS idx_pipeline_runs_pipeline_name "
            "ON baselinr_pipeline_runs (pipeline_name)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at "
            "ON baselinr_pipeline_runs (started_at DESC)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status "
            "ON baselinr_pipeline_runs (status)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_pipeline_runs_git_commit "
            "ON baselinr_pipeline_runs (git_commit_sha)"
        ),
    ]

    for idx_sql in pipeline_run_indexes:
        try:
            conn.execute(text(idx_sql))
        except Exception as e:
            logger.debug(f"Index creation skipped (may already exist): {e}")

    # Create indexes for code_deployments
    deployment_indexes = [
        (
            "CREATE INDEX IF NOT EXISTS idx_code_deployments_deployed_at "
            "ON baselinr_code_deployments (deployed_at DESC)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_code_deployments_git_commit "
            "ON baselinr_code_deployments (git_commit_sha)"
        ),
    ]

    for idx_sql in deployment_indexes:
        try:
            conn.execute(text(idx_sql))
        except Exception as e:
            logger.debug(f"Index creation skipped (may already exist): {e}")

    # Create indexes for RCA results
    rca_indexes = [
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

    for idx_sql in rca_indexes:
        try:
            conn.execute(text(idx_sql))
        except Exception as e:
            logger.debug(f"Index creation skipped (may already exist): {e}")

    logger.info("Created indexes for RCA tables")


migration = Migration(
    version=6,
    description="Add RCA tables (pipeline_runs, code_deployments, rca_results)",
    up_python=up_migration,
    down_sql=None,  # Downgrade not supported
)
