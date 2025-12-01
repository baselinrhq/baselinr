"""Schema version management for Baselinr storage layer."""

CURRENT_SCHEMA_VERSION = 7

# Version history
VERSION_HISTORY = {
    1: {
        "description": "Initial schema with runs, results, events, and table_state tables",
        "applied": "2024-01-01",
        "breaking_changes": False,
    },
    2: {
        "description": "Add schema registry table for schema change detection",
        "applied": "2025-11-18",
        "breaking_changes": False,
    },
    3: {
        "description": "Add expectations table for learned metric ranges and control limits",
        "applied": "2025-01-20",
        "breaking_changes": False,
    },
    4: {
        "description": (
            "Add lineage table for data dependency relationships from multiple providers "
            "with database, schema, and table support"
        ),
        "applied": "2025-01-21",
        "breaking_changes": False,
    },
    5: {
        "description": (
            "Add column-level lineage table for column-to-column dependency relationships "
            "from multiple providers with transformation expression support"
        ),
        "applied": "2025-11-26",
        "breaking_changes": False,
    },
    6: {
        "description": (
            "Add RCA tables (pipeline_runs, code_deployments, rca_results) "
            "for root cause analysis of data anomalies"
        ),
        "applied": "2025-12-01",
        "breaking_changes": False,
    },
    7: {
        "description": (
            "Add database_name column to baselinr_rca_results table "
            "to support fully qualified table names in modern warehouses"
        ),
        "applied": "2025-12-01",
        "breaking_changes": False,
    },
}


def get_version_table_ddl(dialect: str = "generic") -> str:
    """
    Get DDL for schema version tracking table.

    Args:
        dialect: Database dialect (generic, snowflake)

    Returns:
        DDL string for creating version table
    """
    if dialect == "snowflake":
        return """
CREATE TABLE IF NOT EXISTS baselinr_schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    description VARCHAR(500),
    migration_script VARCHAR(255),
    checksum VARCHAR(64)
);
"""
    else:
        return """
CREATE TABLE IF NOT EXISTS baselinr_schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description VARCHAR(500),
    migration_script VARCHAR(255),
    checksum VARCHAR(64)
);
"""
