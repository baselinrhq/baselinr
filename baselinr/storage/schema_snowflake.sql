-- Baselinr Storage Schema for Snowflake
-- Snowflake-specific SQL schema for profiling results storage
-- Schema Version: 1

-- Schema version tracking table
CREATE TABLE IF NOT EXISTS baselinr_schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    description VARCHAR(500),
    migration_script VARCHAR(255),
    checksum VARCHAR(64)
);

-- Runs table - tracks profiling runs
CREATE TABLE IF NOT EXISTS baselinr_runs (
    run_id VARCHAR(36) NOT NULL,
    dataset_name VARCHAR(255) NOT NULL,
    schema_name VARCHAR(255),
    profiled_at TIMESTAMP_NTZ NOT NULL,
    environment VARCHAR(50),
    status VARCHAR(20),
    row_count INTEGER,
    column_count INTEGER,
    PRIMARY KEY (run_id, dataset_name)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_runs_dataset_profiled 
ON baselinr_runs (dataset_name, profiled_at DESC);

-- Results table - stores individual column metrics
CREATE TABLE IF NOT EXISTS baselinr_results (
    id INTEGER AUTOINCREMENT PRIMARY KEY,
    run_id VARCHAR(36) NOT NULL,
    dataset_name VARCHAR(255) NOT NULL,
    schema_name VARCHAR(255),
    column_name VARCHAR(255) NOT NULL,
    column_type VARCHAR(100),
    metric_name VARCHAR(100) NOT NULL,
    metric_value VARCHAR,
    profiled_at TIMESTAMP_NTZ NOT NULL,
    FOREIGN KEY (run_id, dataset_name) REFERENCES baselinr_runs(run_id, dataset_name)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_results_run_id 
ON baselinr_results (run_id);

CREATE INDEX IF NOT EXISTS idx_results_dataset_column 
ON baselinr_results (dataset_name, column_name);

CREATE INDEX IF NOT EXISTS idx_results_metric 
ON baselinr_results (dataset_name, column_name, metric_name);

-- Events table - stores alert events and drift notifications
-- Used by Snowflake event hooks for historical tracking
-- Note: Uses VARIANT type for metadata (Snowflake-specific)
CREATE TABLE IF NOT EXISTS baselinr_events (
    event_id VARCHAR(36) PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    run_id VARCHAR(36),
    table_name VARCHAR(255),
    column_name VARCHAR(255),
    metric_name VARCHAR(100),
    baseline_value FLOAT,
    current_value FLOAT,
    change_percent FLOAT,
    drift_severity VARCHAR(20),
    timestamp TIMESTAMP_NTZ NOT NULL,
    metadata VARIANT,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_events_event_type 
ON baselinr_events (event_type);

CREATE INDEX IF NOT EXISTS idx_events_run_id 
ON baselinr_events (run_id);

CREATE INDEX IF NOT EXISTS idx_events_table_name 
ON baselinr_events (table_name);

CREATE INDEX IF NOT EXISTS idx_events_timestamp 
ON baselinr_events (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_events_drift_severity 
ON baselinr_events (drift_severity);

-- Incremental metadata table - tracks last snapshot/change state per table
CREATE TABLE IF NOT EXISTS baselinr_table_state (
    schema_name VARCHAR(255),
    table_name VARCHAR(255) NOT NULL,
    last_run_id VARCHAR(36),
    snapshot_id VARCHAR(255),
    change_token VARCHAR(255),
    decision VARCHAR(50),
    decision_reason VARCHAR(255),
    last_profiled_at TIMESTAMP_NTZ,
    staleness_score INTEGER,
    row_count NUMBER,
    bytes_scanned NUMBER,
    metadata VARIANT,
    PRIMARY KEY (schema_name, table_name)
);

-- Schema registry table - tracks column schemas for change detection
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
);

-- Create indexes for schema registry
CREATE INDEX IF NOT EXISTS idx_schema_registry_table_schema 
ON baselinr_schema_registry (table_name, schema_name, run_id);

CREATE INDEX IF NOT EXISTS idx_schema_registry_table_column 
ON baselinr_schema_registry (table_name, schema_name, column_name);

CREATE INDEX IF NOT EXISTS idx_schema_registry_run_id 
ON baselinr_schema_registry (run_id);

CREATE INDEX IF NOT EXISTS idx_schema_registry_last_seen 
ON baselinr_schema_registry (last_seen_at DESC);

-- Lineage table - tracks data lineage relationships from multiple providers
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
);

-- Create indexes for lineage table
CREATE INDEX IF NOT EXISTS idx_lineage_downstream 
ON baselinr_lineage (downstream_database, downstream_schema, downstream_table);

CREATE INDEX IF NOT EXISTS idx_lineage_upstream 
ON baselinr_lineage (upstream_database, upstream_schema, upstream_table);

CREATE INDEX IF NOT EXISTS idx_lineage_provider 
ON baselinr_lineage (provider);

CREATE INDEX IF NOT EXISTS idx_lineage_last_seen 
ON baselinr_lineage (last_seen_at DESC);

-- Column lineage table - tracks column-level lineage relationships from multiple providers
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
        downstream_database, downstream_schema, downstream_table, downstream_column,
        upstream_database, upstream_schema, upstream_table, upstream_column, provider
    )
);

-- Create indexes for column lineage table
CREATE INDEX IF NOT EXISTS idx_column_lineage_downstream 
ON baselinr_column_lineage (
    downstream_database, downstream_schema, downstream_table, downstream_column
);

CREATE INDEX IF NOT EXISTS idx_column_lineage_upstream 
ON baselinr_column_lineage (
    upstream_database, upstream_schema, upstream_table, upstream_column
);

CREATE INDEX IF NOT EXISTS idx_column_lineage_provider 
ON baselinr_column_lineage (provider);

CREATE INDEX IF NOT EXISTS idx_column_lineage_last_seen 
ON baselinr_column_lineage (last_seen_at DESC);