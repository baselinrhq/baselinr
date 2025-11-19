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