-- Example downstream model for testing dbt lineage
-- This model depends on example_customers, creating a lineage relationship

{{ config(materialized='table') }}

SELECT 
    customer_id,
    email,
    registration_date,
    status,
    lifetime_value,
    CASE 
        WHEN lifetime_value > 1000 THEN 'High Value'
        WHEN lifetime_value > 500 THEN 'Medium Value'
        ELSE 'Low Value'
    END AS value_segment,
    CASE 
        WHEN status = 'active' THEN TRUE
        ELSE FALSE
    END AS is_active,
    CURRENT_DATE - registration_date AS days_since_registration
FROM {{ ref('example_customers') }}

