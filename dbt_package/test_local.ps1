# Local test script for dbt integration (PowerShell version)
# This creates a test dbt project and runs the same tests as CI

$ErrorActionPreference = "Stop"

# Create test dbt project
$TEST_DIR = "$env:TEMP\test_dbt_project_local"
if (Test-Path $TEST_DIR) {
    Remove-Item -Recurse -Force $TEST_DIR
}
New-Item -ItemType Directory -Path $TEST_DIR -Force | Out-Null
Set-Location $TEST_DIR

# Create dbt_project.yml
@"
name: 'test_project'
version: '1.0.0'
config-version: 2
profile: 'test_profile'

model-paths: ["models"]
"@ | Out-File -FilePath "dbt_project.yml" -Encoding utf8

# Create models directory
New-Item -ItemType Directory -Path "models" -Force | Out-Null

# Create schema.yml
@"
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
"@ | Out-File -FilePath "models\schema.yml" -Encoding utf8

# Create model SQL files
@"
SELECT 
  1 as customer_id,
  'test@example.com' as email,
  '2024-01-01'::date as registration_date
"@ | Out-File -FilePath "models\customers.sql" -Encoding utf8

@"
SELECT 
  1 as order_id,
  1 as customer_id,
  100.0 as amount,
  '2024-01-01'::date as order_date
"@ | Out-File -FilePath "models\orders.sql" -Encoding utf8

@"
SELECT 
  1 as user_id,
  'test_user' as username
"@ | Out-File -FilePath "models\users.sql" -Encoding utf8

# Create profiles directory
New-Item -ItemType Directory -Path "profiles" -Force | Out-Null
@"
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
"@ | Out-File -FilePath "profiles\profiles.yml" -Encoding utf8

Write-Host "Created test dbt project at $TEST_DIR" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Start PostgreSQL (if using docker-compose):"
Write-Host "   cd ..\docker"
Write-Host "   docker compose up -d postgres"
Write-Host ""
Write-Host "2. Compile the dbt project:"
Write-Host "   cd $TEST_DIR"
Write-Host "   `$env:DBT_PROFILES_DIR='.\profiles'"
Write-Host "   dbt compile --profiles-dir .\profiles"
Write-Host ""
Write-Host "3. Run the test script:"
Write-Host "   cd ..\..\baselinr\dbt_package"
Write-Host "   python test_local.py $TEST_DIR\target\manifest.json"

