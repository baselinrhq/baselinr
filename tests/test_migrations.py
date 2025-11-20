"""Tests for schema migration system."""

import pytest
from sqlalchemy import create_engine, text

from baselinr.storage.migrations import Migration, MigrationManager
from baselinr.storage.schema_version import CURRENT_SCHEMA_VERSION


@pytest.fixture
def temp_db_engine():
    """Create temporary SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    yield engine
    engine.dispose()


@pytest.fixture
def migration_manager(temp_db_engine):
    """Create migration manager with test database."""
    # Create version table
    with temp_db_engine.connect() as conn:
        conn.execute(
            text(
                """
            CREATE TABLE baselinr_schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                description VARCHAR(500),
                migration_script VARCHAR(255),
                checksum VARCHAR(64)
            )
        """
            )
        )
        conn.commit()

    return MigrationManager(temp_db_engine)


def test_migration_validation():
    """Test migration validation."""
    # Valid migration with SQL
    migration = Migration(version=1, description="Test migration", up_sql="SELECT 1")
    migration.validate()  # Should not raise

    # Valid migration with Python
    def migrate_up(conn):
        pass

    migration = Migration(version=1, description="Test migration", up_python=migrate_up)
    migration.validate()  # Should not raise

    # Invalid migration with neither
    with pytest.raises(ValueError, match="must have up_sql or up_python"):
        migration = Migration(version=1, description="Invalid migration")
        migration.validate()


def test_get_current_version_empty(migration_manager):
    """Test getting version from empty database."""
    version = migration_manager.get_current_version()
    assert version is None


def test_get_current_version_with_data(migration_manager, temp_db_engine):
    """Test getting version from database with migrations."""
    # Insert a version
    with temp_db_engine.connect() as conn:
        conn.execute(
            text(
                """
            INSERT INTO baselinr_schema_version (version, description)
            VALUES (1, 'Initial version')
        """
            )
        )
        conn.commit()

    version = migration_manager.get_current_version()
    assert version == 1


def test_register_migration(migration_manager):
    """Test registering migrations."""
    migration = Migration(version=1, description="Test migration", up_sql="SELECT 1")

    migration_manager.register_migration(migration)
    assert 1 in migration_manager.migrations
    assert migration_manager.migrations[1] == migration


def test_migrate_to_same_version(migration_manager, temp_db_engine):
    """Test migrating to current version."""
    # Set version to 1
    with temp_db_engine.connect() as conn:
        conn.execute(
            text(
                """
            INSERT INTO baselinr_schema_version (version, description)
            VALUES (1, 'Current version')
        """
            )
        )
        conn.commit()

    migration = Migration(version=1, description="Test", up_sql="SELECT 1")
    migration_manager.register_migration(migration)

    # Migrate to same version
    result = migration_manager.migrate_to(1)
    assert result is True


def test_migrate_downgrade_not_supported(migration_manager, temp_db_engine):
    """Test that downgrade raises error."""
    # Set version to 2
    with temp_db_engine.connect() as conn:
        conn.execute(
            text(
                """
            INSERT INTO baselinr_schema_version (version, description)
            VALUES (2, 'Current version')
        """
            )
        )
        conn.commit()

    # Try to downgrade to 1
    with pytest.raises(ValueError, match="Downgrade not supported"):
        migration_manager.migrate_to(1)


def test_migrate_missing_migration(migration_manager):
    """Test migrating with missing intermediate version."""
    migration1 = Migration(version=1, description="V1", up_sql="SELECT 1")
    migration3 = Migration(version=3, description="V3", up_sql="SELECT 1")

    migration_manager.register_migration(migration1)
    migration_manager.register_migration(migration3)

    # Try to migrate to 3 (missing v2)
    with pytest.raises(ValueError, match="Missing migrations"):
        migration_manager.migrate_to(3)


def test_migrate_apply_sql(migration_manager, temp_db_engine):
    """Test applying SQL migration."""
    # Create test table first
    with temp_db_engine.connect() as conn:
        conn.execute(text("CREATE TABLE test_table (id INTEGER PRIMARY KEY)"))
        conn.commit()

    migration = Migration(
        version=1, description="Add column", up_sql="ALTER TABLE test_table ADD COLUMN name TEXT"
    )

    migration_manager.register_migration(migration)
    result = migration_manager.migrate_to(1)

    assert result is True

    # Verify column was added
    with temp_db_engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(test_table)"))
        columns = {row[1] for row in result.fetchall()}
        assert "name" in columns

        # Verify version recorded
        result = conn.execute(text("SELECT version, description FROM baselinr_schema_version"))
        row = result.fetchone()
        assert row[0] == 1
        assert row[1] == "Add column"


def test_migrate_apply_python(migration_manager, temp_db_engine):
    """Test applying Python migration."""
    # Create test table
    with temp_db_engine.connect() as conn:
        conn.execute(
            text(
                """
            CREATE TABLE test_data (
                id INTEGER PRIMARY KEY,
                value INTEGER
            )
        """
            )
        )
        conn.execute(text("INSERT INTO test_data (value) VALUES (10)"))
        conn.commit()

    def double_values(conn):
        conn.execute(text("UPDATE test_data SET value = value * 2"))

    migration = Migration(version=1, description="Double values", up_python=double_values)

    migration_manager.register_migration(migration)
    result = migration_manager.migrate_to(1)

    assert result is True

    # Verify data was modified
    with temp_db_engine.connect() as conn:
        result = conn.execute(text("SELECT value FROM test_data"))
        value = result.fetchone()[0]
        assert value == 20


def test_migrate_dry_run(migration_manager):
    """Test dry run mode."""
    migration = Migration(
        version=1, description="Test migration", up_sql="CREATE TABLE should_not_exist (id INTEGER)"
    )

    migration_manager.register_migration(migration)
    result = migration_manager.migrate_to(1, dry_run=True)

    assert result is True

    # Verify no changes were made
    version = migration_manager.get_current_version()
    assert version is None


def test_validate_schema_empty(migration_manager):
    """Test schema validation on empty database."""
    results = migration_manager.validate_schema()

    assert results["valid"] is False
    assert "version table missing or empty" in " ".join(results["errors"]).lower()


def test_validate_schema_version_mismatch(migration_manager, temp_db_engine):
    """Test schema validation with version mismatch."""
    # Set DB version behind code version
    with temp_db_engine.connect() as conn:
        conn.execute(
            text(
                """
            INSERT INTO baselinr_schema_version (version, description)
            VALUES (0, 'Old version')
        """
            )
        )
        conn.commit()

    results = migration_manager.validate_schema()

    assert len(results["warnings"]) > 0
    assert "behind" in " ".join(results["warnings"]).lower()


def test_validate_schema_missing_tables(migration_manager, temp_db_engine):
    """Test schema validation with missing tables."""
    # Set version but don't create tables
    with temp_db_engine.connect() as conn:
        conn.execute(
            text(
                """
            INSERT INTO baselinr_schema_version (version, description)
            VALUES (1, 'Current')
        """
            )
        )
        conn.commit()

    results = migration_manager.validate_schema()

    assert results["valid"] is False
    assert any("baselinr_runs" in err for err in results["errors"])


def test_validate_schema_valid(migration_manager, temp_db_engine):
    """Test schema validation on valid database."""
    # Create all required tables
    with temp_db_engine.connect() as conn:
        conn.execute(
            text(
                """
            INSERT INTO baselinr_schema_version (version, description)
            VALUES (:version, 'Current')
        """
            ),
            {"version": CURRENT_SCHEMA_VERSION},
        )

        conn.execute(
            text(
                """
            CREATE TABLE baselinr_runs (
                run_id VARCHAR(36) PRIMARY KEY,
                dataset_name VARCHAR(255)
            )
        """
            )
        )

        conn.execute(
            text(
                """
            CREATE TABLE baselinr_results (
                id INTEGER PRIMARY KEY
            )
        """
            )
        )

        conn.execute(
            text(
                """
            CREATE TABLE baselinr_events (
                event_id VARCHAR(36) PRIMARY KEY
            )
        """
            )
        )

        conn.execute(
            text(
                """
            CREATE TABLE baselinr_table_state (
                table_name VARCHAR(255) PRIMARY KEY
            )
        """
            )
        )

        conn.execute(
            text(
                """
            CREATE TABLE baselinr_schema_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name VARCHAR(255) NOT NULL,
                schema_name VARCHAR(255),
                column_name VARCHAR(255) NOT NULL,
                column_type VARCHAR(100) NOT NULL,
                column_hash VARCHAR(64) NOT NULL,
                nullable BOOLEAN DEFAULT TRUE,
                first_seen_at TIMESTAMP NOT NULL,
                last_seen_at TIMESTAMP NOT NULL,
                run_id VARCHAR(36) NOT NULL
            )
        """
            )
        )

        conn.commit()

    results = migration_manager.validate_schema()

    assert results["valid"] is True
    assert len(results["errors"]) == 0
    assert results["version"] == CURRENT_SCHEMA_VERSION


def test_multiple_migrations_sequence(migration_manager, temp_db_engine):
    """Test applying multiple migrations in sequence."""
    # Create base table
    with temp_db_engine.connect() as conn:
        conn.execute(
            text(
                """
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY
            )
        """
            )
        )
        conn.commit()

    # Register multiple migrations
    migration1 = Migration(
        version=1, description="Add column1", up_sql="ALTER TABLE test_table ADD COLUMN col1 TEXT"
    )

    migration2 = Migration(
        version=2, description="Add column2", up_sql="ALTER TABLE test_table ADD COLUMN col2 TEXT"
    )

    migration_manager.register_migration(migration1)
    migration_manager.register_migration(migration2)

    # Apply both migrations
    result = migration_manager.migrate_to(2)
    assert result is True

    # Verify both columns exist
    with temp_db_engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(test_table)"))
        columns = {row[1] for row in result.fetchall()}
        assert "col1" in columns
        assert "col2" in columns

        # Verify both versions recorded
        result = conn.execute(
            text(
                """
            SELECT COUNT(*) FROM baselinr_schema_version
        """
            )
        )
        count = result.fetchone()[0]
        assert count == 2


def test_migrate_v3_expectations_table(migration_manager, temp_db_engine):
    """Test v3 migration creates expectations table."""
    from baselinr.storage.migrations.versions import ALL_MIGRATIONS

    # Register all migrations
    for migration in ALL_MIGRATIONS:
        migration_manager.register_migration(migration)

    # Migrate to version 3
    result = migration_manager.migrate_to(3)
    assert result is True

    # Verify expectations table exists
    with temp_db_engine.connect() as conn:
        result = conn.execute(
            text(
                """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='baselinr_expectations'
        """
            )
        )
        table_exists = result.fetchone() is not None
        assert table_exists

        # Verify table structure
        result = conn.execute(text("PRAGMA table_info(baselinr_expectations)"))
        columns = {row[1] for row in result.fetchall()}

        # Check key columns exist
        assert "table_name" in columns
        assert "column_name" in columns
        assert "metric_name" in columns
        assert "expected_mean" in columns
        assert "expected_stddev" in columns
        assert "lower_control_limit" in columns
        assert "upper_control_limit" in columns
        assert "distribution_type" in columns
        assert "distribution_params" in columns
        assert "sample_size" in columns
        assert "expectation_version" in columns

        # Verify version recorded
        result = conn.execute(
            text(
                """
            SELECT version, description FROM baselinr_schema_version
            WHERE version = 3
        """
            )
        )
        row = result.fetchone()
        assert row is not None
        assert row[0] == 3
        assert "expectations" in row[1].lower()