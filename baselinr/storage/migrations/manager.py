"""Migration manager for Baselinr storage schemas."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass
class Migration:
    """Represents a schema migration."""

    version: int
    description: str
    up_sql: Optional[str] = None
    up_python: Optional[Callable] = None
    down_sql: Optional[str] = None
    down_python: Optional[Callable] = None

    def validate(self):
        """Ensure migration has at least one up method."""
        if not self.up_sql and not self.up_python:
            raise ValueError(f"Migration v{self.version} must have up_sql or up_python")


class MigrationManager:
    """Manages schema migrations for Baselinr storage."""

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
        query = text(
            """
            SELECT version FROM baselinr_schema_version
            ORDER BY version DESC LIMIT 1
        """
        )
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
                for statement in migration.up_sql.split(";"):
                    statement = statement.strip()
                    if statement:
                        conn.execute(text(statement))

            if migration.up_python:
                migration.up_python(conn)

            # Record migration
            insert_query = text(
                """
                INSERT INTO baselinr_schema_version
                (version, description, applied_at)
                VALUES (:version, :description, :applied_at)
            """
            )
            conn.execute(
                insert_query,
                {
                    "version": migration.version,
                    "description": migration.description,
                    "applied_at": datetime.utcnow(),
                },
            )

            conn.commit()

    def validate_schema(self) -> Dict[str, Any]:
        """
        Validate schema integrity.

        Returns:
            Dict with validation results
        """
        results: Dict[str, Any] = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "version": None,
        }

        try:
            # Check version table exists
            version = self.get_current_version()
            results["version"] = version

            if version is None:
                results["errors"].append("Schema version table missing or empty")
                results["valid"] = False
                return results

            # Check core tables exist
            required_tables = [
                "baselinr_runs",
                "baselinr_results",
                "baselinr_events",
                "baselinr_table_state",
                "baselinr_schema_registry",  # Added in v2
            ]

            with self.engine.connect() as conn:
                for table in required_tables:
                    try:
                        conn.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
                    except Exception as e:
                        results["errors"].append(f"Table {table} missing or inaccessible: {e}")
                        results["valid"] = False

            # Check version matches code
            from ..schema_version import CURRENT_SCHEMA_VERSION

            if version < CURRENT_SCHEMA_VERSION:
                results["warnings"].append(
                    f"Schema version {version} is behind code version {CURRENT_SCHEMA_VERSION}. "
                    "Run migration to upgrade."
                )
            elif version > CURRENT_SCHEMA_VERSION:
                results["errors"].append(
                    f"Schema version {version} is ahead of code version {CURRENT_SCHEMA_VERSION}. "
                    "Update Baselinr package."
                )
                results["valid"] = False

        except Exception as e:
            results["errors"].append(f"Validation failed: {e}")
            results["valid"] = False

        return results
