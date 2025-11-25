"""
Configuration resolution utility for Baselinr.

Resolves and merges configurations from database, schema, table, and column levels
following the precedence: Database → Schema → Table → Column.
"""

import logging
from typing import List, Optional, Union

from ..config.schema import DatabaseConfig, ProfilingConfig, SchemaConfig, TablePattern

logger = logging.getLogger(__name__)


class ConfigResolver:
    """Resolves and merges configurations from database, schema, table, and column levels."""

    def __init__(
        self,
        schema_configs: Optional[List[SchemaConfig]] = None,
        database_configs: Optional[List[DatabaseConfig]] = None,
        profiling_config: Optional[ProfilingConfig] = None,
    ):
        """
        Initialize config resolver.

        Args:
            schema_configs: List of schema-level configurations
            database_configs: List of database-level configurations
            profiling_config: Optional profiling config for context
        """
        self.schema_configs = schema_configs or []
        self.database_configs = database_configs or []
        self.profiling_config = profiling_config

    def find_database_config(self, database_name: Optional[str]) -> Optional[DatabaseConfig]:
        """
        Find matching database configuration.

        Args:
            database_name: Database name to match

        Returns:
            Matching DatabaseConfig, or None if no match found
        """
        if database_name is None:
            return None

        for db_config in self.database_configs:
            if db_config.database == database_name:
                return db_config
        return None

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
        Resolve and merge database + schema + table configs into final TablePattern.

        Args:
            table_pattern: Table pattern from configuration
            schema_name: Schema name (defaults to table_pattern.schema_)
            database_name: Database name (defaults to table_pattern.database)

        Returns:
            Merged TablePattern with database, schema, and table configs applied
        """
        # Use provided schema/database or fall back to pattern values
        resolved_schema = schema_name or table_pattern.schema_
        resolved_database = database_name or table_pattern.database

        # Find matching database and schema configs
        database_config = self.find_database_config(resolved_database)
        schema_config = self.find_schema_config(resolved_schema, resolved_database)

        # Merge database → schema → table (in that order)
        # Start with table pattern and build up: database → schema → table
        merged = table_pattern.model_copy(deep=True)

        # Store original table columns to rebuild in correct order
        table_columns = list(table_pattern.columns) if table_pattern.columns else []
        database_columns = []
        schema_columns = []

        # Store original table partition and sampling to check if schema should override database
        table_has_partition = table_pattern.partition is not None
        table_has_sampling = table_pattern.sampling is not None

        # Apply database config first (lowest priority)
        if database_config:
            merged = self._merge_config_into_pattern(
                database_config,
                merged,
                is_database=True,
                table_has_partition=table_has_partition,
                table_has_sampling=table_has_sampling,
            )
            if database_config.columns:
                database_columns = list(database_config.columns)

        # Apply schema config second (medium priority, overrides database)
        if schema_config:
            merged = self._merge_config_into_pattern(
                schema_config,
                merged,
                is_schema=True,
                table_has_partition=table_has_partition,
                table_has_sampling=table_has_sampling,
            )
            if schema_config.columns:
                schema_columns = list(schema_config.columns)

        # Rebuild column list in correct order: table → schema → database
        # ColumnMatcher checks in order, so higher priority must come first
        if table_columns or schema_columns or database_columns:
            merged.columns = table_columns + schema_columns + database_columns

        # Table config is already in merged (highest priority)
        return merged

    def _merge_config_into_pattern(
        self,
        config: Union[DatabaseConfig, SchemaConfig],
        table_pattern: TablePattern,
        is_database: bool = False,
        is_schema: bool = False,
        table_has_partition: bool = False,
        table_has_sampling: bool = False,
    ) -> TablePattern:
        """
        Merge database or schema config into table pattern.

        Table-level values override config-level values. For nested objects
        (partition, sampling), merge recursively. For lists (columns, filters),
        combine both with table taking precedence for duplicates.

        Args:
            config: Database-level or schema-level configuration
            table_pattern: Table-level configuration

        Returns:
            Merged TablePattern
        """
        # Deep copy table pattern to avoid modifying original
        merged = table_pattern.model_copy(deep=True)

        # Merge partition config
        # Precedence: table → schema → database
        # When merging database into table: table wins (database only fills if table is None)
        # When merging schema into (table+database): schema overrides database, but table still wins
        if config.partition and not table_has_partition:
            # Table doesn't have partition, so we can merge config-level partition
            if is_schema:
                # Schema merge: schema should override database (even if database already set it)
                # Always override when schema is merging (schema overrides database)
                merged.partition = config.partition.model_copy(deep=True)
            elif merged.partition is None:
                # Database merge or first merge: fill if empty
                merged.partition = config.partition.model_copy(deep=True)

        # Merge sampling config
        # Precedence: table → schema → database
        # Schema should override database, but table still wins
        if config.sampling and not table_has_sampling:
            # Table doesn't have sampling, so we can merge config-level sampling
            if is_schema:
                # Schema merge: schema should override database (even if database already set it)
                # Always override when schema is merging (schema overrides database)
                merged.sampling = config.sampling.model_copy(deep=True)
            elif merged.sampling is None:
                # Database merge or first merge: fill if empty
                merged.sampling = config.sampling.model_copy(deep=True)

        # Column configs are handled in resolve_table_config to ensure correct order.
        # Don't modify columns here - they'll be rebuilt in resolve_table_config.

        # Merge filter fields: combine both (both apply)
        # For lists, extend if not None
        if config.table_types:
            if merged.table_types is None:
                merged.table_types = config.table_types.copy()
            else:
                # Combine both lists
                combined = list(set(config.table_types + merged.table_types))
                merged.table_types = combined

        if config.min_rows is not None and merged.min_rows is None:
            merged.min_rows = config.min_rows
        # If both set, table overrides (no merge needed - already set)

        if config.max_rows is not None and merged.max_rows is None:
            merged.max_rows = config.max_rows
        # If both set, table overrides (no merge needed - already set)

        if config.required_columns:
            if merged.required_columns is None:
                merged.required_columns = config.required_columns.copy()
            else:
                # Combine both lists (both required)
                combined = list(set(config.required_columns + merged.required_columns))
                merged.required_columns = combined

        if config.modified_since_days is not None and merged.modified_since_days is None:
            merged.modified_since_days = config.modified_since_days
        # If both set, table overrides (no merge needed - already set)

        if config.exclude_patterns:
            if merged.exclude_patterns is None:
                merged.exclude_patterns = config.exclude_patterns.copy()
            else:
                # Combine both lists (exclude if in either)
                combined = list(set(config.exclude_patterns + merged.exclude_patterns))
                merged.exclude_patterns = combined

        return merged

    def merge_table_patterns(
        self, schema_config: SchemaConfig, table_pattern: TablePattern
    ) -> TablePattern:
        """
        Merge schema config into table pattern.

        This method is kept for backward compatibility. It now delegates to
        _merge_config_into_pattern.

        Args:
            schema_config: Schema-level configuration
            table_pattern: Table-level configuration

        Returns:
            Merged TablePattern
        """
        # For backward compatibility, check original table pattern state
        table_has_partition = table_pattern.partition is not None
        table_has_sampling = table_pattern.sampling is not None
        return self._merge_config_into_pattern(
            schema_config,
            table_pattern,
            is_schema=True,
            table_has_partition=table_has_partition,
            table_has_sampling=table_has_sampling,
        )
