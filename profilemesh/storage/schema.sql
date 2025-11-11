-- ProfileMesh Storage Schema
-- SQL schema for profiling results storage

-- Runs table - tracks profiling runs
CREATE TABLE IF NOT EXISTS profilemesh_runs (
    run_id VARCHAR(36) PRIMARY KEY,
    dataset_name VARCHAR(255) NOT NULL,
    schema_name VARCHAR(255),
    profiled_at TIMESTAMP NOT NULL,
    environment VARCHAR(50),
    status VARCHAR(20),
    row_count INTEGER,
    column_count INTEGER,
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
    FOREIGN KEY (run_id) REFERENCES profilemesh_runs(run_id)
);

