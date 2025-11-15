# Fix: Only One Table Showing in Dashboard

## Problem
When profiling multiple tables in one run, only the first table appears in the dashboard because the `profilemesh_runs` table had `run_id` as the primary key, preventing multiple rows with the same `run_id`.

## Solution
The primary key has been changed to a composite key `(run_id, dataset_name)` to allow each table to have its own run record.

## Fix Existing Database

You have two options:

### Option 1: Recreate Database (Recommended - Fastest)
This will recreate the database with the new schema:

```bash
cd docker
docker compose down -v
docker compose up -d
```

**Note:** This will delete all existing profiling data.

### Option 2: Migrate Existing Database (Preserves Data)
Run the migration script to update the existing table:

```bash
# Using Docker
docker exec -i profilemesh_postgres psql -U profilemesh -d profilemesh < dashboard/backend/migrate_runs_table.sql

# Or using psql directly
psql -h localhost -p 5433 -U profilemesh -d profilemesh -f dashboard/backend/migrate_runs_table.sql
```

**Note:** If you have existing data where multiple tables share the same `run_id`, you may need to re-run profiling to populate the missing run records.

## After Migration

1. **Re-run profiling** to populate run records for all tables:
   ```bash
   profilemesh profile --config examples/config.yml
   ```

2. **Restart the backend** if it's running

3. **Refresh the dashboard** - you should now see all three tables (customers, products, orders)

## What Changed

- **Schema**: Primary key changed from `run_id` to `(run_id, dataset_name)`
- **Writer Logic**: Updated to check for both `run_id` AND `dataset_name` before inserting
- **Result**: Each table in a profiling batch now gets its own run record

