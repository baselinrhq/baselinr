# Fix Missing Database Tables

If you're getting errors like `relation "profilemesh_events" does not exist`, the ProfileMesh storage tables haven't been created yet.

## Quick Fix Options

### Option 1: Recreate Database (Recommended for Development)

This will recreate the database with all tables:

```bash
# From the profile_mesh directory
cd docker
docker compose down -v
docker compose up -d
```

This will:
- Remove all volumes (including database data)
- Recreate containers
- Run `init_postgres.sql` which now includes ProfileMesh storage schema

**Note:** This will delete all existing data in the database.

### Option 2: Manually Create Tables (Preserves Existing Data)

If you want to keep existing data, run the SQL script manually:

```bash
# Using psql
psql -h localhost -p 5433 -U profilemesh -d profilemesh -f dashboard/backend/create_tables.sql

# Or using Docker
docker exec -i profilemesh_postgres psql -U profilemesh -d profilemesh < dashboard/backend/create_tables.sql
```

### Option 3: Create Tables via Python Script

You can also create tables programmatically:

```python
from sqlalchemy import create_engine, text

engine = create_engine("postgresql://profilemesh:profilemesh@localhost:5433/profilemesh")

with open("dashboard/backend/create_tables.sql", "r") as f:
    sql = f.read()

with engine.connect() as conn:
    conn.execute(text(sql))
    conn.commit()
```

## Verify Tables Were Created

After running any of the above options, verify the tables exist:

```sql
-- Connect to database
psql -h localhost -p 5433 -U profilemesh -d profilemesh

-- List tables
\dt profilemesh_*

-- Should show:
-- profilemesh_events
-- profilemesh_results  
-- profilemesh_runs
```

## What Was Fixed

1. **Added ProfileMesh storage schema to `init_postgres.sql`** - Tables will be created automatically on fresh database initialization
2. **Updated event hooks to include `run_id`** - Events now store `run_id` when available in metadata
3. **Created `create_tables.sql`** - Standalone script for manual table creation

## Next Steps

After creating the tables:
1. Restart your backend API
2. The dashboard should now work without errors
3. Run a profiling job to populate the tables with data

