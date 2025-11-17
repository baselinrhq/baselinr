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
        SELECT 1
    """,
    down_sql=None,  # Cannot downgrade from baseline
)
