-- ProfileMesh Storage Schema
-- SQL schema for profiling results storage

-- Runs table - tracks profiling runs
CREATE TABLE IF NOT EXISTS profilemesh_runs (
    run_id VARCHAR(36) NOT NULL,
    dataset_name VARCHAR(255) NOT NULL,
    schema_name VARCHAR(255),
    profiled_at TIMESTAMP NOT NULL,
    environment VARCHAR(50),
    status VARCHAR(20),
    row_count INTEGER,
    column_count INTEGER,
    PRIMARY KEY (run_id, dataset_name),
    INDEX idx_dataset_profiled (dataset_name, profiled_at DESC)
);

-- Results table - stores individual column metrics
CREATE TABLE IF NOT EXISTS profilemesh_results (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    run_id VARCHAR(36) NOT NULL,
    dataset_name VARCHAR(255) NOT NULL,
    schema_name VARCHAR(255),
    column_name VARCHAR(255) NOT NULL,
    column_type VARCHAR(100),
    metric_name VARCHAR(100) NOT NULL,
    metric_value TEXT,
    profiled_at TIMESTAMP NOT NULL,
    INDEX idx_run_id (run_id),
    INDEX idx_dataset_column (dataset_name, column_name),
    INDEX idx_metric (dataset_name, column_name, metric_name),
    FOREIGN KEY (run_id, dataset_name) REFERENCES profilemesh_runs(run_id, dataset_name)
);

-- Events table - stores alert events and drift notifications
-- Used by SQL and Snowflake event hooks for historical tracking
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
    timestamp TIMESTAMP NOT NULL,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_event_type (event_type),
    INDEX idx_table_name (table_name),
    INDEX idx_timestamp (timestamp DESC),
    INDEX idx_drift_severity (drift_severity)
);

