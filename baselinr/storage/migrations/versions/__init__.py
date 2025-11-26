"""Migration versions."""

from .v1_initial import migration as v1_migration
from .v2_schema_registry import migration as v2_migration
from .v3_expectations import migration as v3_migration
from .v4_lineage import migration as v4_migration

# Register all migrations here
ALL_MIGRATIONS = [v1_migration, v2_migration, v3_migration, v4_migration]
