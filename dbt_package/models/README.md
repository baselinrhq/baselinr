# Example Models

This directory contains example models for testing the baselinr dbt integration.

## Models

- **`example_customers.sql`**: Example customer model with tags `critical`, `customer`, `baselinr_test`
- **`example_orders.sql`**: Example orders model with tags `critical`, `order`, `baselinr_test`

## Usage

### 1. Enable Baselinr Integration

Edit `schema.yml` and uncomment the baselinr post-hooks and tests:

```yaml
models:
  - name: example_customers
    config:
      post-hook: "{{ baselinr_profile(target.schema, target.name) }}"  # Uncomment this
    columns:
      - name: customer_id
        tests:
          - baselinr_drift:  # Uncomment this
              metric: count
              threshold: 5.0
              severity: high
```

### 2. Populate Models with Test Data

The example models are empty by default (`WHERE 1=0`). To use them for testing, remove the `WHERE 1=0` clause and add actual data:

```sql
-- example_customers.sql (remove WHERE 1=0 and add data)
SELECT 
  1 as customer_id,
  'test@example.com' as email,
  '2024-01-01'::date as registration_date,
  'active' as status,
  100.0 as lifetime_value
UNION ALL
SELECT 
  2 as customer_id,
  'test2@example.com' as email,
  '2024-01-02'::date as registration_date,
  'active' as status,
  200.0 as lifetime_value
```

### 3. Run Models

```bash
dbt run --select example_customers example_orders
```

### 4. Test with Baselinr

The models are configured with baselinr post-hooks and tests in `schema.yml`. After running the models, profiling and drift detection will execute automatically.

### 5. Use in Baselinr Config

You can reference these models in your baselinr config:

```yaml
profiling:
  tables:
    - dbt_ref: example_customers
      dbt_project_path: ./your_dbt_project
    - dbt_selector: tag:baselinr_test
      dbt_project_path: ./your_dbt_project
```

## Notes

- These models are for **testing purposes only**
- They are included in the package but won't interfere with your actual models
- You can exclude them from production runs using dbt selectors
- Models are tagged with `baselinr_test` for easy filtering
