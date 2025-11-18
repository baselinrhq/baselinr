# Baselinr Schema Migration Guide

This guide explains how to create, test, and apply schema migrations for Baselinr storage layer.

## Overview

Baselinr uses a simple integer-based versioning system for schema migrations. Each migration represents a transition from version N to version N+1.

### Migration System Components

- **Migration Manager** (`baselinr/storage/migrations/manager.py`) - Orchestrates migrations
- **Migration Versions** (`baselinr/storage/migrations/versions/`) - Individual migration files
- **Schema Version Table** (`baselinr_schema_version`) - Tracks applied migrations

---

## Checking Schema Version

### CLI Command

```bash
# Check current schema version
baselinr migrate status --config config.yml
```

**Output:**
```
============================================================
SCHEMA VERSION STATUS
============================================================
Current database version: 1
Current code version: 1

✅ Schema version is up to date
```

### Validation

```bash
# Validate schema integrity
baselinr migrate validate --config config.yml
```

**Output:**
```
Validating schema integrity...

Schema Version: 1
Valid: ✅ Yes
```

---

## Creating a New Migration

### Step 1: Determine Version Number

Migrations must be sequential. If current version is 1, your new migration is version 2.

```bash
# Check current version first
baselinr migrate status --config config.yml
```

### Step 2: Create Migration File

Create a new file: `baselinr/storage/migrations/versions/v{N}_{description}.py`

**Example:** `v2_add_cost_tracking.py`

```python
"""
Migration v2: Add cost tracking fields

Adds cost-related columns to baselinr_runs table for
tracking profiling costs and resource usage.
"""

from ..manager import Migration

# SQL migration
migration = Migration(
    version=2,
    description="Add cost tracking fields to runs table",
    up_sql="""
        ALTER TABLE baselinr_runs 
        ADD COLUMN cost_dollars DECIMAL(10, 4);
        
        ALTER TABLE baselinr_runs 
        ADD COLUMN bytes_scanned BIGINT;
        
        CREATE INDEX idx_runs_cost 
        ON baselinr_runs (cost_dollars);
    """,
    down_sql="""
        -- Rollback (optional - not currently supported)
        DROP INDEX IF EXISTS idx_runs_cost;
        ALTER TABLE baselinr_runs DROP COLUMN bytes_scanned;
        ALTER TABLE baselinr_runs DROP COLUMN cost_dollars;
    """
)
```

### Step 3: Register Migration

Edit `baselinr/storage/migrations/versions/__init__.py`:

```python
"""Migration versions."""
from .v1_initial import migration as v1_migration
from .v2_add_cost_tracking import migration as v2_migration  # Add this line

# Register all migrations here
ALL_MIGRATIONS = [
    v1_migration,
    v2_migration,  # Add this line
]
```

### Step 4: Update Schema Version Constant

Edit `baselinr/storage/schema_version.py`:

```python
CURRENT_SCHEMA_VERSION = 2  # Update this

# Version history
VERSION_HISTORY = {
    1: {
        "description": "Initial schema with runs, results, events, and table_state tables",
        "applied": "2024-01-01",
        "breaking_changes": False
    },
    2: {  # Add this entry
        "description": "Add cost tracking fields",
        "applied": "2024-11-16",
        "breaking_changes": False
    }
}
```

---

## Migration Types

### SQL Migration (Recommended)

Best for schema changes (DDL):

```python
migration = Migration(
    version=2,
    description="Add new column",
    up_sql="""
        ALTER TABLE baselinr_runs 
        ADD COLUMN new_field VARCHAR(100);
    """,
    down_sql=None  # Rollback not required
)
```

### Python Migration

For data transformations (DML):

```python
def migrate_up(conn):
    """Custom Python migration logic."""
    # Example: Populate new column from existing data
    query = text("""
        UPDATE baselinr_runs 
        SET new_field = CONCAT(dataset_name, '_v1')
        WHERE new_field IS NULL
    """)
    conn.execute(query)

migration = Migration(
    version=2,
    description="Populate new field",
    up_python=migrate_up,
    down_python=None
)
```

### Hybrid Migration

Combine SQL and Python:

```python
migration = Migration(
    version=2,
    description="Add and populate field",
    up_sql="ALTER TABLE baselinr_runs ADD COLUMN new_field VARCHAR(100);",
    up_python=migrate_up,
    down_sql=None
)
```

---

## Testing Migrations

### 1. Dry Run

Preview changes without applying:

```bash
baselinr migrate apply --config config.yml --target 2 --dry-run
```

**Output:**
```
🔍 DRY RUN MODE - No changes will be applied

[DRY RUN] Would apply v2: Add cost tracking fields
```

### 2. Test Environment

Always test on a copy of production data:

```bash
# 1. Clone production database
pg_dump prod_db > backup.sql
createdb test_db
psql test_db < backup.sql

# 2. Update config to point to test_db
# 3. Apply migration
baselinr migrate apply --config test_config.yml --target 2

# 4. Validate
baselinr migrate validate --config test_config.yml
```

### 3. Rollback Plan

Document rollback procedure (even if not automated):

```sql
-- Rollback steps for v2
-- 1. Drop new indexes
DROP INDEX IF EXISTS idx_runs_cost;

-- 2. Remove new columns
ALTER TABLE baselinr_runs DROP COLUMN bytes_scanned;
ALTER TABLE baselinr_runs DROP COLUMN cost_dollars;

-- 3. Remove migration record
DELETE FROM baselinr_schema_version WHERE version = 2;
```

---

## Applying Migrations

### Production Migration Checklist

- [ ] Migration tested on copy of production data
- [ ] Rollback procedure documented
- [ ] Backup created
- [ ] Downtime scheduled (if needed)
- [ ] Team notified
- [ ] Monitoring alerts configured

### Apply Migration

```bash
# 1. Backup database
pg_dump prod_db > backup_$(date +%Y%m%d).sql

# 2. Apply migration
baselinr migrate apply --config config.yml --target 2

# Output:
# Applying migration v2: Add cost tracking fields
# ✅ Successfully migrated to version 2

# 3. Verify
baselinr migrate status --config config.yml
baselinr migrate validate --config config.yml
```

### Multi-Version Migration

Skip intermediate versions (applies all):

```bash
# Migrate from v1 → v3 (applies v2 and v3)
baselinr migrate apply --config config.yml --target 3
```

---

## Database-Specific Considerations

### PostgreSQL

```python
# Use IF NOT EXISTS for safety
up_sql="""
    ALTER TABLE baselinr_runs 
    ADD COLUMN IF NOT EXISTS new_field VARCHAR(100);
"""
```

### Snowflake

```python
# Snowflake syntax differences
up_sql="""
    ALTER TABLE baselinr_runs 
    ADD COLUMN new_field VARCHAR(100);
    
    -- Snowflake uses VARIANT for JSON
    ALTER TABLE baselinr_runs 
    ADD COLUMN metadata VARIANT;
"""
```

### MySQL

```python
# MySQL-specific syntax
up_sql="""
    ALTER TABLE baselinr_runs 
    ADD COLUMN new_field VARCHAR(100),
    ADD INDEX idx_new_field (new_field);
"""
```

### SQLite

```python
# SQLite limitations: Can't drop columns
# Must recreate table
up_sql="""
    -- Create new table with new schema
    CREATE TABLE baselinr_runs_new (
        run_id VARCHAR(36) PRIMARY KEY,
        -- ... all columns including new one
    );
    
    -- Copy data
    INSERT INTO baselinr_runs_new 
    SELECT *, NULL as new_field 
    FROM baselinr_runs;
    
    -- Swap tables
    DROP TABLE baselinr_runs;
    ALTER TABLE baselinr_runs_new RENAME TO baselinr_runs;
"""
```

---

## Common Migration Patterns

### Adding a Column

```python
up_sql="""
    ALTER TABLE baselinr_runs 
    ADD COLUMN new_field VARCHAR(100) DEFAULT 'default_value';
"""
```

### Adding an Index

```python
up_sql="""
    CREATE INDEX idx_new_field 
    ON baselinr_runs (new_field);
"""
```

### Adding a New Table

```python
up_sql="""
    CREATE TABLE baselinr_new_feature (
        id INTEGER PRIMARY KEY AUTO_INCREMENT,
        feature_name VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX idx_feature_name 
    ON baselinr_new_feature (feature_name);
"""
```

### Modifying Column Type (Breaking)

```python
# WARNING: This is a breaking change
# Increment version and test thoroughly
up_sql="""
    -- 1. Add new column
    ALTER TABLE baselinr_runs 
    ADD COLUMN row_count_new BIGINT;
    
    -- 2. Copy data
    UPDATE baselinr_runs 
    SET row_count_new = row_count;
    
    -- 3. Drop old column
    ALTER TABLE baselinr_runs 
    DROP COLUMN row_count;
    
    -- 4. Rename new column
    ALTER TABLE baselinr_runs 
    RENAME COLUMN row_count_new TO row_count;
"""
```

---

## Troubleshooting

### Migration Fails Mid-Way

1. Check error message in logs
2. Database may be in inconsistent state
3. Restore from backup
4. Fix migration script
5. Reapply

### Version Mismatch

```
⚠️  Database schema is behind (v1 < v2)
Run: baselinr migrate apply --target 2
```

**Solution:** Apply migrations to bring DB up to date

### Missing Migrations

```
ValueError: Missing migrations for versions: {2}
```

**Solution:** All intermediate migrations must exist

---

## Best Practices

### DO ✅

- Test on copy of production data
- Create backups before migrating
- Use transactions (SQL migrations are auto-wrapped)
- Document breaking changes
- Keep migrations small and focused
- Use descriptive version file names

### DON'T ❌

- Skip version numbers
- Modify existing migrations (create new one instead)
- Run migrations directly on production without testing
- Use migrations for routine data changes
- Ignore migration failures

---

## Migration Workflow Summary

```
1. Check current version
   ↓
2. Create migration file (vN+1)
   ↓
3. Register in versions/__init__.py
   ↓
4. Update CURRENT_SCHEMA_VERSION
   ↓
5. Test with --dry-run
   ↓
6. Test on copy of production
   ↓
7. Create backup
   ↓
8. Apply to production
   ↓
9. Verify with status/validate
   ↓
10. Monitor application logs
```

---

## Additional Resources

- [Schema Reference](./SCHEMA_REFERENCE.md) - Full table documentation
- [Query Examples](./QUERY_EXAMPLES.md) - Common query patterns

---

**Need Help?** Open an issue on GitHub or consult the team.
