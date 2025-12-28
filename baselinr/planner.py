"""
Profiling plan builder for Baselinr.

Analyzes configuration and builds an execution plan showing what will be profiled
without actually running the profiling logic.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .config.schema import BaselinrConfig, TablePattern
from .connectors.factory import create_connector
from .incremental import IncrementalPlan, IncrementalPlanner, TableRunDecision
from .profiling.table_matcher import TableMatcher
from .profiling.tag_metadata import TagResolver

# Optional dbt integration
try:
    from .integrations.dbt import DBTManifestParser, DBTSelectorResolver

    DBT_AVAILABLE = True
except ImportError:
    DBT_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class TablePlan:
    """Plan for profiling a single table."""

    name: str
    schema: Optional[str] = None
    status: str = "ready"
    partition_config: Optional[Dict[str, Any]] = None
    sampling_config: Optional[Dict[str, Any]] = None
    metrics: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        """Get fully qualified table name."""
        if self.schema:
            return f"{self.schema}.{self.name}"
        return self.name


@dataclass
class ProfilingPlan:
    """Complete profiling execution plan."""

    run_id: str
    timestamp: datetime
    environment: str
    tables: List[TablePlan] = field(default_factory=list)
    source_type: str = "postgres"
    source_database: str = ""
    drift_strategy: str = "absolute_threshold"
    total_tables: int = 0
    estimated_metrics: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary."""
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat(),
            "environment": self.environment,
            "source": {"type": self.source_type, "database": self.source_database},
            "drift_detection": {"strategy": self.drift_strategy},
            "tables": [
                {
                    "name": table.full_name,
                    "schema": table.schema,
                    "table": table.name,
                    "status": table.status,
                    "partition": table.partition_config,
                    "sampling": table.sampling_config,
                    "metrics": table.metrics,
                    "metadata": table.metadata,
                }
                for table in self.tables
            ],
            "summary": {
                "total_tables": self.total_tables,
                "estimated_metrics": self.estimated_metrics,
            },
        }


class PlanBuilder:
    """Builds profiling execution plans from configuration."""

    def __init__(self, config: BaselinrConfig, config_file_path: Optional[str] = None):
        """
        Initialize plan builder.

        Args:
            config: Baselinr configuration
            config_file_path: Optional path to the config file (for resolving relative paths)
        """
        self.config = config
        self.config_file_path = config_file_path
        self._incremental_planner: Optional[IncrementalPlanner] = None
        self._table_matcher: Optional[TableMatcher] = None
        self._connector: Optional[Any] = None
        self._connector_cache: Dict[Optional[str], Any] = {}  # database -> connector
        self._tag_provider: Optional[Any] = None
        self._discovery_cache: Dict[str, Tuple[List[str], float]] = (
            {}
        )  # schema -> (tables, timestamp)

    def expand_table_patterns(
        self, patterns: Optional[List[TablePattern]] = None
    ) -> List[TablePattern]:
        """
        Expand all patterns (wildcard, regex, schema, database-level)
        into concrete TablePattern objects.

        This is a public method that can be used by CLI commands and SDK
        to get expanded table patterns before building the plan.

        Args:
            patterns: Optional list of TablePattern objects to expand.
                     If None, uses config.profiling.tables.
                     If profiling.tables is empty, extracts patterns from ODCS contracts.

        Returns:
            List of expanded TablePattern objects with concrete table names
        """
        if patterns is None:
            patterns = self.config.profiling.tables

        # If no table patterns specified, try to extract from ODCS contracts
        if not patterns:
            if self.config.contracts:

                from pathlib import Path

                from .contracts import ContractLoader

                # Load contracts - resolve path relative to config file if available,
                # otherwise relative to current working directory
                contracts_dir = Path(self.config.contracts.directory)
                if not contracts_dir.is_absolute():
                    if self.config_file_path:
                        # Resolve relative to config file location (same as config loader)
                        config_path = Path(self.config_file_path)
                        contracts_dir = config_path.parent / contracts_dir
                    else:
                        # Fallback to current working directory
                        contracts_dir = Path.cwd() / contracts_dir

                loader = ContractLoader(
                    validate_on_load=self.config.contracts.validate_on_load,
                    file_patterns=self.config.contracts.file_patterns,
                )
                try:
                    contracts = loader.load_from_directory(
                        str(contracts_dir),
                        recursive=self.config.contracts.recursive,
                        exclude_patterns=self.config.contracts.exclude_patterns,
                    )

                    # Extract table patterns from contracts
                    patterns = []
                    for contract in contracts:
                        if contract.dataset:
                            for ds in contract.dataset:
                                if ds.name or ds.physicalName:
                                    # Parse physical name if available
                                    table_name = ds.name or ""
                                    schema = None
                                    database = None

                                    if ds.physicalName:
                                        parts = ds.physicalName.split(".")
                                        if len(parts) == 3:
                                            database = parts[0]
                                            schema = parts[1]
                                            table_name = parts[2]
                                        elif len(parts) == 2:
                                            schema = parts[0]
                                            table_name = parts[1]
                                        else:
                                            table_name = ds.physicalName

                                    # Don't extract database from server config - use source
                                    # database from main config. Server config in contracts is
                                    # for documentation, not connection. Only use schema from
                                    # server config if not already set
                                    if contract.servers and not schema:
                                        env = (
                                            contract.servers.development
                                            or contract.servers.production
                                        )
                                        if env and env.schema_:
                                            schema = env.schema_

                                    if table_name:
                                        pattern = TablePattern(
                                            table=table_name,
                                            schema=schema,
                                            database=database,
                                        )  # type: ignore[call-arg]
                                        patterns.append(pattern)
                                        logger.debug(
                                            f"Extracted table pattern from contract: {table_name} "
                                            f"(schema: {schema}, database: {database})"
                                        )
                except Exception as e:
                    logger.warning(f"Failed to load contracts for table extraction: {e}")

        if not patterns:
            return []

        logger.info("Expanding table patterns...")

        # Validate regex patterns if enabled
        if self.config.profiling.discovery_options.validate_regex:
            self._validate_regex_patterns(patterns)

        # Expand patterns
        expanded_patterns = []
        for pattern in patterns:
            expanded = self._expand_pattern(pattern)
            expanded_patterns.extend(expanded)

        # Filter out any patterns without table names (should not happen, but be safe)
        # This ensures only valid expanded patterns proceed to precedence resolution
        valid_patterns = []
        for pattern in expanded_patterns:
            if pattern.table is not None:
                valid_patterns.append(pattern)
            else:
                logger.warning(
                    f"Skipping pattern without table name after expansion: {pattern}. "
                    "This should not happen - please report this issue."
                )

        # Resolve precedence and deduplicate
        resolved_patterns = self._resolve_precedence(valid_patterns)

        # Validate that all resolved patterns have table names set
        for pattern in resolved_patterns:
            if pattern.table is None:
                logger.error(
                    f"Resolved pattern missing table name: {pattern}. "
                    "This should not happen after expansion. "
                    "Pattern will be skipped."
                )

        # Filter out any patterns without table names (should not happen, but be safe)
        resolved_patterns = [p for p in resolved_patterns if p.table is not None]

        logger.info(f"Expanded {len(patterns)} pattern(s) into {len(resolved_patterns)} table(s)")

        return resolved_patterns

    def build_plan(self) -> ProfilingPlan:
        """
        Build profiling execution plan from configuration.

        Returns:
            ProfilingPlan with all tables to be profiled

        Raises:
            ValueError: If configuration is invalid or empty
        """
        logger.info("Building profiling execution plan...")

        # Get table patterns from config
        # Tables can come from:
        # 1. profiling.tables (table selection patterns)
        # 2. ODCS contracts (extract table patterns from contracts)
        table_patterns = self.config.profiling.tables

        # If no table patterns specified, try to extract from ODCS contracts
        if not table_patterns:
            if self.config.contracts:
                try:
                    from ..contracts import ContractLoader
                    from ..contracts.adapter import ODCSAdapter

                    # Load contracts
                    loader = ContractLoader(
                        validate_on_load=self.config.contracts.validate_on_load,
                        file_patterns=self.config.contracts.file_patterns,
                    )
                    contracts = loader.load_from_directory(
                        self.config.contracts.directory,
                        recursive=self.config.contracts.recursive,
                        exclude_patterns=self.config.contracts.exclude_patterns,
                    )

                    # Extract table patterns from contracts
                    adapter = ODCSAdapter()
                    table_patterns = []
                    for contract in contracts:
                        targets = adapter.to_profiling_targets(contract)
                        for target in targets:
                            if target.table:
                                pattern = TablePattern(
                                    table=target.table,
                                    schema=target.schema,
                                    database=target.database,
                                )  # type: ignore[call-arg]
                                table_patterns.append(pattern)
                                logger.debug(
                                    f"Extracted table pattern from contract: {target.table} "
                                    f"(schema: {target.schema}, database: {target.database})"
                                )
                except Exception as e:
                    logger.warning(f"Failed to extract table patterns from contracts: {e}")

        # Expand patterns into concrete tables
        # Use extracted patterns if we got them from contracts, otherwise use config patterns
        expanded_patterns = self.expand_table_patterns(
            patterns=table_patterns if table_patterns else None
        )

        # Validate that we have some way to determine tables
        # If no expanded patterns and table discovery is enabled, that's ok
        # Discovery will happen later. But if we have no patterns and no discovery, we can't proceed
        if not expanded_patterns and not self.config.profiling.table_discovery:
            raise ValueError(
                "No tables configured for profiling. "
                "Add tables to the 'profiling.tables' section, enable 'profiling.table_discovery', "
                "or configure ODCS contracts in the 'contracts' section in your config."
            )

        # Create plan
        plan = ProfilingPlan(
            run_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            environment=self.config.environment,
            source_type=self.config.source.type,
            source_database=self.config.source.database,
            drift_strategy=self.config.drift_detection.strategy,
        )

        incremental_plan: Optional[IncrementalPlan] = None
        decision_map: Dict[str, TableRunDecision] = {}
        if self.config.incremental.enabled:
            # Pass expanded patterns to incremental planner
            incremental_plan = self.get_tables_to_run(plan.timestamp, expanded_patterns)
            decision_map = {
                self._table_key(decision.table): decision for decision in incremental_plan.decisions
            }

        # Build table plans from expanded patterns
        for table_pattern in expanded_patterns:
            table_plan = self._build_table_plan(
                table_pattern, decision_map.get(self._table_key(table_pattern))
            )
            plan.tables.append(table_plan)

        # Calculate summary statistics
        plan.total_tables = len(plan.tables)
        plan.estimated_metrics = self._estimate_total_metrics(plan.tables)

        logger.info(
            f"Plan built: {plan.total_tables} tables, " f"~{plan.estimated_metrics} metrics"
        )

        return plan

    def _get_connector(self, database: Optional[str] = None):
        """
        Get or create database connector.

        Args:
            database: Optional database name. If None, uses config.source.database.
                     If specified, creates a connector for that database.

        Returns:
            BaseConnector instance for the specified database
        """
        # Use None as cache key for source database to distinguish from explicit databases
        cache_key = None if database is None else database

        # Return cached connector if available
        if cache_key in self._connector_cache:
            return self._connector_cache[cache_key]

        # Create connector
        if database is None:
            # Use source connector (backward compatible)
            connector = create_connector(self.config.source, self.config.retry)
        else:
            # Create connector with database override
            from copy import deepcopy

            db_config = deepcopy(self.config.source)
            db_config.database = database
            connector = create_connector(db_config, self.config.retry)

        # Cache connector
        self._connector_cache[cache_key] = connector

        # Also cache as _connector for backward compatibility
        if self._connector is None:
            self._connector = connector

        return connector

    def _get_table_matcher(self) -> TableMatcher:
        """Get or create table matcher."""
        if self._table_matcher is None:
            self._table_matcher = TableMatcher(
                validate_regex=self.config.profiling.discovery_options.validate_regex
            )
        return self._table_matcher

    def _get_tag_provider(self):
        """Get or create tag provider."""
        if self._tag_provider is None:
            connector = self._get_connector()
            tag_provider_name = self.config.profiling.discovery_options.tag_provider
            dbt_manifest_path = self.config.profiling.discovery_options.dbt_manifest_path

            self._tag_provider = TagResolver.create_provider(
                connector,
                self.config.source,
                tag_provider=tag_provider_name,
                dbt_manifest_path=dbt_manifest_path,
            )
        return self._tag_provider

    def _validate_regex_patterns(self, patterns: List[TablePattern]) -> None:
        """Validate all regex patterns at config load time."""
        from .profiling.table_matcher import RegexValidator

        for pattern in patterns:
            if pattern.pattern and pattern.pattern_type == "regex":
                if not RegexValidator.validate_pattern(pattern.pattern):
                    raise ValueError(
                        f"Invalid regex pattern in table pattern: '{pattern.pattern}'. "
                        "Please check your regex syntax."
                    )
            if pattern.schema_pattern and pattern.pattern_type == "regex":
                if not RegexValidator.validate_pattern(pattern.schema_pattern):
                    raise ValueError(
                        f"Invalid regex schema pattern in table pattern: "
                        f"'{pattern.schema_pattern}'. Please check your regex syntax."
                    )

    def _expand_pattern(self, pattern: TablePattern) -> List[TablePattern]:
        """
        Expand a single pattern into concrete TablePattern objects.

        Args:
            pattern: TablePattern to expand

        Returns:
            List of expanded TablePattern objects
        """
        expanded = []

        # Explicit table - no expansion needed
        if pattern.table and not pattern.pattern:
            expanded.append(pattern)
            return expanded

        # Get database-specific connector and matcher
        database = pattern.database
        connector = self._get_connector(database)
        matcher = self._get_table_matcher()

        # Determine schemas to search
        schemas_to_search: List[Optional[str]] = self._get_schemas_to_search(pattern, database)

        # Expand based on pattern type
        if pattern.dbt_ref or pattern.dbt_selector:
            # dbt-based: resolve dbt refs/selectors
            expanded.extend(self._expand_dbt_pattern(pattern, database))
        elif pattern.select_all_schemas:
            # Database-level: all schemas
            expanded.extend(self._expand_database_level(pattern, connector, matcher, database))
        elif pattern.select_schema:
            # Schema-level: all tables in specified schema(s)
            expanded.extend(
                self._expand_schema_level(pattern, connector, matcher, schemas_to_search, database)
            )
        elif pattern.pattern:
            # Pattern-based: match tables against pattern
            expanded.extend(
                self._expand_pattern_based(pattern, connector, matcher, schemas_to_search, database)
            )
        else:
            # Should not reach here due to validation, but handle gracefully
            logger.warning(
                f"Pattern has no expansion method: {pattern}. "
                "Pattern should have 'table', 'pattern', 'select_schema', "
                "'select_all_schemas', 'dbt_ref', or 'dbt_selector' set."
            )
            # Don't add pattern without table name - it will fail validation later
            # This ensures we don't pass invalid patterns to the profiling engine

        # Final safety check: ensure all returned patterns have table names set
        valid_expanded = []
        for p in expanded:
            if p.table is not None:
                valid_expanded.append(p)
            else:
                logger.warning(
                    f"Pattern expanded without table name: {p}. "
                    "This should not happen. Skipping this pattern."
                )
        return valid_expanded

    def _get_schemas_to_search(
        self, pattern: TablePattern, database: Optional[str] = None
    ) -> List[Optional[str]]:
        """Get list of schemas to search based on pattern and discovery options."""
        discovery_opts = self.config.profiling.discovery_options

        # Start with pattern schema
        base_schemas: List[Optional[str]] = []
        if pattern.schema_:
            base_schemas.append(pattern.schema_)
        elif pattern.schema_pattern:
            # Expand schema pattern using database-specific connector
            connector = self._get_connector(database)
            all_schemas = connector.list_schemas()
            matcher = self._get_table_matcher()
            pattern_type = pattern.pattern_type or "wildcard"

            for schema in all_schemas:
                if matcher.match_schema(schema, pattern.schema_pattern, pattern_type):
                    base_schemas.append(schema)
        else:
            base_schemas.append(None)  # Default schema

        # Apply discovery filters
        if discovery_opts.include_schemas:
            base_schemas = [s for s in base_schemas if s in discovery_opts.include_schemas]

        if discovery_opts.exclude_schemas:
            base_schemas = [s for s in base_schemas if s not in discovery_opts.exclude_schemas]

        return base_schemas

    def _expand_database_level(
        self,
        pattern: TablePattern,
        connector: Any,
        matcher: TableMatcher,
        database: Optional[str] = None,
    ) -> List[TablePattern]:
        """Expand database-level pattern (all schemas)."""
        discovery_opts = self.config.profiling.discovery_options

        # Get all schemas
        all_schemas = connector.list_schemas()

        # Apply discovery limits
        max_schemas = discovery_opts.max_schemas_per_database
        if len(all_schemas) > max_schemas:
            self._handle_discovery_limit(
                f"Database has {len(all_schemas)} schemas, limiting to {max_schemas}",
                "schemas",
                len(all_schemas),
                max_schemas,
            )
            all_schemas = all_schemas[:max_schemas]

        # Filter schemas
        if discovery_opts.include_schemas:
            all_schemas = [s for s in all_schemas if s in discovery_opts.include_schemas]

        if discovery_opts.exclude_schemas:
            all_schemas = [s for s in all_schemas if s not in discovery_opts.exclude_schemas]

        # Expand each schema
        expanded = []
        for schema in all_schemas:
            schema_pattern = pattern.model_copy(deep=True)
            schema_pattern.select_schema = True
            schema_pattern.select_all_schemas = None
            schema_pattern.schema_ = schema
            # Preserve database field
            if database is not None:
                schema_pattern.database = database
            expanded.extend(
                self._expand_schema_level(schema_pattern, connector, matcher, [schema], database)
            )

        return expanded

    def _expand_schema_level(
        self,
        pattern: TablePattern,
        connector: Any,
        matcher: TableMatcher,
        schemas: List[Optional[str]],
        database: Optional[str] = None,
    ) -> List[TablePattern]:
        """Expand schema-level pattern (all tables in schema)."""
        expanded = []

        for schema in schemas:
            # Get all tables in schema using database-specific connector
            tables = self._get_tables_in_schema(schema, database)

            # Apply exclude patterns
            if pattern.exclude_patterns:
                exclude_type = pattern.pattern_type or "wildcard"
                tables = [
                    t
                    for t in tables
                    if not matcher.matches_exclude_patterns(
                        t, pattern.exclude_patterns, exclude_type
                    )
                ]

            # Filter by tag if tag provider available
            if pattern.tags or pattern.tags_any:
                tag_provider = self._get_tag_provider()
                if tag_provider:
                    table_tuples = [(t, schema) for t in tables]
                    filtered = tag_provider.filter_tables_by_tags(
                        table_tuples,
                        required_tags=pattern.tags,
                        any_tags=pattern.tags_any,
                    )
                    tables = [t for t, _ in filtered]
                else:
                    logger.warning(
                        f"Tag filtering requested but no tag provider available. "
                        f"Tags: {pattern.tags or pattern.tags_any}"
                    )

            # Create TablePattern for each table
            for table in tables:
                if not table:  # Skip empty or None table names
                    logger.warning(f"Skipping empty table name in schema {schema}")
                    continue
                table_pattern = pattern.model_copy(deep=True)
                table_pattern.table = table
                table_pattern.schema_ = schema
                table_pattern.pattern = None  # Clear pattern, now it's explicit
                table_pattern.select_schema = None
                table_pattern.select_all_schemas = None
                # Preserve database field
                if database is not None:
                    table_pattern.database = database
                # Validate table name was set
                assert (
                    table_pattern.table is not None
                ), f"Table name not set after expansion for table: {table}"
                expanded.append(table_pattern)

        return expanded

    def _expand_pattern_based(
        self,
        pattern: TablePattern,
        connector: Any,
        matcher: TableMatcher,
        schemas: List[Optional[str]],
        database: Optional[str] = None,
    ) -> List[TablePattern]:
        """Expand pattern-based selection (wildcard/regex)."""
        expanded = []
        pattern_type = pattern.pattern_type or "wildcard"

        for schema in schemas:
            # Get all tables in schema using database-specific connector
            tables = self._get_tables_in_schema(schema, database)

            # Match against pattern
            if pattern.pattern:
                matched_tables = matcher.filter_tables(
                    tables,
                    pattern=pattern.pattern,
                    pattern_type=pattern_type,
                    exclude_patterns=pattern.exclude_patterns,
                )
            else:
                matched_tables = tables

            # Apply discovery limits
            discovery_opts = self.config.profiling.discovery_options
            max_tables = discovery_opts.max_tables_per_pattern
            if len(matched_tables) > max_tables:
                self._handle_discovery_limit(
                    f"Pattern '{pattern.pattern}' matched {len(matched_tables)} "
                    f"tables, limiting to {max_tables}",
                    "tables",
                    len(matched_tables),
                    max_tables,
                )
                matched_tables = matched_tables[:max_tables]

            # Filter by tag if tag provider available
            if pattern.tags or pattern.tags_any:
                tag_provider = self._get_tag_provider()
                if tag_provider:
                    table_tuples = [(t, schema) for t in matched_tables]
                    filtered = tag_provider.filter_tables_by_tags(
                        table_tuples,
                        required_tags=pattern.tags,
                        any_tags=pattern.tags_any,
                    )
                    matched_tables = [t for t, _ in filtered]
                else:
                    logger.warning(
                        f"Tag filtering requested but no tag provider available. "
                        f"Tags: {pattern.tags or pattern.tags_any}"
                    )

            # Create TablePattern for each matched table
            for table in matched_tables:
                if not table:  # Skip empty or None table names
                    logger.warning(f"Skipping empty table name in schema {schema}")
                    continue
                table_pattern = pattern.model_copy(deep=True)
                table_pattern.table = table
                table_pattern.schema_ = schema
                table_pattern.pattern = None  # Clear pattern, now it's explicit
                table_pattern.select_schema = None
                table_pattern.select_all_schemas = None
                # Preserve database field
                if database is not None:
                    table_pattern.database = database
                # Validate table name was set
                assert (
                    table_pattern.table is not None
                ), f"Table name not set after expansion for table: {table}"
                expanded.append(table_pattern)

        return expanded

    def _get_tables_in_schema(
        self, schema: Optional[str], database: Optional[str] = None
    ) -> List[str]:
        """Get all tables in a schema, using cache if enabled."""
        discovery_opts = self.config.profiling.discovery_options
        # Include database in cache key to avoid cross-database cache collisions
        db_key = database or self.config.source.database
        cache_key = f"{db_key}:{schema or '__default__'}"

        # Check cache
        if discovery_opts.cache_discovery and cache_key in self._discovery_cache:
            cached_tables, cache_time = self._discovery_cache[cache_key]
            cache_age = time.time() - cache_time

            if cache_age < discovery_opts.cache_ttl_seconds:
                logger.debug(f"Using cached table list for schema {schema} in database {db_key}")
                return cached_tables

        # Fetch from database using database-specific connector
        connector = self._get_connector(database)
        tables: List[str] = connector.list_tables(schema=schema)

        # Store in cache
        if discovery_opts.cache_discovery:
            self._discovery_cache[cache_key] = (tables, time.time())

        return tables

    def _handle_discovery_limit(
        self, message: str, resource_type: str, actual: int, limit: int
    ) -> None:
        """Handle discovery limit exceeded."""
        discovery_opts = self.config.profiling.discovery_options
        action = discovery_opts.discovery_limit_action

        if action == "error":
            raise ValueError(
                f"{message}. Increase max_{resource_type}_per_pattern "
                "or set discovery_limit_action to 'warn'."
            )
        elif action == "skip":
            logger.warning(f"{message}. Skipping additional {resource_type}.")
        else:  # warn (default)
            logger.warning(
                f"{message}. Consider increasing max_{resource_type}_per_pattern "
                "in discovery_options."
            )

    def _resolve_precedence(self, patterns: List[TablePattern]) -> List[TablePattern]:
        """
        Resolve precedence and deduplicate patterns.

        Priority order (higher is better):
        - Explicit table: 100 (default)
        - Tag-based: 50 (if tags specified)
        - Pattern-based: 10 (default)
        - Schema-based: 5 (default)
        - Database-level: 1 (default)

        Args:
            patterns: List of TablePattern objects

        Returns:
            Deduplicated list with highest priority matches kept
        """
        if not patterns:
            return []

        # Calculate priority for each pattern
        pattern_priorities: Dict[str, Tuple[TablePattern, int]] = {}

        for pattern in patterns:
            key = self._table_key(pattern)

            # Calculate priority
            if pattern.override_priority is not None:
                priority = pattern.override_priority
            elif pattern.table and not pattern.pattern:
                # Explicit table
                priority = 100
            elif pattern.tags or pattern.tags_any:
                # Tag-based
                priority = 50
            elif pattern.pattern:
                # Pattern-based
                priority = 10
            elif pattern.select_schema:
                # Schema-based
                priority = 5
            elif pattern.select_all_schemas:
                # Database-level
                priority = 1
            else:
                # Default
                priority = 0

            # Keep highest priority
            if key not in pattern_priorities:
                pattern_priorities[key] = (pattern, priority)
            else:
                existing_pattern, existing_priority = pattern_priorities[key]
                if priority > existing_priority:
                    pattern_priorities[key] = (pattern, priority)
                    logger.debug(
                        f"Pattern for {key} replaced with higher priority pattern "
                        f"(old: {existing_priority}, new: {priority})"
                    )

        # Return patterns sorted by priority (highest first)
        sorted_patterns = sorted(pattern_priorities.values(), key=lambda x: x[1], reverse=True)
        return [pattern for pattern, _ in sorted_patterns]

    def _build_table_plan(
        self, pattern: TablePattern, decision: Optional[TableRunDecision]
    ) -> TablePlan:
        """
        Build plan for a single table pattern.

        Args:
            pattern: Table pattern from configuration

        Returns:
            TablePlan for this table
        """
        # Get metrics to compute
        metrics = self.config.profiling.metrics.copy()

        # Build metadata
        metadata: Dict[str, Any] = {
            "compute_histograms": self.config.profiling.compute_histograms,
            "histogram_bins": self.config.profiling.histogram_bins,
            "max_distinct_values": self.config.profiling.max_distinct_values,
        }

        # Get merged profiling config from contracts
        from .config.merger import ConfigMerger

        merger = ConfigMerger(self.config)
        profiling_config = merger.merge_profiling_config(
            table_pattern=pattern,
            database_name=pattern.database,
            schema=pattern.schema_,
            table=pattern.table,
        )

        # Convert partition/sampling configs to dicts
        partition_dict = (
            profiling_config["partition"].model_dump()
            if profiling_config.get("partition")
            else None
        )
        sampling_dict = (
            profiling_config["sampling"].model_dump() if profiling_config.get("sampling") else None
        )

        status = "ready"
        if decision:
            status = decision.action
            metadata.update(
                {
                    "incremental_reason": decision.reason,
                    "changed_partitions": decision.changed_partitions,
                    "estimated_cost": decision.estimated_cost,
                    "snapshot_id": decision.snapshot_id,
                }
            )

        # Ensure table name exists (should after expansion)
        table_name = pattern.table
        if not table_name:
            raise ValueError(f"TablePattern must have table name: {pattern}")

        return TablePlan(
            name=table_name,
            schema=pattern.schema_,
            status=status,
            partition_config=partition_dict,
            sampling_config=sampling_dict,
            metrics=metrics,
            metadata=metadata,
        )

    def _estimate_total_metrics(self, tables: List[TablePlan]) -> int:
        """
        Estimate total number of metrics that will be computed.

        This is a rough estimate assuming average column counts.

        Args:
            tables: List of table plans

        Returns:
            Estimated total number of metrics
        """
        # Rough estimate: assume 10 columns per table, each with all configured metrics
        avg_columns_per_table = 10
        metrics_per_column = len(self.config.profiling.metrics)

        return len(tables) * avg_columns_per_table * metrics_per_column

    def validate_plan(self, plan: ProfilingPlan) -> List[str]:
        """
        Validate the profiling plan.

        Args:
            plan: Profiling plan to validate

        Returns:
            List of validation warnings (empty if all valid)
        """
        warnings = []

        # Check for duplicate tables
        table_names = [t.full_name for t in plan.tables]
        duplicates = set([name for name in table_names if table_names.count(name) > 1])
        if duplicates:
            warnings.append(f"Duplicate tables in plan: {', '.join(duplicates)}")

        # Check sampling configuration
        for table in plan.tables:
            if table.sampling_config and table.sampling_config.get("enabled"):
                fraction = table.sampling_config.get("fraction", 0.01)
                if fraction <= 0.0 or fraction > 1.0:
                    warnings.append(
                        f"Invalid sampling fraction for {table.full_name}: {fraction} "
                        "(must be between 0.0 and 1.0)"
                    )

        # Check if any metrics are configured
        if not any(table.metrics for table in plan.tables):
            warnings.append("No metrics configured for profiling")

        return warnings

    def get_tables_to_run(
        self,
        current_time: Optional[datetime] = None,
        expanded_patterns: Optional[List[TablePattern]] = None,
    ) -> IncrementalPlan:
        """
        Expose incremental planner decisions for sensors/CLI.

        Args:
            current_time: Optional current time for incremental planning
            expanded_patterns: Optional expanded table patterns (will expand if not provided)

        Returns:
            IncrementalPlan with table run decisions
        """
        if self._incremental_planner is None:
            self._incremental_planner = IncrementalPlanner(self.config)

        # Expand patterns if not provided
        if expanded_patterns is None:
            expanded_patterns = self.expand_table_patterns()

        # Pass expanded patterns to incremental planner
        return self._incremental_planner.get_tables_to_run(
            current_time=current_time, expanded_patterns=expanded_patterns
        )

    def _expand_dbt_pattern(
        self, pattern: TablePattern, database: Optional[str] = None
    ) -> List[TablePattern]:
        """
        Expand dbt-based pattern (dbt_ref or dbt_selector) into concrete TablePattern objects.

        Args:
            pattern: TablePattern with dbt_ref or dbt_selector set
            database: Optional database name

        Returns:
            List of expanded TablePattern objects
        """
        if not DBT_AVAILABLE:
            logger.error(
                "dbt integration not available. Install dbt-core or ensure "
                "baselinr.integrations.dbt module is importable."
            )
            return []

        # Determine manifest path
        manifest_path = pattern.dbt_manifest_path
        project_path = pattern.dbt_project_path

        if not manifest_path and not project_path:
            logger.error(
                "dbt pattern requires either dbt_manifest_path or dbt_project_path to be set"
            )
            return []

        try:
            # Create manifest parser
            parser = DBTManifestParser(manifest_path=manifest_path, project_path=project_path)
            parser.load_manifest()

            expanded = []

            if pattern.dbt_ref:
                # Resolve single dbt ref
                result = parser.resolve_ref(pattern.dbt_ref)
                if result:
                    schema, table = result
                    table_pattern = pattern.model_copy(deep=True)
                    table_pattern.table = table
                    table_pattern.schema_ = schema
                    table_pattern.dbt_ref = None  # Clear dbt fields
                    table_pattern.dbt_selector = None
                    table_pattern.dbt_project_path = None
                    table_pattern.dbt_manifest_path = None
                    if database is not None:
                        table_pattern.database = database
                    expanded.append(table_pattern)
                else:
                    logger.warning(f"Could not resolve dbt ref: {pattern.dbt_ref}")

            elif pattern.dbt_selector:
                # Resolve dbt selector
                selector_resolver = DBTSelectorResolver(parser)
                models = selector_resolver.resolve_selector(pattern.dbt_selector)

                for model in models:
                    schema, table = parser.model_to_table(model)
                    table_pattern = pattern.model_copy(deep=True)
                    table_pattern.table = table
                    table_pattern.schema_ = schema
                    table_pattern.dbt_ref = None  # Clear dbt fields
                    table_pattern.dbt_selector = None
                    table_pattern.dbt_project_path = None
                    table_pattern.dbt_manifest_path = None
                    if database is not None:
                        table_pattern.database = database
                    expanded.append(table_pattern)

                if not expanded:
                    logger.warning(f"dbt selector '{pattern.dbt_selector}' matched no models")

            return expanded

        except Exception as e:
            logger.error(f"Failed to expand dbt pattern: {e}", exc_info=True)
            return []

    def _table_key(self, pattern: TablePattern) -> str:
        """Get unique key for table pattern."""
        table_name = pattern.table or pattern.pattern or "unknown"

        # Resolve database: use pattern.database or default to source.database
        database = pattern.database if pattern.database is not None else self.config.source.database

        # Build key: database.schema.table or database.table or schema.table or table
        parts = []
        if database:
            parts.append(database)
        if pattern.schema_:
            parts.append(pattern.schema_)
        parts.append(table_name)

        return ".".join(parts)


def print_plan(plan: ProfilingPlan, format: str = "text", verbose: bool = False):
    """
    Print profiling plan to stdout.

    Args:
        plan: Profiling plan to print
        format: Output format ("text" or "json")
        verbose: Whether to include verbose details
    """
    if format == "json":
        import json

        print(json.dumps(plan.to_dict(), indent=2))
    else:
        _print_text_plan(plan, verbose)


def _print_text_plan(plan: ProfilingPlan, verbose: bool = False):
    """Print plan in human-readable text format with Rich formatting."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        # Import from cli_output if available, otherwise define locally
        try:
            from ..cli_output import get_status_indicator, safe_print
        except ImportError:
            # Define locally if import fails
            def get_status_indicator(state: str) -> Text:
                color_map = {
                    "optimized": "#a78bfa",
                    "profiling": "#4a90e2",
                }
                color = color_map.get(state, "#4a90e2")
                return Text("●", style=f"bold {color}")

            def safe_print(*args, **kwargs) -> None:
                print(*args, **kwargs)

        console = Console()
        use_rich = True
    except (ImportError, AttributeError):
        use_rich = False
        console = None

        def get_status_indicator_dummy(_state: str) -> str:
            return ""

    if not use_rich or not console:
        # Fallback to plain text
        _print_text_plan_plain(plan, verbose)
        return

    # Header Panel
    header_text = "[bold]PROFILING EXECUTION PLAN[/bold]\n\n"
    header_text += f"Run ID: [cyan]{plan.run_id[:8]}...[/cyan]\n"
    header_text += f"Timestamp: [dim]{plan.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}[/dim]\n"
    header_text += f"Environment: [green]{plan.environment}[/green]\n"
    header_text += f"Source: [cyan]{plan.source_type}[/cyan] ([dim]{plan.source_database}[/dim])\n"
    header_text += f"Drift Strategy: [yellow]{plan.drift_strategy}[/yellow]"
    header_panel = Panel(header_text, border_style="#4a90e2", title="[bold]Plan[/bold]")
    console.print()
    console.print(header_panel)

    # Tables Table
    tables_table = Table(
        title=f"Tables to be Profiled ({plan.total_tables})",
        show_header=True,
        header_style="bold magenta",
    )
    tables_table.add_column("#", justify="right", style="dim")
    tables_table.add_column("Table", style="cyan")
    tables_table.add_column("Status", justify="center")
    tables_table.add_column("Partition", style="dim")
    tables_table.add_column("Sampling", style="dim")
    tables_table.add_column("Optimized", justify="center")

    for i, table in enumerate(plan.tables, 1):
        # Determine if optimized (sampling or partial partition)
        is_optimized = False
        optimized_indicator = ""
        if table.sampling_config and table.sampling_config.get("enabled"):
            is_optimized = True
            optimized_indicator = get_status_indicator("optimized")
        elif table.partition_config and table.partition_config.get("strategy") != "all":
            is_optimized = True
            optimized_indicator = get_status_indicator("optimized")

        # Format partition info
        partition_str = "full table"
        if table.partition_config:
            partition = table.partition_config
            strategy = partition.get("strategy", "all")
            if strategy != "all":
                partition_str = f"{strategy}"
                if partition.get("key"):
                    partition_str += f" on {partition['key']}"
                if partition.get("strategy") == "recent_n" and partition.get("recent_n"):
                    partition_str += f" (N={partition['recent_n']})"

        # Format sampling info
        sampling_str = "none"
        if table.sampling_config and table.sampling_config.get("enabled"):
            sampling = table.sampling_config
            fraction = sampling.get("fraction", 0.01) * 100
            method = sampling.get("method", "random")
            sampling_str = f"{method} ({fraction:.2f}%)"
            if sampling.get("max_rows"):
                sampling_str += f", max {sampling['max_rows']:,} rows"

        tables_table.add_row(
            str(i),
            table.full_name,
            table.status,
            partition_str,
            sampling_str,
            str(optimized_indicator) if is_optimized else "",
        )

    console.print()
    console.print(tables_table)

    # Summary Table
    summary_table = Table(title="Summary", show_header=True, header_style="bold green")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", justify="right", style="green")
    summary_table.add_row("Total Tables", str(plan.total_tables))
    summary_table.add_row("Estimated Metrics", f"~{plan.estimated_metrics}")

    if verbose:
        compute_hist = (
            plan.tables[0].metadata.get("compute_histograms", False) if plan.tables else "N/A"
        )
        hist_bins = plan.tables[0].metadata.get("histogram_bins", "N/A") if plan.tables else "N/A"
        max_dist = (
            plan.tables[0].metadata.get("max_distinct_values", "N/A") if plan.tables else "N/A"
        )
        summary_table.add_row("Compute Histograms", str(compute_hist))
        summary_table.add_row("Histogram Bins", str(hist_bins))
        summary_table.add_row("Max Distinct Values", str(max_dist))

    console.print()
    console.print(summary_table)

    # Configuration Details section (verbose only)
    if verbose:
        console.print()
        # Print title explicitly so it appears in captured output
        console.print("[bold yellow]Configuration Details[/bold yellow]")
        config_table = Table(
            show_header=True,
            header_style="bold yellow",
        )
        config_table.add_column("Setting", style="cyan")
        config_table.add_column("Value", justify="right", style="green")

        compute_hist = (
            plan.tables[0].metadata.get("compute_histograms", False) if plan.tables else "N/A"
        )
        hist_bins = plan.tables[0].metadata.get("histogram_bins", "N/A") if plan.tables else "N/A"
        max_dist = (
            plan.tables[0].metadata.get("max_distinct_values", "N/A") if plan.tables else "N/A"
        )

        config_table.add_row("Compute Histograms", str(compute_hist))
        config_table.add_row("Histogram Bins", str(hist_bins))
        config_table.add_row("Max Distinct Values", str(max_dist))

        console.print(config_table)


def _print_text_plan_plain(plan: ProfilingPlan, verbose: bool = False):
    """Print plan in plain text format (fallback)."""
    print("\n" + "=" * 70)
    print("PROFILING EXECUTION PLAN")
    print("=" * 70)

    # Header information
    print(f"\nRun ID: {plan.run_id}")
    print(f"Timestamp: {plan.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Environment: {plan.environment}")
    print(f"Source: {plan.source_type} ({plan.source_database})")
    print(f"Drift Strategy: {plan.drift_strategy}")

    # Tables section
    print(f"\n{'-' * 70}")
    print(f"TABLES TO BE PROFILED ({plan.total_tables})")
    print("-" * 70)

    for i, table in enumerate(plan.tables, 1):
        print(f"\n{i}. {table.full_name}")
        print(f"   Status: {table.status}")

        # Show partition configuration
        if table.partition_config:
            partition = table.partition_config
            print(f"   Partition: {partition.get('strategy', 'all')}", end="")
            if partition.get("key"):
                print(f" on {partition['key']}", end="")
            if partition.get("strategy") == "recent_n" and partition.get("recent_n"):
                print(f" (N={partition['recent_n']})", end="")
            print()
        else:
            print("   Partition: full table")

        # Show sampling configuration
        if table.sampling_config and table.sampling_config.get("enabled"):
            sampling = table.sampling_config
            fraction = sampling.get("fraction", 0.01) * 100
            method = sampling.get("method", "random")
            print(f"   Sampling: {method} ({fraction:.2f}%)", end="")
            if sampling.get("max_rows"):
                print(f", max {sampling['max_rows']:,} rows", end="")
            print()
        else:
            print("   Sampling: none (full dataset)")

        if verbose:
            print(f"   Metrics ({len(table.metrics)}): {', '.join(table.metrics)}")
            if table.metadata:
                print("   Configuration:")
                for key, value in table.metadata.items():
                    print(f"     - {key}: {value}")

    # Summary
    print(f"\n{'-' * 70}")
    print("SUMMARY")
    print("-" * 70)
    print(f"Total Tables: {plan.total_tables}")
    print(f"Estimated Metrics: ~{plan.estimated_metrics}")

    if verbose:
        print("\nConfiguration Details:")
        compute_hist = (
            plan.tables[0].metadata.get("compute_histograms", False) if plan.tables else "N/A"
        )
        print(f"  - Compute Histograms: {compute_hist}")
        hist_bins = plan.tables[0].metadata.get("histogram_bins", "N/A") if plan.tables else "N/A"
        print(f"  - Histogram Bins: {hist_bins}")
        max_dist = (
            plan.tables[0].metadata.get("max_distinct_values", "N/A") if plan.tables else "N/A"
        )
        print(f"  - Max Distinct Values: {max_dist}")

    print("\n" + "=" * 70)
    print(f"Plan built successfully. Ready to profile {plan.total_tables} table(s).")
    print("=" * 70 + "\n")
