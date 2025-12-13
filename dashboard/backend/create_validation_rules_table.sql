-- Migration: Create baselinr_validation_rules table
-- This table stores validation rules that can be managed via the API

CREATE TABLE IF NOT EXISTS baselinr_validation_rules (
    id VARCHAR(255) PRIMARY KEY,
    rule_type VARCHAR(50) NOT NULL,
    table_name VARCHAR(255) NOT NULL,
    schema_name VARCHAR(255),
    column_name VARCHAR(255),
    config JSONB NOT NULL DEFAULT '{}',
    severity VARCHAR(20) NOT NULL DEFAULT 'medium',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    last_tested TIMESTAMP,
    last_test_result BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_validation_rules_table ON baselinr_validation_rules(table_name);
CREATE INDEX IF NOT EXISTS idx_validation_rules_schema ON baselinr_validation_rules(schema_name);
CREATE INDEX IF NOT EXISTS idx_validation_rules_type ON baselinr_validation_rules(rule_type);
CREATE INDEX IF NOT EXISTS idx_validation_rules_enabled ON baselinr_validation_rules(enabled);

