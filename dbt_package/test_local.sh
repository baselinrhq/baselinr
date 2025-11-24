#!/bin/bash
# Local test script for dbt integration
# This creates a test dbt project and runs the same tests as CI

set -e

# Create test dbt project
TEST_DIR="/tmp/test_dbt_project_local"
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

# Create dbt_project.yml
cat > dbt_project.yml << 'EOF'
name: 'test_project'
version: '1.0.0'
config-version: 2
profile: 'test_profile'

model-paths: ["models"]
EOF

# Create models directory
mkdir -p models

# Create schema.yml
cat > models/schema.yml << 'EOF'
version: 2

models:
  - name: customers
    description: "Test customer model"
    tags:
      - critical
      - customer
    config:
      materialized: table
  - name: orders
    description: "Test orders model"
    tags:
      - critical
    config:
      materialized: table
  - name: users
    description: "Test users model"
    tags:
      - user
    config:
      materialized: view
EOF

# Create model SQL files
cat > models/customers.sql << 'EOF'
SELECT 
  1 as customer_id,
  'test@example.com' as email,
  '2024-01-01'::date as registration_date
EOF

cat > models/orders.sql << 'EOF'
SELECT 
  1 as order_id,
  1 as customer_id,
  100.0 as amount,
  '2024-01-01'::date as order_date
EOF

cat > models/users.sql << 'EOF'
SELECT 
  1 as user_id,
  'test_user' as username
EOF

# Create profiles directory
mkdir -p profiles
cat > profiles/profiles.yml << 'EOF'
test_profile:
  outputs:
    dev:
      type: postgres
      host: localhost
      port: 5433
      user: baselinr
      password: baselinr
      dbname: baselinr
      schema: public
  target: dev
EOF

echo "Created test dbt project at $TEST_DIR"
echo "Run: cd $TEST_DIR && dbt compile --profiles-dir ./profiles"
echo "Then test with: python -c \"from baselinr.integrations.dbt import DBTManifestParser; parser = DBTManifestParser(manifest_path='$TEST_DIR/target/manifest.json'); models = parser.get_models_by_tag('critical'); print(f'Found {len(models)} models with critical tag')\""

