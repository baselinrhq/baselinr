-- Migration: Create baselinr_saved_connections table
-- This table stores saved database connections with encrypted passwords

CREATE TABLE IF NOT EXISTS baselinr_saved_connections (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    connection_json JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    last_tested TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_connections_name ON baselinr_saved_connections(name);


