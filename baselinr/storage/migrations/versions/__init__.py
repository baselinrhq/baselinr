"""Migration versions."""

from .v1_initial import migration as v1_migration
from .v2_schema_registry import migration as v2_migration
from .v3_expectations import migration as v3_migration
from .v4_lineage import migration as v4_migration
from .v5_column_lineage import migration as v5_migration
from .v6_rca_tables import migration as v6_migration
from .v7_add_database_name_to_rca import migration as v7_migration
from .v8_validation import migration as v8_migration
from .v9_quality_scores import migration as v9_migration
from .v10_column_quality_scores import migration as v10_migration

# Register all migrations here
ALL_MIGRATIONS = [
    v1_migration,
    v2_migration,
    v3_migration,
    v4_migration,
    v5_migration,
    v6_migration,
    v7_migration,
    v8_migration,
    v9_migration,
    v10_migration,
]
