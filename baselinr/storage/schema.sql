-- Baselinr Storage Schema
-- SQL schema for profiling results storage
-- Schema Version: 2

-- Schema version tracking table
CREATE TABLE IF NOT EXISTS baselinr_schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description VARCHAR(500),
    migration_script VARCHAR(255),
    checksum VARCHAR(64)
);

-- Runs table - tracks profiling runs
CREATE TABLE IF NOT EXISTS baselinr_runs (
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
CREATE TABLE IF NOT EXISTS baselinr_results (
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
    FOREIGN KEY (run_id, dataset_name) REFERENCES baselinr_runs(run_id, dataset_name)
);

-- Events table - stores alert events and drift notifications
-- Used by SQL and Snowflake event hooks for historical tracking
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
    timestamp TIMESTAMP NOT NULL,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_event_type (event_type),
    INDEX idx_run_id (run_id),
    INDEX idx_table_name (table_name),
    INDEX idx_timestamp (timestamp DESC),
    INDEX idx_drift_severity (drift_severity)
);

-- Incremental metadata table - tracks last snapshot/change state per table
CREATE TABLE IF NOT EXISTS baselinr_table_state (
    schema_name VARCHAR(255),
    table_name VARCHAR(255) NOT NULL,
    last_run_id VARCHAR(36),
    snapshot_id VARCHAR(255),
    change_token VARCHAR(255),
    decision VARCHAR(50),
    decision_reason VARCHAR(255),
    last_profiled_at TIMESTAMP,
    staleness_score INTEGER,
    row_count BIGINT,
    bytes_scanned BIGINT,
    metadata TEXT,
    PRIMARY KEY (schema_name, table_name)
);

-- Schema registry table - tracks column schemas for change detection
CREATE TABLE IF NOT EXISTS baselinr_schema_registry (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    table_name VARCHAR(255) NOT NULL,
    schema_name VARCHAR(255),
    column_name VARCHAR(255) NOT NULL,
    column_type VARCHAR(100) NOT NULL,
    column_hash VARCHAR(64) NOT NULL,
    nullable BOOLEAN DEFAULT TRUE,
    first_seen_at TIMESTAMP NOT NULL,
    last_seen_at TIMESTAMP NOT NULL,
    run_id VARCHAR(36) NOT NULL,
    INDEX idx_table_schema (table_name, schema_name, run_id),
    INDEX idx_table_column (table_name, schema_name, column_name),
    INDEX idx_run_id (run_id),
    INDEX idx_last_seen (last_seen_at DESC)
);

-- Lineage table - tracks data lineage relationships from multiple providers
CREATE TABLE IF NOT EXISTS baselinr_lineage (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    downstream_database VARCHAR(255),
    downstream_schema VARCHAR(255) NOT NULL,
    downstream_table VARCHAR(255) NOT NULL,
    upstream_database VARCHAR(255),
    upstream_schema VARCHAR(255) NOT NULL,
    upstream_table VARCHAR(255) NOT NULL,
    lineage_type VARCHAR(50) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    confidence_score FLOAT DEFAULT 1.0,
    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,
    UNIQUE KEY unique_lineage (
        downstream_database, downstream_schema, downstream_table,
        upstream_database, upstream_schema, upstream_table, provider
    ),
    INDEX idx_downstream (downstream_database, downstream_schema, downstream_table),
    INDEX idx_upstream (upstream_database, upstream_schema, upstream_table),
    INDEX idx_provider (provider),
    INDEX idx_last_seen (last_seen_at DESC)
);

-- Column lineage table - tracks column-level lineage relationships from multiple providers
CREATE TABLE IF NOT EXISTS baselinr_column_lineage (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
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
    transformation_expression TEXT,
    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,
    UNIQUE KEY unique_column_lineage (
        downstream_database, downstream_schema, downstream_table, downstream_column,
        upstream_database, upstream_schema, upstream_table, upstream_column, provider
    ),
    INDEX idx_downstream (
        downstream_database, downstream_schema, downstream_table, downstream_column
    ),
    INDEX idx_upstream (
        upstream_database, upstream_schema, upstream_table, upstream_column
    ),
    INDEX idx_provider (provider),
    INDEX idx_last_seen (last_seen_at DESC)
);