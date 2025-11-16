# Phase 4: Data Layer Enhancements - Implementation Prompt

## Context

ProfileMesh is a data profiling and drift detection tool. You are implementing Phase 4: Data Layer Enhancements to formalize the warehouse storage layer with schema versioning and queryable metadata APIs.

**Current State:**
- ✅ Four tables actively used: `profilemesh_runs`, `profilemesh_results`, `profilemesh_events`, `profilemesh_table_state`
- ✅ Storage writer at `profilemesh/storage/writer.py` handles writes
- ✅ Schema DDL files exist: `profilemesh/storage/schema.sql`, `schema_snowflake.sql`
- ✅ Dashboard REST API exists at `dashboard/backend/main.py` with FastAPI
- ✅ CLI at `profilemesh/cli.py` has `profile`, `drift`, and `plan` commands

**Your Mission:**
Implement schema versioning, migration system, and CLI query commands to make ProfileMesh's data layer production-ready.

---

## Implementation Plan

### Part 1: Schema Versioning (Priority 1)

#### Task 1.1: Create Schema Version Table

Create a new migration to add schema versioning support.

**File: `profilemesh/storage/schema_version.py`**
```python
"""Schema version management for ProfileMesh storage layer."""

CURRENT_SCHEMA_VERSION = 1

# Version history
VERSION_HISTORY = {
    1: {
        "description": "Initial schema with runs, results, events, and table_state tables",
        "applied": "2024-01-01",
        "breaking_changes": False
    }
}

def get_version_table_ddl(dialect: str = "generic") -> str:
    """Get DDL for schema version tracking table."""
    if dialect == "snowflake":
        return """
CREATE TABLE IF NOT EXISTS profilemesh_schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    description VARCHAR(500),
    migration_script VARCHAR(255),
    checksum VARCHAR(64)
);
"""
    else:
        return """
CREATE TABLE IF NOT EXISTS profilemesh_schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description VARCHAR(500),
    migration_script VARCHAR(255),
    checksum VARCHAR(64)
);
"""
```

**Instructions:**
1. Create the file above
2. Update `profilemesh/storage/schema.sql` to include the version table DDL (add at top)
3. Update `profilemesh/storage/schema_snowflake.sql` similarly
4. Update `docker/init_postgres.sql` to include version table

#### Task 1.2: Update ResultWriter to Track Schema Version

Modify `profilemesh/storage/writer.py` to check and record schema version on initialization.

**Instructions:**
1. Import `CURRENT_SCHEMA_VERSION` from `schema_version`
2. In `ResultWriter._create_tables()`, after creating tables, add:
   ```python
   # Initialize or verify schema version
   self._init_schema_version()
   ```
3. Add new method:
   ```python
   def _init_schema_version(self):
       """Initialize or verify schema version."""
       from .schema_version import CURRENT_SCHEMA_VERSION, get_version_table_ddl
       
       # Create version table if it doesn't exist
       with self.engine.connect() as conn:
           dialect = "snowflake" if "snowflake" in str(self.engine.url) else "generic"
           conn.execute(text(get_version_table_ddl(dialect)))
           conn.commit()
           
           # Check current version
           version_query = text("""
               SELECT version FROM profilemesh_schema_version 
               ORDER BY version DESC LIMIT 1
           """)
           result = conn.execute(version_query).fetchone()
           
           if result is None:
               # First time - insert initial version
               insert_query = text("""
                   INSERT INTO profilemesh_schema_version 
                   (version, description, migration_script)
                   VALUES (:version, :description, :script)
               """)
               conn.execute(insert_query, {
                   'version': CURRENT_SCHEMA_VERSION,
                   'description': 'Initial schema version',
                   'script': 'schema.sql'
               })
               conn.commit()
               logger.info(f"Initialized schema version: {CURRENT_SCHEMA_VERSION}")
           else:
               current_version = result[0]
               if current_version != CURRENT_SCHEMA_VERSION:
                   logger.warning(
                       f"Schema version mismatch: DB={current_version}, "
                       f"Code={CURRENT_SCHEMA_VERSION}. Migration may be needed."
                   )
               else:
                   logger.debug(f"Schema version verified: {current_version}")
   
   def get_schema_version(self) -> Optional[int]:
       """Get current schema version from database."""
       query = text("""
           SELECT version FROM profilemesh_schema_version 
           ORDER BY version DESC LIMIT 1
       """)
       with self.engine.connect() as conn:
           result = conn.execute(query).fetchone()
           return result[0] if result else None
   ```

#### Task 1.3: Document Schemas

Create comprehensive schema documentation.

**File: `docs/schemas/SCHEMA_REFERENCE.md`**

Structure the document with:
1. Overview section
2. Table-by-table breakdown with:
   - Purpose and use cases
   - Column definitions with types and constraints
   - Indexes and their rationale
   - Foreign key relationships
   - Example queries
3. Schema versioning policy
4. Breaking vs non-breaking changes

Include this content:
```markdown
# ProfileMesh Storage Schema Reference

Version: 1.0  
Last Updated: 2024-11-16

## Overview

ProfileMesh stores profiling results, run metadata, drift events, and incremental state in four core tables. All tables use a consistent naming convention (`profilemesh_*`) and are designed for multi-tenant, multi-warehouse deployments.

## Core Tables

### 1. profilemesh_runs

**Purpose:** Tracks metadata for each profiling run, including execution time, row counts, and status.

**Schema:**
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| run_id | VARCHAR(36) | PRIMARY KEY | UUID identifying the profiling run |
| dataset_name | VARCHAR(255) | PRIMARY KEY | Table name that was profiled |
| schema_name | VARCHAR(255) | NULL | Schema/database name |
| profiled_at | TIMESTAMP | NOT NULL | When profiling executed |
| environment | VARCHAR(50) | NULL | Environment (dev/staging/prod) |
| status | VARCHAR(20) | NULL | Run status (completed/failed) |
| row_count | INTEGER | NULL | Number of rows profiled |
| column_count | INTEGER | NULL | Number of columns profiled |

**Composite Primary Key:** (run_id, dataset_name) - allows multiple tables in single run

**Indexes:**
- `idx_dataset_profiled` on (dataset_name, profiled_at DESC) - optimizes historical queries per table

**Use Cases:**
- Query run history for a specific table
- Track profiling frequency and status
- Identify failed runs
- Power dashboard overview

**Example Queries:**
```sql
-- Get last 10 runs for a table
SELECT run_id, profiled_at, status, row_count 
FROM profilemesh_runs 
WHERE dataset_name = 'customers' 
ORDER BY profiled_at DESC 
LIMIT 10;

-- Find failed runs in last 7 days
SELECT * FROM profilemesh_runs 
WHERE status = 'failed' 
  AND profiled_at > CURRENT_TIMESTAMP - INTERVAL '7 days';
```

[Continue for each table...]

## Schema Versioning

**Current Version:** 1

**Versioning Policy:**
- Version numbers are integers starting at 1
- Breaking changes increment version
- Non-breaking changes (new optional columns, indexes) don't require version bump
- Schema version tracked in `profilemesh_schema_version` table

**Breaking Changes:**
- Removing columns
- Renaming columns
- Changing column types in incompatible ways
- Removing tables
- Changing primary keys

**Non-Breaking Changes:**
- Adding nullable columns
- Adding indexes
- Adding new tables
- Expanding column sizes
```

---

### Part 2: Migration Framework (Priority 2)

#### Task 2.1: Create Migration Manager

**File: `profilemesh/storage/migrations/__init__.py`**
```python
"""Storage schema migration system."""

from .manager import MigrationManager, Migration

__all__ = ['MigrationManager', 'Migration']
```

**File: `profilemesh/storage/migrations/manager.py`**

Create a complete migration manager with these capabilities:
1. Detect current schema version
2. Apply migrations (up direction)
3. Validate schema state
4. Generate migration templates
5. Support both SQL and Python migrations

```python
"""Migration manager for ProfileMesh storage schemas."""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass
class Migration:
    """Represents a schema migration."""
    version: int
    description: str
    up_sql: Optional[str] = None
    up_python: Optional[callable] = None
    down_sql: Optional[str] = None
    down_python: Optional[callable] = None
    
    def validate(self):
        """Ensure migration has at least one up method."""
        if not self.up_sql and not self.up_python:
            raise ValueError(f"Migration v{self.version} must have up_sql or up_python")


class MigrationManager:
    """Manages schema migrations for ProfileMesh storage."""
    
    def __init__(self, engine: Engine):
        self.engine = engine
        self.migrations: Dict[int, Migration] = {}
    
    def register_migration(self, migration: Migration):
        """Register a migration."""
        migration.validate()
        self.migrations[migration.version] = migration
        logger.debug(f"Registered migration v{migration.version}: {migration.description}")
    
    def get_current_version(self) -> Optional[int]:
        """Get current schema version from database."""
        query = text("""
            SELECT version FROM profilemesh_schema_version 
            ORDER BY version DESC LIMIT 1
        """)
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query).fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.warning(f"Could not read schema version: {e}")
            return None
    
    def migrate_to(self, target_version: int, dry_run: bool = False) -> bool:
        """
        Migrate schema to target version.
        
        Args:
            target_version: Target schema version
            dry_run: If True, only validate without applying
            
        Returns:
            True if successful, False otherwise
        """
        current = self.get_current_version() or 0
        
        if current == target_version:
            logger.info(f"Already at version {target_version}")
            return True
        
        if target_version < current:
            raise ValueError(
                f"Downgrade not supported. Current: {current}, Target: {target_version}"
            )
        
        # Find migrations to apply
        to_apply = [
            self.migrations[v] 
            for v in range(current + 1, target_version + 1)
            if v in self.migrations
        ]
        
        if len(to_apply) != (target_version - current):
            missing = set(range(current + 1, target_version + 1)) - set(self.migrations.keys())
            raise ValueError(f"Missing migrations for versions: {missing}")
        
        logger.info(f"Migrating from v{current} to v{target_version} ({len(to_apply)} migrations)")
        
        if dry_run:
            for migration in to_apply:
                logger.info(f"[DRY RUN] Would apply v{migration.version}: {migration.description}")
            return True
        
        # Apply migrations
        for migration in to_apply:
            logger.info(f"Applying migration v{migration.version}: {migration.description}")
            try:
                self._apply_migration(migration)
            except Exception as e:
                logger.error(f"Migration v{migration.version} failed: {e}")
                return False
        
        logger.info(f"Successfully migrated to v{target_version}")
        return True
    
    def _apply_migration(self, migration: Migration):
        """Apply a single migration."""
        with self.engine.connect() as conn:
            # Execute migration
            if migration.up_sql:
                for statement in migration.up_sql.split(';'):
                    statement = statement.strip()
                    if statement:
                        conn.execute(text(statement))
            
            if migration.up_python:
                migration.up_python(conn)
            
            # Record migration
            insert_query = text("""
                INSERT INTO profilemesh_schema_version 
                (version, description, applied_at)
                VALUES (:version, :description, :applied_at)
            """)
            conn.execute(insert_query, {
                'version': migration.version,
                'description': migration.description,
                'applied_at': datetime.utcnow()
            })
            
            conn.commit()
    
    def validate_schema(self) -> Dict[str, Any]:
        """
        Validate schema integrity.
        
        Returns:
            Dict with validation results
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'version': None
        }
        
        try:
            # Check version table exists
            version = self.get_current_version()
            results['version'] = version
            
            if version is None:
                results['errors'].append("Schema version table missing or empty")
                results['valid'] = False
                return results
            
            # Check core tables exist
            required_tables = [
                'profilemesh_runs',
                'profilemesh_results', 
                'profilemesh_events',
                'profilemesh_table_state'
            ]
            
            with self.engine.connect() as conn:
                for table in required_tables:
                    try:
                        conn.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
                    except Exception as e:
                        results['errors'].append(f"Table {table} missing or inaccessible: {e}")
                        results['valid'] = False
            
            # Check version matches code
            from ..schema_version import CURRENT_SCHEMA_VERSION
            if version < CURRENT_SCHEMA_VERSION:
                results['warnings'].append(
                    f"Schema version {version} is behind code version {CURRENT_SCHEMA_VERSION}. "
                    "Run migration to upgrade."
                )
            elif version > CURRENT_SCHEMA_VERSION:
                results['errors'].append(
                    f"Schema version {version} is ahead of code version {CURRENT_SCHEMA_VERSION}. "
                    "Update ProfileMesh package."
                )
                results['valid'] = False
        
        except Exception as e:
            results['errors'].append(f"Validation failed: {e}")
            results['valid'] = False
        
        return results
```

#### Task 2.2: Create Example Migration

**File: `profilemesh/storage/migrations/versions/__init__.py`**
```python
"""Migration versions."""
from .v1_initial import migration as v1_migration

# Register all migrations here
ALL_MIGRATIONS = [
    v1_migration
]
```

**File: `profilemesh/storage/migrations/versions/v1_initial.py`**
```python
"""
Migration v1: Initial schema baseline

This represents the current schema as the baseline version.
No actual changes needed - just records current state.
"""

from ..manager import Migration

migration = Migration(
    version=1,
    description="Initial schema with runs, results, events, and table_state tables",
    up_sql="""
        -- This migration is a baseline marker
        -- Tables already exist from schema.sql
        SELECT 1;
    """,
    down_sql=None  # Cannot downgrade from baseline
)
```

#### Task 2.3: Add Migration CLI Command

Update `profilemesh/cli.py` to add migration commands.

**Instructions:**
1. Add new imports at top:
```python
from .storage.migrations import MigrationManager
from .storage.migrations.versions import ALL_MIGRATIONS
```

2. Add new function after `plan_command`:
```python
def migrate_command(args):
    """Execute schema migration command."""
    logger.info(f"Loading configuration from: {args.config}")
    
    try:
        # Load configuration
        config = ConfigLoader.load_from_file(args.config)
        
        # Create migration manager
        from .connectors.factory import create_connector
        connector = create_connector(config.storage.connection, config.retry)
        manager = MigrationManager(connector.engine)
        
        # Register all migrations
        for migration in ALL_MIGRATIONS:
            manager.register_migration(migration)
        
        # Execute subcommand
        if args.migrate_command == 'status':
            current = manager.get_current_version()
            from .storage.schema_version import CURRENT_SCHEMA_VERSION
            
            print(f"\n{'='*60}")
            print("SCHEMA VERSION STATUS")
            print(f"{'='*60}")
            print(f"Current database version: {current or 'not initialized'}")
            print(f"Current code version: {CURRENT_SCHEMA_VERSION}")
            
            if current is None:
                print("\n⚠️  Schema version not initialized")
                print("Run: profilemesh migrate apply --target 1")
            elif current < CURRENT_SCHEMA_VERSION:
                print(f"\n⚠️  Database schema is behind (v{current} < v{CURRENT_SCHEMA_VERSION})")
                print(f"Run: profilemesh migrate apply --target {CURRENT_SCHEMA_VERSION}")
            elif current > CURRENT_SCHEMA_VERSION:
                print(f"\n❌ Database schema is ahead (v{current} > v{CURRENT_SCHEMA_VERSION})")
                print("Update ProfileMesh package to match database version")
            else:
                print("\n✅ Schema version is up to date")
        
        elif args.migrate_command == 'apply':
            target = args.target
            dry_run = args.dry_run
            
            if dry_run:
                print("🔍 DRY RUN MODE - No changes will be applied\n")
            
            success = manager.migrate_to(target, dry_run=dry_run)
            
            if success:
                if not dry_run:
                    print(f"\n✅ Successfully migrated to version {target}")
                return 0
            else:
                print(f"\n❌ Migration failed")
                return 1
        
        elif args.migrate_command == 'validate':
            print("Validating schema integrity...\n")
            results = manager.validate_schema()
            
            print(f"Schema Version: {results['version']}")
            print(f"Valid: {'✅ Yes' if results['valid'] else '❌ No'}\n")
            
            if results['errors']:
                print("Errors:")
                for error in results['errors']:
                    print(f"  ❌ {error}")
                print()
            
            if results['warnings']:
                print("Warnings:")
                for warning in results['warnings']:
                    print(f"  ⚠️  {warning}")
                print()
            
            return 0 if results['valid'] else 1
        
        return 0
    
    except Exception as e:
        logger.error(f"Migration command failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1
```

3. Add migrate subcommand to argument parser in `main()`:
```python
# Migrate command
migrate_parser = subparsers.add_parser('migrate', help='Manage schema migrations')
migrate_subparsers = migrate_parser.add_subparsers(dest='migrate_command', help='Migration operation')

# migrate status
status_parser = migrate_subparsers.add_parser('status', help='Show current schema version')
status_parser.add_argument('--config', '-c', required=True, help='Path to configuration file')

# migrate apply
apply_parser = migrate_subparsers.add_parser('apply', help='Apply migrations')
apply_parser.add_argument('--config', '-c', required=True, help='Path to configuration file')
apply_parser.add_argument('--target', type=int, required=True, help='Target schema version')
apply_parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')

# migrate validate
validate_parser = migrate_subparsers.add_parser('validate', help='Validate schema integrity')
validate_parser.add_argument('--config', '-c', required=True, help='Path to configuration file')
```

4. Add to command dispatcher:
```python
elif args.command == 'migrate':
    if not args.migrate_command:
        migrate_parser.print_help()
        return 1
    return migrate_command(args)
```

---

### Part 3: CLI Query Commands (Priority 3)

#### Task 3.1: Create Query Client

**File: `profilemesh/query/__init__.py`**
```python
"""Query module for ProfileMesh metadata."""

from .client import MetadataQueryClient
from .formatters import format_runs, format_drift, format_table

__all__ = ['MetadataQueryClient', 'format_runs', 'format_drift', 'format_table']
```

**File: `profilemesh/query/client.py`**

Create a comprehensive query client with filtering capabilities:

```python
"""Client for querying ProfileMesh metadata from storage."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass
class RunSummary:
    """Summary of a profiling run."""
    run_id: str
    dataset_name: str
    schema_name: Optional[str]
    profiled_at: datetime
    environment: Optional[str]
    status: Optional[str]
    row_count: Optional[int]
    column_count: Optional[int]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'run_id': self.run_id,
            'dataset_name': self.dataset_name,
            'schema_name': self.schema_name,
            'profiled_at': self.profiled_at.isoformat() if self.profiled_at else None,
            'environment': self.environment,
            'status': self.status,
            'row_count': self.row_count,
            'column_count': self.column_count
        }


@dataclass
class DriftEvent:
    """Drift detection event."""
    event_id: str
    event_type: str
    table_name: Optional[str]
    column_name: Optional[str]
    metric_name: Optional[str]
    baseline_value: Optional[float]
    current_value: Optional[float]
    change_percent: Optional[float]
    drift_severity: Optional[str]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'table_name': self.table_name,
            'column_name': self.column_name,
            'metric_name': self.metric_name,
            'baseline_value': self.baseline_value,
            'current_value': self.current_value,
            'change_percent': self.change_percent,
            'drift_severity': self.drift_severity,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class MetadataQueryClient:
    """Client for querying ProfileMesh metadata."""
    
    def __init__(self, engine: Engine, runs_table: str = "profilemesh_runs",
                 results_table: str = "profilemesh_results",
                 events_table: str = "profilemesh_events"):
        self.engine = engine
        self.runs_table = runs_table
        self.results_table = results_table
        self.events_table = events_table
    
    def query_runs(
        self,
        schema: Optional[str] = None,
        table: Optional[str] = None,
        status: Optional[str] = None,
        environment: Optional[str] = None,
        days: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[RunSummary]:
        """
        Query profiling runs with filters.
        
        Args:
            schema: Filter by schema name
            table: Filter by table name
            status: Filter by status
            environment: Filter by environment
            days: Number of days to look back
            limit: Maximum results to return
            offset: Pagination offset
            
        Returns:
            List of RunSummary objects
        """
        conditions = []
        params = {}
        
        if schema:
            conditions.append("schema_name = :schema")
            params['schema'] = schema
        
        if table:
            conditions.append("dataset_name = :table")
            params['table'] = table
        
        if status:
            conditions.append("status = :status")
            params['status'] = status
        
        if environment:
            conditions.append("environment = :environment")
            params['environment'] = environment
        
        if days:
            conditions.append("profiled_at > :start_date")
            params['start_date'] = datetime.utcnow() - timedelta(days=days)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = text(f"""
            SELECT run_id, dataset_name, schema_name, profiled_at,
                   environment, status, row_count, column_count
            FROM {self.runs_table}
            WHERE {where_clause}
            ORDER BY profiled_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        params['limit'] = limit
        params['offset'] = offset
        
        with self.engine.connect() as conn:
            results = conn.execute(query, params).fetchall()
            return [
                RunSummary(
                    run_id=row[0],
                    dataset_name=row[1],
                    schema_name=row[2],
                    profiled_at=row[3],
                    environment=row[4],
                    status=row[5],
                    row_count=row[6],
                    column_count=row[7]
                )
                for row in results
            ]
    
    def query_run_details(self, run_id: str, dataset_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed results for a specific run.
        
        Args:
            run_id: Run ID to query
            dataset_name: Optional dataset name (required if run has multiple tables)
            
        Returns:
            Dictionary with run metadata and metrics
        """
        # Get run metadata
        run_query = text(f"""
            SELECT run_id, dataset_name, schema_name, profiled_at,
                   environment, status, row_count, column_count
            FROM {self.runs_table}
            WHERE run_id = :run_id
            {"AND dataset_name = :dataset_name" if dataset_name else ""}
        """)
        
        params = {'run_id': run_id}
        if dataset_name:
            params['dataset_name'] = dataset_name
        
        with self.engine.connect() as conn:
            run_result = conn.execute(run_query, params).fetchone()
            
            if not run_result:
                return None
            
            # Get metrics
            metrics_query = text(f"""
                SELECT column_name, column_type, metric_name, metric_value
                FROM {self.results_table}
                WHERE run_id = :run_id
                {"AND dataset_name = :dataset_name" if dataset_name else ""}
                ORDER BY column_name, metric_name
            """)
            
            metrics_results = conn.execute(metrics_query, params).fetchall()
            
            # Organize metrics by column
            columns = {}
            for row in metrics_results:
                col_name = row[0]
                if col_name not in columns:
                    columns[col_name] = {
                        'column_name': col_name,
                        'column_type': row[1],
                        'metrics': {}
                    }
                columns[col_name]['metrics'][row[2]] = row[3]
            
            return {
                'run_id': run_result[0],
                'dataset_name': run_result[1],
                'schema_name': run_result[2],
                'profiled_at': run_result[3].isoformat() if run_result[3] else None,
                'environment': run_result[4],
                'status': run_result[5],
                'row_count': run_result[6],
                'column_count': run_result[7],
                'columns': list(columns.values())
            }
    
    def query_drift_events(
        self,
        table: Optional[str] = None,
        severity: Optional[str] = None,
        days: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[DriftEvent]:
        """
        Query drift detection events.
        
        Args:
            table: Filter by table name
            severity: Filter by severity (low/medium/high)
            days: Number of days to look back
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of DriftEvent objects
        """
        conditions = []
        params = {}
        
        if table:
            conditions.append("table_name = :table")
            params['table'] = table
        
        if severity:
            conditions.append("drift_severity = :severity")
            params['severity'] = severity
        
        if days:
            conditions.append("timestamp > :start_date")
            params['start_date'] = datetime.utcnow() - timedelta(days=days)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = text(f"""
            SELECT event_id, event_type, table_name, column_name, metric_name,
                   baseline_value, current_value, change_percent, drift_severity, timestamp
            FROM {self.events_table}
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT :limit OFFSET :offset
        """)
        
        params['limit'] = limit
        params['offset'] = offset
        
        with self.engine.connect() as conn:
            results = conn.execute(query, params).fetchall()
            return [
                DriftEvent(
                    event_id=row[0],
                    event_type=row[1],
                    table_name=row[2],
                    column_name=row[3],
                    metric_name=row[4],
                    baseline_value=row[5],
                    current_value=row[6],
                    change_percent=row[7],
                    drift_severity=row[8],
                    timestamp=row[9]
                )
                for row in results
            ]
    
    def query_table_history(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        days: Optional[int] = 30
    ) -> Dict[str, Any]:
        """
        Get historical profiling data for a specific table.
        
        Args:
            table_name: Table to query
            schema_name: Optional schema name
            days: Number of days of history
            
        Returns:
            Dictionary with run history and trends
        """
        conditions = ["dataset_name = :table"]
        params = {'table': table_name}
        
        if schema_name:
            conditions.append("schema_name = :schema")
            params['schema'] = schema_name
        
        if days:
            conditions.append("profiled_at > :start_date")
            params['start_date'] = datetime.utcnow() - timedelta(days=days)
        
        where_clause = " AND ".join(conditions)
        
        # Get run history
        runs_query = text(f"""
            SELECT run_id, profiled_at, status, row_count, column_count
            FROM {self.runs_table}
            WHERE {where_clause}
            ORDER BY profiled_at DESC
        """)
        
        with self.engine.connect() as conn:
            runs = conn.execute(runs_query, params).fetchall()
            
            return {
                'table_name': table_name,
                'schema_name': schema_name,
                'run_count': len(runs),
                'runs': [
                    {
                        'run_id': row[0],
                        'profiled_at': row[1].isoformat() if row[1] else None,
                        'status': row[2],
                        'row_count': row[3],
                        'column_count': row[4]
                    }
                    for row in runs
                ]
            }
```

#### Task 3.2: Create Output Formatters

**File: `profilemesh/query/formatters.py`**

```python
"""Output formatters for query results."""

import json
from typing import List, Dict, Any
from datetime import datetime


def format_runs(runs: List[Any], format: str = "table") -> str:
    """
    Format run query results.
    
    Args:
        runs: List of RunSummary objects
        format: Output format (table, json, csv)
        
    Returns:
        Formatted string
    """
    if format == "json":
        return json.dumps([run.to_dict() for run in runs], indent=2, default=str)
    
    elif format == "csv":
        if not runs:
            return "run_id,dataset_name,schema_name,profiled_at,environment,status,row_count,column_count"
        
        lines = ["run_id,dataset_name,schema_name,profiled_at,environment,status,row_count,column_count"]
        for run in runs:
            lines.append(
                f"{run.run_id},{run.dataset_name},{run.schema_name or ''},"
                f"{run.profiled_at.isoformat() if run.profiled_at else ''},"
                f"{run.environment or ''},{run.status or ''},{run.row_count or ''},{run.column_count or ''}"
            )
        return "\n".join(lines)
    
    else:  # table format
        if not runs:
            return "No runs found."
        
        # Use tabulate if available, otherwise simple formatting
        try:
            from tabulate import tabulate
            
            headers = ["Run ID", "Table", "Schema", "Profiled At", "Status", "Rows", "Cols"]
            rows = []
            for run in runs:
                rows.append([
                    run.run_id[:8] + "...",
                    run.dataset_name,
                    run.schema_name or "-",
                    run.profiled_at.strftime("%Y-%m-%d %H:%M") if run.profiled_at else "-",
                    run.status or "-",
                    f"{run.row_count:,}" if run.row_count else "-",
                    run.column_count or "-"
                ])
            
            return tabulate(rows, headers=headers, tablefmt="grid")
        
        except ImportError:
            # Fallback to simple formatting
            lines = ["RUN RESULTS", "=" * 80]
            for run in runs:
                lines.append(f"\nRun ID: {run.run_id}")
                lines.append(f"  Table: {run.dataset_name}")
                lines.append(f"  Schema: {run.schema_name or 'N/A'}")
                lines.append(f"  Profiled: {run.profiled_at}")
                lines.append(f"  Status: {run.status}")
                lines.append(f"  Rows: {run.row_count:,}" if run.row_count else "  Rows: N/A")
                lines.append(f"  Columns: {run.column_count}")
            return "\n".join(lines)


def format_drift(events: List[Any], format: str = "table") -> str:
    """Format drift event query results."""
    if format == "json":
        return json.dumps([event.to_dict() for event in events], indent=2, default=str)
    
    elif format == "csv":
        if not events:
            return "event_id,event_type,table_name,column_name,metric_name,baseline_value,current_value,change_percent,severity,timestamp"
        
        lines = ["event_id,event_type,table_name,column_name,metric_name,baseline_value,current_value,change_percent,severity,timestamp"]
        for event in events:
            lines.append(
                f"{event.event_id},{event.event_type},{event.table_name or ''},"
                f"{event.column_name or ''},{event.metric_name or ''},"
                f"{event.baseline_value or ''},{event.current_value or ''},"
                f"{event.change_percent or ''},{event.drift_severity or ''},"
                f"{event.timestamp.isoformat() if event.timestamp else ''}"
            )
        return "\n".join(lines)
    
    else:  # table format
        if not events:
            return "No drift events found."
        
        try:
            from tabulate import tabulate
            
            headers = ["Table", "Column", "Metric", "Baseline", "Current", "Change %", "Severity", "Time"]
            rows = []
            for event in events:
                rows.append([
                    event.table_name or "-",
                    event.column_name or "-",
                    event.metric_name or "-",
                    f"{event.baseline_value:.2f}" if event.baseline_value else "-",
                    f"{event.current_value:.2f}" if event.current_value else "-",
                    f"{event.change_percent:+.1f}%" if event.change_percent else "-",
                    event.drift_severity or "-",
                    event.timestamp.strftime("%Y-%m-%d %H:%M") if event.timestamp else "-"
                ])
            
            return tabulate(rows, headers=headers, tablefmt="grid")
        
        except ImportError:
            lines = ["DRIFT EVENTS", "=" * 80]
            for event in events:
                lines.append(f"\n[{event.drift_severity.upper()}] {event.table_name}.{event.column_name}")
                lines.append(f"  Metric: {event.metric_name}")
                lines.append(f"  Baseline: {event.baseline_value}")
                lines.append(f"  Current: {event.current_value}")
                lines.append(f"  Change: {event.change_percent:+.2f}%" if event.change_percent else "  Change: N/A")
                lines.append(f"  Time: {event.timestamp}")
            return "\n".join(lines)


def format_table_history(data: Dict[str, Any], format: str = "table") -> str:
    """Format table history results."""
    if format == "json":
        return json.dumps(data, indent=2, default=str)
    
    elif format == "csv":
        if not data.get('runs'):
            return "run_id,profiled_at,status,row_count,column_count"
        
        lines = ["run_id,profiled_at,status,row_count,column_count"]
        for run in data['runs']:
            lines.append(
                f"{run['run_id']},{run['profiled_at']},{run['status']},"
                f"{run['row_count'] or ''},{run['column_count'] or ''}"
            )
        return "\n".join(lines)
    
    else:  # table format
        lines = [
            f"TABLE HISTORY: {data['table_name']}",
            "=" * 80,
            f"Schema: {data.get('schema_name') or 'N/A'}",
            f"Total Runs: {data['run_count']}",
            ""
        ]
        
        if not data.get('runs'):
            lines.append("No run history found.")
            return "\n".join(lines)
        
        try:
            from tabulate import tabulate
            
            headers = ["Run ID", "Profiled At", "Status", "Rows", "Columns"]
            rows = []
            for run in data['runs']:
                rows.append([
                    run['run_id'][:8] + "...",
                    run['profiled_at'][:16] if run['profiled_at'] else "-",
                    run['status'] or "-",
                    f"{run['row_count']:,}" if run['row_count'] else "-",
                    run['column_count'] or "-"
                ])
            
            lines.append(tabulate(rows, headers=headers, tablefmt="grid"))
            return "\n".join(lines)
        
        except ImportError:
            for run in data['runs']:
                lines.append(f"\nRun: {run['run_id']}")
                lines.append(f"  Profiled: {run['profiled_at']}")
                lines.append(f"  Status: {run['status']}")
                lines.append(f"  Rows: {run['row_count']:,}" if run['row_count'] else "  Rows: N/A")
            return "\n".join(lines)
```

#### Task 3.3: Add Query CLI Commands

Update `profilemesh/cli.py` to add query commands.

**Instructions:**

1. Add imports:
```python
from .query import MetadataQueryClient, format_runs, format_drift, format_table_history
```

2. Add query command function:
```python
def query_command(args):
    """Execute query command."""
    try:
        # Load configuration
        config = ConfigLoader.load_from_file(args.config)
        
        # Create query client
        from .connectors.factory import create_connector
        connector = create_connector(config.storage.connection, config.retry)
        client = MetadataQueryClient(
            connector.engine,
            runs_table=config.storage.runs_table,
            results_table=config.storage.results_table,
            events_table="profilemesh_events"
        )
        
        # Execute subcommand
        if args.query_command == 'runs':
            runs = client.query_runs(
                schema=args.schema,
                table=args.table,
                status=args.status,
                environment=args.environment,
                days=args.days,
                limit=args.limit,
                offset=args.offset
            )
            
            output = format_runs(runs, format=args.format)
            print(output)
            
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(output)
                logger.info(f"Results saved to: {args.output}")
        
        elif args.query_command == 'drift':
            events = client.query_drift_events(
                table=args.table,
                severity=args.severity,
                days=args.days,
                limit=args.limit,
                offset=args.offset
            )
            
            output = format_drift(events, format=args.format)
            print(output)
            
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(output)
                logger.info(f"Results saved to: {args.output}")
        
        elif args.query_command == 'run':
            details = client.query_run_details(args.run_id, dataset_name=args.table)
            
            if not details:
                print(f"Run {args.run_id} not found")
                return 1
            
            if args.format == 'json':
                output = json.dumps(details, indent=2, default=str)
            else:
                # Pretty print for table format
                output = f"""
RUN DETAILS
{'=' * 80}
Run ID: {details['run_id']}
Dataset: {details['dataset_name']}
Schema: {details.get('schema_name') or 'N/A'}
Profiled: {details['profiled_at']}
Status: {details['status']}
Environment: {details.get('environment') or 'N/A'}
Row Count: {details['row_count']:,}
Column Count: {details['column_count']}

COLUMN METRICS:
"""
                for col in details['columns']:
                    output += f"\n  {col['column_name']} ({col['column_type']}):\n"
                    for metric, value in col['metrics'].items():
                        output += f"    {metric}: {value}\n"
            
            print(output)
            
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(output)
                logger.info(f"Results saved to: {args.output}")
        
        elif args.query_command == 'table':
            history = client.query_table_history(
                args.table,
                schema_name=args.schema,
                days=args.days
            )
            
            output = format_table_history(history, format=args.format)
            print(output)
            
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(output)
                logger.info(f"Results saved to: {args.output}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Query command failed: {e}", exc_info=True)
        print(f"\nError: {e}")
        return 1
```

3. Add query subparser in `main()`:
```python
# Query command
query_parser = subparsers.add_parser('query', help='Query profiling metadata')
query_subparsers = query_parser.add_subparsers(dest='query_command', help='Query type')

# query runs
runs_parser = query_subparsers.add_parser('runs', help='Query profiling runs')
runs_parser.add_argument('--config', '-c', required=True, help='Configuration file')
runs_parser.add_argument('--schema', help='Filter by schema name')
runs_parser.add_argument('--table', help='Filter by table name')
runs_parser.add_argument('--status', choices=['completed', 'failed'], help='Filter by status')
runs_parser.add_argument('--environment', help='Filter by environment')
runs_parser.add_argument('--days', type=int, default=30, help='Days to look back')
runs_parser.add_argument('--limit', type=int, default=100, help='Max results')
runs_parser.add_argument('--offset', type=int, default=0, help='Pagination offset')
runs_parser.add_argument('--format', choices=['table', 'json', 'csv'], default='table')
runs_parser.add_argument('--output', '-o', help='Output file')

# query drift
drift_parser = query_subparsers.add_parser('drift', help='Query drift events')
drift_parser.add_argument('--config', '-c', required=True, help='Configuration file')
drift_parser.add_argument('--table', help='Filter by table name')
drift_parser.add_argument('--severity', choices=['low', 'medium', 'high'], help='Filter by severity')
drift_parser.add_argument('--days', type=int, default=30, help='Days to look back')
drift_parser.add_argument('--limit', type=int, default=100, help='Max results')
drift_parser.add_argument('--offset', type=int, default=0, help='Pagination offset')
drift_parser.add_argument('--format', choices=['table', 'json', 'csv'], default='table')
drift_parser.add_argument('--output', '-o', help='Output file')

# query run (specific run details)
run_parser = query_subparsers.add_parser('run', help='Query specific run details')
run_parser.add_argument('--config', '-c', required=True, help='Configuration file')
run_parser.add_argument('--run-id', required=True, help='Run ID to query')
run_parser.add_argument('--table', help='Dataset name (if run has multiple tables)')
run_parser.add_argument('--format', choices=['table', 'json'], default='table')
run_parser.add_argument('--output', '-o', help='Output file')

# query table (table history)
table_parser = query_subparsers.add_parser('table', help='Query table profiling history')
table_parser.add_argument('--config', '-c', required=True, help='Configuration file')
table_parser.add_argument('--table', required=True, help='Table name')
table_parser.add_argument('--schema', help='Schema name')
table_parser.add_argument('--days', type=int, default=30, help='Days of history')
table_parser.add_argument('--format', choices=['table', 'json', 'csv'], default='table')
table_parser.add_argument('--output', '-o', help='Output file')
```

4. Add to command dispatcher:
```python
elif args.command == 'query':
    if not args.query_command:
        query_parser.print_help()
        return 1
    return query_command(args)
```

---

## Testing Requirements

### Test Migration System
Create `tests/test_migrations.py`:
- Test schema version initialization
- Test migration application
- Test schema validation
- Test version mismatch detection

### Test Query Client
Create `tests/test_query_client.py`:
- Test run queries with various filters
- Test drift event queries
- Test run details retrieval
- Test table history queries
- Test pagination

### Test CLI Commands
Update `tests/test_cli.py`:
- Test `migrate status` command
- Test `migrate validate` command
- Test `query runs` command
- Test `query drift` command
- Test output formats (json, csv, table)

---

## Documentation Requirements

Create these documentation files:

1. **`docs/schemas/SCHEMA_REFERENCE.md`** - Complete schema documentation
2. **`docs/schemas/MIGRATION_GUIDE.md`** - How to create and apply migrations
3. **`docs/schemas/QUERY_EXAMPLES.md`** - CLI query examples and use cases
4. **`docs/guides/DATA_RETENTION.md`** - Data retention best practices (future)

Update existing docs:
- Add migration commands to `README.md`
- Add query commands to CLI help section
- Update `docs/dashboard/README.md` with new API capabilities

---

## Dependencies to Add

Update `requirements.txt` and `setup.py` to include:
```
tabulate>=0.9.0  # For table formatting
```

---

## Success Criteria

✅ **Schema Versioning:**
- [ ] Schema version table created and tracked
- [ ] Version initialization works on first startup
- [ ] Version mismatch warnings displayed correctly

✅ **Migration System:**
- [ ] `profilemesh migrate status` shows current version
- [ ] `profilemesh migrate validate` checks schema integrity
- [ ] `profilemesh migrate apply` can upgrade schemas
- [ ] Dry-run mode works correctly

✅ **Query Commands:**
- [ ] `profilemesh query runs` retrieves and filters runs
- [ ] `profilemesh query drift` retrieves and filters events
- [ ] `profilemesh query run` shows detailed run info
- [ ] `profilemesh query table` shows table history
- [ ] All three output formats work (json, csv, table)

✅ **Documentation:**
- [ ] Schema reference is complete and clear
- [ ] Migration guide explains how to create migrations
- [ ] Query examples demonstrate common use cases

✅ **Tests:**
- [ ] Migration tests pass
- [ ] Query client tests pass
- [ ] CLI command tests pass
- [ ] Integration tests pass

---

## Implementation Order

Follow this sequence for best results:

1. **Day 1-2:** Schema versioning foundation
   - Create `schema_version.py`
   - Update SQL files with version table
   - Modify `ResultWriter` to track version

2. **Day 3-4:** Migration framework
   - Create `MigrationManager` class
   - Create baseline migration
   - Add `migrate` CLI commands

3. **Day 5-6:** Query client
   - Create `MetadataQueryClient`
   - Create output formatters
   - Add comprehensive filtering

4. **Day 7-8:** Query CLI commands
   - Add `query` subcommands to CLI
   - Implement all query types
   - Test all output formats

5. **Day 9:** Testing
   - Write unit tests
   - Write integration tests
   - Test against all supported databases

6. **Day 10:** Documentation
   - Write schema reference
   - Write migration guide
   - Create query examples

---

## Notes and Best Practices

### Schema Versioning
- Always use sequential integer versions (1, 2, 3...)
- Never skip version numbers
- Document breaking vs non-breaking changes
- Keep migrations idempotent when possible

### Migration Design
- Each migration should be atomic
- Prefer SQL migrations for schema changes
- Use Python migrations for data transformations
- Always test rollback paths (even if not implemented)

### Query Performance
- Ensure proper indexes exist for common queries
- Use LIMIT/OFFSET for pagination
- Consider caching for expensive queries
- Monitor query performance in production

### CLI Design
- Provide sensible defaults for all parameters
- Support multiple output formats
- Allow piping output to other commands
- Show progress for long-running operations

---

## Answers to Open Questions

**Q1: Should migrations be automatic or manual?**
**A:** Manual. Use explicit `profilemesh migrate apply` command. This gives users control and prevents unexpected changes in production.

**Q2: Default retention periods?**
**A:** Start without automatic cleanup. Document retention as a future enhancement. Users can manually delete old data if needed.

**Q3: API authentication?**
**A:** Not in Phase 4. The REST API is for the internal dashboard only. Document that it should not be exposed publicly. Add authentication in Phase 5.

**Q4: How many schema versions to support?**
**A:** Support N-1 (previous version) for reading, but always write in current format. Warn users to upgrade within one version cycle.

**Q5: Database-specific migrations?**
**A:** Keep migrations database-agnostic when possible. If DB-specific features needed, use dialect detection and conditional SQL.

---

## Final Checklist

Before considering Phase 4 complete:

- [ ] All new files created and implemented
- [ ] All existing files updated correctly
- [ ] All CLI commands work as documented
- [ ] Tests written and passing
- [ ] Documentation complete
- [ ] Example queries tested
- [ ] Schema versioning works across all supported databases
- [ ] Migration system tested on Postgres, SQLite, and Snowflake
- [ ] Query commands tested with various filters
- [ ] Output formats all work correctly
- [ ] README updated with new commands
- [ ] CHANGELOG updated with Phase 4 features

---

**End of Implementation Prompt**

Use this prompt to guide your implementation. Follow the order, test thoroughly, and document as you go. Good luck! 🚀
