-- Example model for testing baselinr dbt integration
-- This model can be used to test profiling and drift detection
--
-- To use this model for testing:
-- 1. Remove the WHERE 1=0 clause
-- 2. Add actual test data or reference a source table
-- 3. Run: dbt run --select example_customers
-- 4. Profiling will run automatically if post-hook is enabled in schema.yml

SELECT 
  1 as customer_id,
  'test@example.com' as email,
  '2024-01-01'::date as registration_date,
  'active' as status,
  100.0 as lifetime_value
WHERE 1=0  -- Empty by default - remove this line and add data for testing

