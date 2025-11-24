"""
Column name pattern matching utility for Baselinr.

Supports matching column names against patterns (wildcards and regex)
to determine which columns should be profiled based on column-level configurations.
"""

import fnmatch
import logging
import re
from typing import List, Optional, Set, Tuple

from ..config.schema import ColumnConfig

logger = logging.getLogger(__name__)


class ColumnMatcher:
    """Matches column names against patterns and manages column configurations."""

    def __init__(self, column_configs: Optional[List[ColumnConfig]] = None):
        """
        Initialize column matcher.

        Args:
            column_configs: List of column-level configurations to match against
        """
        self.column_configs = column_configs or []
        self._compiled_patterns: List[Tuple[ColumnConfig, Optional[re.Pattern]]] = []

        # Compile regex patterns for faster matching
        for config in self.column_configs:
            if config.pattern_type == "regex":
                try:
                    pattern = re.compile(config.name)
                    self._compiled_patterns.append((config, pattern))
                except re.error as e:
                    logger.warning(
                        f"Invalid regex pattern '{config.name}': {e}. " "Treating as literal."
                    )
                    # Fall back to literal matching
                    self._compiled_patterns.append((config, None))

    def matches(self, column_name: str, config: ColumnConfig) -> bool:
        """
        Check if a column name matches a configuration pattern.

        Args:
            column_name: Name of the column to check
            config: Column configuration to match against

        Returns:
            True if column matches the pattern, False otherwise
        """
        if config.pattern_type == "regex":
            # Find compiled pattern
            compiled = None
            for cfg, pat in self._compiled_patterns:
                if cfg == config:
                    compiled = pat
                    break

            if compiled is not None:
                return bool(compiled.match(column_name))
            else:
                # Fallback: compile on the fly
                try:
                    pattern = re.compile(config.name)
                    return bool(pattern.match(column_name))
                except re.error:
                    logger.warning(f"Invalid regex pattern '{config.name}'. Treating as literal.")
                    return column_name == config.name
        else:
            # Default: wildcard matching using fnmatch
            return fnmatch.fnmatch(column_name, config.name)

    def find_matching_config(self, column_name: str) -> Optional[ColumnConfig]:
        """
        Find the first matching column configuration for a column name.

        Args:
            column_name: Name of the column to find config for

        Returns:
            First matching ColumnConfig, or None if no match
        """
        for config in self.column_configs:
            if self.matches(column_name, config):
                return config
        return None

    def find_all_matching_configs(self, column_name: str) -> List[ColumnConfig]:
        """
        Find all matching column configurations for a column name.

        Args:
            column_name: Name of the column to find configs for

        Returns:
            List of matching ColumnConfigs (may be empty)
        """
        matches = []
        for config in self.column_configs:
            if self.matches(column_name, config):
                matches.append(config)
        return matches

    def get_profiled_columns(
        self, all_columns: List[str], include_defaults: bool = True
    ) -> Set[str]:
        """
        Get set of column names that should be profiled based on column configs.

        Args:
            all_columns: List of all column names in the table
            include_defaults: If True, include columns not explicitly configured
                             (default behavior when no column configs specified)

        Returns:
            Set of column names that should be profiled
        """
        profiled = set()

        # If no column configs specified, profile all columns (backward compatibility)
        if not self.column_configs:
            if include_defaults:
                return set(all_columns)
            else:
                return set()

        # Process each column
        for column_name in all_columns:
            matching_configs = self.find_all_matching_configs(column_name)

            if matching_configs:
                # Use the first matching config (can be enhanced later for priority/precedence)
                config = matching_configs[0]

                # Check if profiling is enabled (default: True)
                profiling_enabled = True
                if config.profiling and config.profiling.enabled is not None:
                    profiling_enabled = config.profiling.enabled

                if profiling_enabled:
                    profiled.add(column_name)
            elif include_defaults:
                # No matching config, use default behavior (profile all)
                profiled.add(column_name)

        return profiled

    def should_profile_column(self, column_name: str) -> bool:
        """
        Check if a column should be profiled.

        Args:
            column_name: Name of the column to check

        Returns:
            True if column should be profiled, False otherwise
        """
        # If no column configs, profile everything (backward compatibility)
        if not self.column_configs:
            return True

        matching_config = self.find_matching_config(column_name)

        if matching_config:
            # Check if profiling is enabled (default: True)
            if matching_config.profiling and matching_config.profiling.enabled is not None:
                return matching_config.profiling.enabled
            return True  # Default: enabled

        # No matching config: use default behavior (profile all)
        return True

    def get_column_metrics(self, column_name: str) -> Optional[List[str]]:
        """
        Get list of metrics to compute for a column.

        Args:
            column_name: Name of the column

        Returns:
            List of metric names, or None if using defaults
        """
        matching_config = self.find_matching_config(column_name)
        if matching_config and matching_config.metrics:
            return matching_config.metrics
        return None

    def get_column_drift_config(self, column_name: str) -> Optional[ColumnConfig]:
        """
        Get drift detection configuration for a column.

        Args:
            column_name: Name of the column

        Returns:
            ColumnConfig if drift config exists, None otherwise
        """
        matching_config = self.find_matching_config(column_name)
        if matching_config and matching_config.drift:
            return matching_config
        return None

    def get_column_anomaly_config(self, column_name: str) -> Optional[ColumnConfig]:
        """
        Get anomaly detection configuration for a column.

        Args:
            column_name: Name of the column

        Returns:
            ColumnConfig if anomaly config exists, None otherwise
        """
        matching_config = self.find_matching_config(column_name)
        if matching_config and matching_config.anomaly:
            return matching_config
        return None
