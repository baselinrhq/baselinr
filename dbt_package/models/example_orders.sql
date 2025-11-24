-- Example model for testing baselinr dbt integration
--
-- To use this model for testing:
-- 1. Remove the WHERE 1=0 clause
-- 2. Add actual test data or reference a source table
-- 3. Run: dbt run --select example_orders
-- 4. Profiling will run automatically if post-hook is enabled in schema.yml

SELECT 
  1 as order_id,
  1 as customer_id,
  100.0 as amount,
  '2024-01-01'::date as order_date,
  'completed' as status
WHERE 1=0  -- Empty by default - remove this line and add data for testing

