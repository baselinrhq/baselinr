"""Configuration merger for applying dataset-level overrides."""

import logging
from copy import deepcopy
from typing import Any, Dict, List, Optional

from .schema import (
    BaselinrConfig,
    ColumnConfig,
    DatasetConfig,
    DriftDetectionConfig,
    TablePattern,
    ValidationRuleConfig,
)

logger = logging.getLogger(__name__)


class ConfigMerger:
    """Merges dataset-level overrides with global and table-level configs."""

    def __init__(self, config: Optional[BaselinrConfig] = None):
        """Initialize config merger.

        Args:
            config: BaselinrConfig instance (optional)
        """
        self.config = config
        self.datasets: List[DatasetConfig] = []
        if config and config.datasets:
            self.datasets = config.datasets.datasets

    def find_matching_dataset(
        self, database: Optional[str], schema: Optional[str], table: Optional[str]
    ) -> Optional[DatasetConfig]:
        """Find matching dataset config for given database/schema/table.

        Matching rules:
        - All specified fields must match (None = wildcard)
        - More specific matches take precedence

        Args:
            database: Database name (or None)
            schema: Schema name (or None)
            table: Table name (or None)

        Returns:
            Matching DatasetConfig or None
        """
        matches = []
        for dataset in self.datasets:
            # Check if all specified fields match
            db_match = dataset.database is None or dataset.database == database
            schema_match = dataset.schema_ is None or dataset.schema_ == schema
            table_match = dataset.table is None or dataset.table == table

            if db_match and schema_match and table_match:
                matches.append(dataset)

        if not matches:
            return None

        # Return most specific match (fewest None values)
        # Sort by specificity: more specific = fewer None values
        matches.sort(
            key=lambda d: (
                d.database is None,
                d.schema_ is None,
                d.table is None,
            )
        )
        return matches[0]

    def merge_profiling_config(
        self,
        table_pattern: TablePattern,
        database_name: Optional[str] = None,
        schema: Optional[str] = None,
        table: Optional[str] = None,
    ) -> TablePattern:
        """Merge profiling config with dataset overrides.

        Args:
            table_pattern: Table pattern to merge
            database_name: Database name (defaults to table_pattern.database)
            schema: Schema name (defaults to table_pattern.schema_)
            table: Table name (defaults to table_pattern.table)

        Returns:
            Merged TablePattern
        """
        # Use provided values or fall back to table_pattern
        db = database_name or table_pattern.database
        schema_name = schema or table_pattern.schema_
        table_name = table or table_pattern.table

        dataset = self.find_matching_dataset(db, schema_name, table_name)
        if not dataset or not dataset.profiling:
            return table_pattern

        # Create a copy to avoid modifying original
        merged = deepcopy(table_pattern)

        # Merge partition config (only if table_pattern doesn't have one)
        if dataset.profiling.partition and merged.partition is None:
            merged.partition = deepcopy(dataset.profiling.partition)

        # Merge sampling config (only if table_pattern doesn't have one)
        if dataset.profiling.sampling and merged.sampling is None:
            merged.sampling = deepcopy(dataset.profiling.sampling)

        # Merge column configs (append dataset columns to table columns)
        if dataset.profiling.columns:
            if merged.columns is None:
                merged.columns = []
            # Table columns come first (higher priority)
            merged.columns = list(merged.columns) + [
                deepcopy(col) for col in dataset.profiling.columns
            ]

        return merged

    def merge_drift_config(
        self, database: Optional[str], schema: Optional[str], table: Optional[str]
    ) -> Optional[DriftDetectionConfig]:
        """Merge drift detection config with dataset overrides.

        Args:
            database: Database name
            schema: Schema name
            table: Table name

        Returns:
            Merged DriftDetectionConfig or None if no config
        """
        # Start with global config
        if not self.config:
            return None
        base_config = self.config.drift_detection
        merged = deepcopy(base_config)

        dataset = self.find_matching_dataset(database, schema, table)
        if not dataset or not dataset.drift:
            return merged

        # Merge strategy
        if dataset.drift.strategy is not None:
            merged.strategy = dataset.drift.strategy

        # Merge thresholds
        if dataset.drift.absolute_threshold:
            if merged.absolute_threshold is None:
                merged.absolute_threshold = {}
            merged.absolute_threshold.update(dataset.drift.absolute_threshold)

        if dataset.drift.statistical:
            if merged.statistical is None:
                merged.statistical = {}
            merged.statistical.update(dataset.drift.statistical)

        return merged

    def get_validation_rules(
        self, database: Optional[str], schema: Optional[str], table: Optional[str]
    ) -> List[ValidationRuleConfig]:
        """Get validation rules (global + dataset-specific).

        Args:
            database: Database name
            schema: Schema name
            table: Table name

        Returns:
            List of ValidationRuleConfig
        """
        rules = []

        # Add global rules
        if self.config and self.config.validation and self.config.validation.rules:
            rules.extend(self.config.validation.rules)

        # Add dataset-specific rules
        dataset = self.find_matching_dataset(database, schema, table)
        if dataset and dataset.validation and dataset.validation.rules:
            for rule in dataset.validation.rules:
                # Set table name if not provided
                rule_copy = deepcopy(rule)
                if rule_copy.table is None and table:
                    rule_copy.table = table
                rules.append(rule_copy)

        return rules

    def get_anomaly_column_configs(
        self, database: Optional[str], schema: Optional[str], table: Optional[str]
    ) -> List[ColumnConfig]:
        """Get anomaly column configs from dataset.

        Args:
            database: Database name
            schema: Schema name
            table: Table name

        Returns:
            List of ColumnConfig with anomaly settings
        """
        dataset = self.find_matching_dataset(database, schema, table)
        if not dataset or not dataset.anomaly or not dataset.anomaly.columns:
            return []

        return [deepcopy(col) for col in dataset.anomaly.columns]

    def get_drift_column_configs(
        self, database: Optional[str], schema: Optional[str], table: Optional[str]
    ) -> List[ColumnConfig]:
        """Get drift column configs from dataset.

        Args:
            database: Database name
            schema: Schema name
            table: Table name

        Returns:
            List of ColumnConfig with drift settings
        """
        dataset = self.find_matching_dataset(database, schema, table)
        if not dataset or not dataset.drift or not dataset.drift.columns:
            return []

        return [deepcopy(col) for col in dataset.drift.columns]

    def resolve_table_config(self, table_pattern: TablePattern) -> Dict[str, Any]:
        """Resolve complete table config with all feature overrides.

        Args:
            table_pattern: Table pattern to resolve

        Returns:
            Dict with keys: profiling, drift, validation_rules, anomaly_columns, drift_columns
        """
        db = table_pattern.database
        schema = table_pattern.schema_
        table = table_pattern.table

        return {
            "profiling": self.merge_profiling_config(table_pattern, db, schema, table),
            "drift": self.merge_drift_config(db, schema, table),
            "validation_rules": self.get_validation_rules(db, schema, table),
            "anomaly_columns": self.get_anomaly_column_configs(db, schema, table),
            "drift_columns": self.get_drift_column_configs(db, schema, table),
        }
