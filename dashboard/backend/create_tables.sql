-- ProfileMesh Storage Schema for PostgreSQL
-- Run this script manually if tables don't exist
-- Usage: psql -h localhost -p 5433 -U profilemesh -d profilemesh -f create_tables.sql

-- Runs table - tracks profiling runs
-- Note: Primary key is composite (run_id, dataset_name) to allow multiple tables per run
CREATE TABLE IF NOT EXISTS profilemesh_runs (
    run_id VARCHAR(36) NOT NULL,
    dataset_name VARCHAR(255) NOT NULL,
    schema_name VARCHAR(255),
    profiled_at TIMESTAMP NOT NULL,
    environment VARCHAR(50),
    status VARCHAR(20),
    row_count INTEGER,
    column_count INTEGER,
    PRIMARY KEY (run_id, dataset_name)
);

-- Create index for runs table
CREATE INDEX IF NOT EXISTS idx_runs_dataset_profiled 
ON profilemesh_runs (dataset_name, profiled_at DESC);

-- Results table - stores individual column metrics
CREATE TABLE IF NOT EXISTS profilemesh_results (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(36) NOT NULL,
    dataset_name VARCHAR(255) NOT NULL,
    schema_name VARCHAR(255),
    column_name VARCHAR(255) NOT NULL,
    column_type VARCHAR(100),
    metric_name VARCHAR(100) NOT NULL,
    metric_value TEXT,
    profiled_at TIMESTAMP NOT NULL,
    FOREIGN KEY (run_id) REFERENCES profilemesh_runs(run_id)
);

-- Create indexes for results table
CREATE INDEX IF NOT EXISTS idx_results_run_id 
ON profilemesh_results (run_id);

CREATE INDEX IF NOT EXISTS idx_results_dataset_column 
ON profilemesh_results (dataset_name, column_name);

CREATE INDEX IF NOT EXISTS idx_results_metric 
ON profilemesh_results (dataset_name, column_name, metric_name);

-- Events table - stores alert events and drift notifications
CREATE TABLE IF NOT EXISTS profilemesh_events (
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
    timestamp TIMESTAMP NOT NULL,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for events table
CREATE INDEX IF NOT EXISTS idx_events_event_type 
ON profilemesh_events (event_type);

CREATE INDEX IF NOT EXISTS idx_events_run_id 
ON profilemesh_events (run_id);

CREATE INDEX IF NOT EXISTS idx_events_table_name 
ON profilemesh_events (table_name);

CREATE INDEX IF NOT EXISTS idx_events_timestamp 
ON profilemesh_events (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_events_drift_severity 
ON profilemesh_events (drift_severity);

