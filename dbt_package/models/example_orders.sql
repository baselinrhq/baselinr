-- Example model for testing dbt integration
-- Used internally to test dbt_ref and dbt_selector patterns

SELECT 
  1 as order_id,
  1 as customer_id,
  100.0 as amount,
  '2024-01-01'::date as order_date,
  'completed' as status
WHERE 1=0  -- Empty by default for testing
