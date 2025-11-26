-- Initialize PostgreSQL for Baselinr development

-- Create dagster database for Dagster storage
CREATE DATABASE dagster;

-- Switch to baselinr database (created by POSTGRES_DB env var)
\c baselinr;

-- Enable pg_stat_statements extension for query history lineage
-- This extension tracks query execution statistics and is required for
-- PostgreSQL query history lineage extraction.
-- Note: If you have an existing database volume, you may need to recreate it
-- (docker-compose down -v) for shared_preload_libraries to take effect.
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Create sample schema and tables for profiling

-- Customers table
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255) UNIQUE,
    age INTEGER,
    registration_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    total_purchases DECIMAL(10, 2) DEFAULT 0.00,
    customer_segment VARCHAR(50)
);

-- Products table
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    price DECIMAL(10, 2),
    stock_quantity INTEGER,
    manufacturer VARCHAR(100),
    release_date DATE,
    rating DECIMAL(3, 2)
);

-- Orders table
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10, 2),
    status VARCHAR(50),
    shipping_address TEXT,
    delivery_date DATE
);

-- Insert sample data into customers
INSERT INTO customers (first_name, last_name, email, age, registration_date, is_active, total_purchases, customer_segment)
VALUES
    ('John', 'Doe', 'john.doe@example.com', 35, '2023-01-15', TRUE, 1250.50, 'Premium'),
    ('Jane', 'Smith', 'jane.smith@example.com', 28, '2023-02-20', TRUE, 850.75, 'Standard'),
    ('Bob', 'Johnson', 'bob.johnson@example.com', 42, '2023-01-10', TRUE, 2300.00, 'Premium'),
    ('Alice', 'Williams', 'alice.williams@example.com', 31, '2023-03-05', FALSE, 450.25, 'Standard'),
    ('Charlie', 'Brown', 'charlie.brown@example.com', 55, '2023-01-25', TRUE, 3200.00, 'VIP'),
    ('Diana', 'Martinez', 'diana.martinez@example.com', 29, '2023-04-12', TRUE, 680.50, 'Standard'),
    ('Eve', 'Davis', 'eve.davis@example.com', 38, '2023-02-08', TRUE, 1450.00, 'Premium'),
    ('Frank', 'Garcia', 'frank.garcia@example.com', 45, '2023-01-30', FALSE, 120.00, 'Basic'),
    ('Grace', 'Lopez', 'grace.lopez@example.com', 33, '2023-03-15', TRUE, 890.25, 'Standard'),
    ('Henry', 'Wilson', 'henry.wilson@example.com', 50, '2023-02-01', TRUE, 2100.00, 'Premium');

-- Insert sample data into products
INSERT INTO products (product_name, category, price, stock_quantity, manufacturer, release_date, rating)
VALUES
    ('Laptop Pro', 'Electronics', 1299.99, 50, 'TechCorp', '2023-01-01', 4.5),
    ('Wireless Mouse', 'Electronics', 29.99, 200, 'TechCorp', '2023-02-15', 4.2),
    ('Office Chair', 'Furniture', 249.99, 75, 'ComfortCo', '2023-01-20', 4.7),
    ('Desk Lamp', 'Furniture', 45.99, 150, 'LightWorks', '2023-03-01', 4.0),
    ('Notebook Set', 'Stationery', 12.99, 500, 'PaperPlus', '2023-01-10', 4.3),
    ('USB-C Cable', 'Electronics', 15.99, 300, 'TechCorp', '2023-02-20', 4.1),
    ('Standing Desk', 'Furniture', 599.99, 30, 'ComfortCo', '2023-01-15', 4.8),
    ('Webcam HD', 'Electronics', 89.99, 100, 'TechCorp', '2023-03-10', 4.4),
    ('Ergonomic Keyboard', 'Electronics', 79.99, 120, 'TechCorp', '2023-02-05', 4.6),
    ('Monitor 27"', 'Electronics', 399.99, 60, 'DisplayTech', '2023-01-25', 4.7);

-- Insert sample data into orders
INSERT INTO orders (customer_id, order_date, total_amount, status, shipping_address, delivery_date)
VALUES
    (1, '2023-05-01 10:30:00', 1329.98, 'Delivered', '123 Main St, City, State 12345', '2023-05-05'),
    (2, '2023-05-02 14:15:00', 75.98, 'Delivered', '456 Oak Ave, Town, State 67890', '2023-05-06'),
    (3, '2023-05-03 09:45:00', 849.98, 'In Transit', '789 Pine Rd, Village, State 13579', '2023-05-08'),
    (1, '2023-05-04 16:20:00', 45.99, 'Delivered', '123 Main St, City, State 12345', '2023-05-07'),
    (5, '2023-05-05 11:00:00', 1899.97, 'Processing', '321 Elm St, Suburb, State 24680', '2023-05-10'),
    (7, '2023-05-06 13:30:00', 649.98, 'Delivered', '654 Maple Dr, County, State 11223', '2023-05-09'),
    (9, '2023-05-07 10:15:00', 399.99, 'In Transit', '987 Birch Ln, Metro, State 33445', '2023-05-11'),
    (2, '2023-05-08 15:45:00', 92.97, 'Delivered', '456 Oak Ave, Town, State 67890', '2023-05-10'),
    (6, '2023-05-09 12:00:00', 279.98, 'Processing', '147 Cedar Way, District, State 55667', '2023-05-13'),
    (10, '2023-05-10 09:30:00', 1299.99, 'Processing', '258 Spruce Ct, Region, State 77889', '2023-05-14');

-- Create indexes for better performance
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_products_category ON products(category);

-- Create downstream views/tables for lineage testing
-- Customer summary view (depends on customers table)
CREATE OR REPLACE VIEW customer_summary AS
SELECT 
    customer_id,
    first_name || ' ' || last_name AS full_name,
    email,
    age,
    customer_segment,
    total_purchases,
    is_active,
    registration_date,
    CASE 
        WHEN total_purchases > 2000 THEN 'High Value'
        WHEN total_purchases > 1000 THEN 'Medium Value'
        ELSE 'Low Value'
    END AS value_tier
FROM customers;

-- Customer analytics table (depends on customers and orders tables)
-- Drop if exists to allow re-running the init script
DROP TABLE IF EXISTS customer_analytics;

CREATE TABLE customer_analytics AS
SELECT 
    c.customer_id,
    c.customer_segment,
    COUNT(o.order_id) AS total_orders,
    COALESCE(SUM(o.total_amount), 0) AS lifetime_revenue,
    COALESCE(AVG(o.total_amount), 0) AS avg_order_value,
    MAX(o.order_date) AS last_order_date,
    MIN(o.order_date) AS first_order_date
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_segment;

-- Grant permissions
-- Note: GRANT ON ALL TABLES covers both tables and views in PostgreSQL
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO baselinr;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO baselinr;

-- ============================================================================
-- Baselinr Storage Schema
-- ============================================================================
-- Create Baselinr storage tables for profiling results and events
-- Schema Version: 1

-- Schema version tracking table
CREATE TABLE IF NOT EXISTS baselinr_schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description VARCHAR(500),
    migration_script VARCHAR(255),
    checksum VARCHAR(64)
);

-- Runs table - tracks profiling runs
-- Note: Primary key is composite (run_id, dataset_name) to allow multiple tables per run
CREATE TABLE IF NOT EXISTS baselinr_runs (
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
ON baselinr_runs (dataset_name, profiled_at DESC);

-- Results table - stores individual column metrics
CREATE TABLE IF NOT EXISTS baselinr_results (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(36) NOT NULL,
    dataset_name VARCHAR(255) NOT NULL,
    schema_name VARCHAR(255),
    column_name VARCHAR(255) NOT NULL,
    column_type VARCHAR(100),
    metric_name VARCHAR(100) NOT NULL,
    metric_value TEXT,
    profiled_at TIMESTAMP NOT NULL,
    FOREIGN KEY (run_id, dataset_name) REFERENCES baselinr_runs(run_id, dataset_name)
);

-- Create indexes for results table
CREATE INDEX IF NOT EXISTS idx_results_run_id 
ON baselinr_results (run_id);

CREATE INDEX IF NOT EXISTS idx_results_dataset_column 
ON baselinr_results (dataset_name, column_name);

CREATE INDEX IF NOT EXISTS idx_results_metric 
ON baselinr_results (dataset_name, column_name, metric_name);

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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for events table
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

-- Grant permissions on Baselinr tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO baselinr;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO baselinr;

