-- ProfileMesh Storage Schema for Snowflake
-- Snowflake-specific SQL schema for profiling results storage

-- Runs table - tracks profiling runs
CREATE TABLE IF NOT EXISTS profilemesh_runs (
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
ON profilemesh_runs (dataset_name, profiled_at DESC);

-- Results table - stores individual column metrics
CREATE TABLE IF NOT EXISTS profilemesh_results (
    id INTEGER AUTOINCREMENT PRIMARY KEY,
    run_id VARCHAR(36) NOT NULL,
    dataset_name VARCHAR(255) NOT NULL,
    schema_name VARCHAR(255),
    column_name VARCHAR(255) NOT NULL,
    column_type VARCHAR(100),
    metric_name VARCHAR(100) NOT NULL,
    metric_value VARCHAR,
    profiled_at TIMESTAMP_NTZ NOT NULL,
    FOREIGN KEY (run_id, dataset_name) REFERENCES profilemesh_runs(run_id, dataset_name)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_results_run_id 
ON profilemesh_results (run_id);

CREATE INDEX IF NOT EXISTS idx_results_dataset_column 
ON profilemesh_results (dataset_name, column_name);

CREATE INDEX IF NOT EXISTS idx_results_metric 
ON profilemesh_results (dataset_name, column_name, metric_name);

-- Events table - stores alert events and drift notifications
-- Used by Snowflake event hooks for historical tracking
-- Note: Uses VARIANT type for metadata (Snowflake-specific)
CREATE TABLE IF NOT EXISTS profilemesh_events (
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
ON profilemesh_events (event_type);

CREATE INDEX IF NOT EXISTS idx_events_table_name 
ON profilemesh_events (table_name);

CREATE INDEX IF NOT EXISTS idx_events_timestamp 
ON profilemesh_events (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_events_drift_severity 
ON profilemesh_events (drift_severity);

