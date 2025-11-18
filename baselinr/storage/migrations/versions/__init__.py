"""Migration versions."""

from .v1_initial import migration as v1_migration

# Register all migrations here
ALL_MIGRATIONS = [v1_migration]
