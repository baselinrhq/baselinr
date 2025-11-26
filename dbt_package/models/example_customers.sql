-- Example model for testing dbt integration
-- Used internally to test dbt_ref and dbt_selector patterns

SELECT 
  1 as customer_id,
  'test@example.com' as email,
  '2024-01-01'::date as registration_date,
  'active' as status,
  100.0 as lifetime_value
WHERE 1=0  -- Empty by default for testing
