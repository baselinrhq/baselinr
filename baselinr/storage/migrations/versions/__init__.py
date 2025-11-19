"""Migration versions."""

from .v1_initial import migration as v1_migration
from .v2_schema_registry import migration as v2_migration

# Register all migrations here
ALL_MIGRATIONS = [v1_migration, v2_migration]
