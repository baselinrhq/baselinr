"""
Configuration resolution utility for Baselinr.

Resolves and merges configurations from schema, table, and column levels
following the precedence: Schema → Table → Column.
"""

import logging
from typing import List, Optional

from ..config.schema import ProfilingConfig, SchemaConfig, TablePattern

logger = logging.getLogger(__name__)


class ConfigResolver:
    """Resolves and merges configurations from schema, table, and column levels."""

    def __init__(
        self,
        schema_configs: Optional[List[SchemaConfig]] = None,
        profiling_config: Optional[ProfilingConfig] = None,
    ):
        """
        Initialize config resolver.

        Args:
            schema_configs: List of schema-level configurations
            profiling_config: Optional profiling config for context
        """
        self.schema_configs = schema_configs or []
        self.profiling_config = profiling_config

    def find_schema_config(
        self, schema_name: Optional[str], database_name: Optional[str] = None
    ) -> Optional[SchemaConfig]:
        """
        Find matching schema configuration.

        Args:
            schema_name: Schema name to match
            database_name: Optional database name for matching

        Returns:
            Matching SchemaConfig, or None if no match found
        """
        if schema_name is None:
            return None

        # Find exact matches first (schema + database)
        exact_matches = []
        schema_only_matches = []

        for schema_config in self.schema_configs:
            if schema_config.schema_ == schema_name:
                if schema_config.database == database_name:
                    exact_matches.append(schema_config)
                elif schema_config.database is None:
                    # Schema config without database specified (matches any database)
                    schema_only_matches.append(schema_config)

        # Prefer exact database match
        if exact_matches:
            # If multiple exact matches, return first (could be enhanced with priority)
            return exact_matches[0]

        # Fall back to schema-only match
        if schema_only_matches:
            return schema_only_matches[0]

        return None

    def resolve_table_config(
        self,
        table_pattern: TablePattern,
        schema_name: Optional[str] = None,
        database_name: Optional[str] = None,
    ) -> TablePattern:
        """
        Resolve and merge schema + table configs into final TablePattern.

        Args:
            table_pattern: Table pattern from configuration
            schema_name: Schema name (defaults to table_pattern.schema_)
            database_name: Database name (defaults to table_pattern.database)

        Returns:
            Merged TablePattern with schema configs applied
        """
        # Use provided schema/database or fall back to pattern values
        resolved_schema = schema_name or table_pattern.schema_
        resolved_database = database_name or table_pattern.database

        # Find matching schema config
        schema_config = self.find_schema_config(resolved_schema, resolved_database)

        if schema_config is None:
            # No schema config found, return table pattern as-is
            return table_pattern

        # Merge schema config into table pattern
        return self.merge_table_patterns(schema_config, table_pattern)

    def merge_table_patterns(
        self, schema_config: SchemaConfig, table_pattern: TablePattern
    ) -> TablePattern:
        """
        Merge schema config into table pattern.

        Table-level values override schema-level values. For nested objects
        (partition, sampling), merge recursively. For lists (columns, filters),
        combine both with table taking precedence for duplicates.

        Args:
            schema_config: Schema-level configuration
            table_pattern: Table-level configuration

        Returns:
            Merged TablePattern
        """
        # Deep copy table pattern to avoid modifying original
        merged = table_pattern.model_copy(deep=True)

        # Merge partition config
        if schema_config.partition and merged.partition is None:
            merged.partition = schema_config.partition.model_copy(deep=True)
        elif schema_config.partition and merged.partition:
            # Merge partition configs: table overrides schema
            schema_partition_dict = schema_config.partition.model_dump()
            table_partition_dict = merged.partition.model_dump()
            # Table values override schema values
            merged_partition_dict = {**schema_partition_dict, **table_partition_dict}
            merged.partition = type(schema_config.partition)(**merged_partition_dict)

        # Merge sampling config
        if schema_config.sampling and merged.sampling is None:
            merged.sampling = schema_config.sampling.model_copy(deep=True)
        elif schema_config.sampling and merged.sampling:
            # Merge sampling configs: table overrides schema
            schema_sampling_dict = schema_config.sampling.model_dump()
            table_sampling_dict = merged.sampling.model_dump()
            merged_sampling_dict = {**schema_sampling_dict, **table_sampling_dict}
            merged.sampling = type(schema_config.sampling)(**merged_sampling_dict)

        # Merge column configs: table columns first (higher priority), then schema columns
        # ColumnMatcher.find_matching_config returns first match, so table configs must come first
        merged_columns = []

        # Add table column configs first (higher priority, checked first by ColumnMatcher)
        if merged.columns:
            merged_columns.extend(merged.columns)

        # Add schema column configs second (lower priority, checked after table configs)
        if schema_config.columns:
            merged_columns.extend(schema_config.columns)

        if merged_columns:
            merged.columns = merged_columns

        # Merge filter fields: combine both (both apply)
        # For lists, extend if not None
        if schema_config.table_types:
            if merged.table_types is None:
                merged.table_types = schema_config.table_types.copy()
            else:
                # Combine both lists
                combined = list(set(schema_config.table_types + merged.table_types))
                merged.table_types = combined

        if schema_config.min_rows is not None and merged.min_rows is None:
            merged.min_rows = schema_config.min_rows
        # If both set, table overrides (no merge needed - already set)

        if schema_config.max_rows is not None and merged.max_rows is None:
            merged.max_rows = schema_config.max_rows
        # If both set, table overrides (no merge needed - already set)

        if schema_config.required_columns:
            if merged.required_columns is None:
                merged.required_columns = schema_config.required_columns.copy()
            else:
                # Combine both lists (both required)
                combined = list(set(schema_config.required_columns + merged.required_columns))
                merged.required_columns = combined

        if schema_config.modified_since_days is not None and merged.modified_since_days is None:
            merged.modified_since_days = schema_config.modified_since_days
        # If both set, table overrides (no merge needed - already set)

        if schema_config.exclude_patterns:
            if merged.exclude_patterns is None:
                merged.exclude_patterns = schema_config.exclude_patterns.copy()
            else:
                # Combine both lists (exclude if in either)
                combined = list(set(schema_config.exclude_patterns + merged.exclude_patterns))
                merged.exclude_patterns = combined

        return merged
