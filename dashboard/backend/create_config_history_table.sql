-- Migration: Create baselinr_config_history table
-- This table stores configuration version history for audit and rollback

CREATE TABLE IF NOT EXISTS baselinr_config_history (
    version_id VARCHAR(255) PRIMARY KEY,
    config_json JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    comment TEXT
);

CREATE INDEX IF NOT EXISTS idx_config_history_created_at ON baselinr_config_history(created_at DESC);


