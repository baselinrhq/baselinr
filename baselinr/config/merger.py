"""Configuration merger for applying dataset-level overrides."""

import logging
from copy import deepcopy
from typing import Any, Dict, List, Optional

from .schema import (
    BaselinrConfig,
    ColumnConfig,
    DatasetConfig,
    DatasetsConfig,
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
            # ConfigLoader should have already converted DatasetsDirectoryConfig to DatasetsConfig
            # but we check to be safe for type checking
            if isinstance(config.datasets, DatasetsConfig):
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
    ) -> Dict[str, Any]:
        """Merge profiling config with dataset overrides.

        Args:
            table_pattern: Table pattern (for selection only, no profiling config)
            database_name: Database name (defaults to table_pattern.database)
            schema: Schema name (defaults to table_pattern.schema_)
            table: Table name (defaults to table_pattern.table)

        Returns:
            Dict with merged profiling config: partition, sampling, columns
        """
        # Use provided values or fall back to table_pattern
        db = database_name or table_pattern.database
        schema_name = schema or table_pattern.schema_
        table_name = table or table_pattern.table

        dataset = self.find_matching_dataset(db, schema_name, table_name)
        if not dataset:
            return {
                "partition": None,
                "sampling": None,
                "columns": None,
            }

        # Get partition and sampling from profiling config
        partition = None
        sampling = None
        if dataset.profiling:
            partition = (
                deepcopy(dataset.profiling.partition) if dataset.profiling.partition else None
            )
            sampling = deepcopy(dataset.profiling.sampling) if dataset.profiling.sampling else None

        # Get columns from unified columns field (Phase 3.5)
        columns = None
        if dataset.columns:
            columns = [deepcopy(col) for col in dataset.columns]

        return {
            "partition": partition,
            "sampling": sampling,
            "columns": columns,
        }

    def merge_drift_config(
        self, database: Optional[str], schema: Optional[str], table: Optional[str]
    ) -> Optional[DriftDetectionConfig]:
        """Merge drift detection config with dataset overrides.

        All dataset-level drift configuration must be in the `datasets` section.
        The global `drift_detection` section should only contain default values.

        Args:
            database: Database name
            schema: Schema name
            table: Table name

        Returns:
            Merged DriftDetectionConfig or None if no config
        """
        # Start with global config (defaults only)
        if not self.config:
            return None
        base_config = self.config.drift_detection
        merged = deepcopy(base_config)

        # Get dataset-specific overrides from datasets section
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

        if dataset.drift.standard_deviation:
            if merged.standard_deviation is None:
                merged.standard_deviation = {}
            merged.standard_deviation.update(dataset.drift.standard_deviation)

        if dataset.drift.statistical:
            if merged.statistical is None:
                merged.statistical = {}
            merged.statistical.update(dataset.drift.statistical)

        if dataset.drift.baselines:
            if merged.baselines is None:
                merged.baselines = {}
            merged.baselines.update(dataset.drift.baselines)

        return merged

    def get_validation_rules(
        self, database: Optional[str], schema: Optional[str], table: Optional[str]
    ) -> List[ValidationRuleConfig]:
        """Get validation rules from datasets section.

        All validation rules must be defined in the `datasets` section.
        Column-specific rules should be in `columns[].validation.rules`.
        Table-level rules (without column) should be in `validation.rules`.

        Args:
            database: Database name
            schema: Schema name
            table: Table name

        Returns:
            List of ValidationRuleConfig
        """
        rules: List[ValidationRuleConfig] = []

        # Get global rules (dataset with no table/schema/database specified)
        global_dataset = self.find_matching_dataset(None, None, None)
        if global_dataset:
            # Get table-level rules from validation.rules
            if global_dataset.validation and global_dataset.validation.rules:
                for rule in global_dataset.validation.rules:
                    rule_copy = deepcopy(rule)
                    # Set table name if not provided and we have a table context
                    if rule_copy.table is None and table:
                        rule_copy.table = table
                    rules.append(rule_copy)

            # Get column-level rules from columns[].validation.rules (Phase 3.5)
            if global_dataset.columns:
                for col in global_dataset.columns:
                    if col.validation and col.validation.rules:
                        for rule in col.validation.rules:
                            rule_copy = deepcopy(rule)
                            # Set table and column from context
                            if rule_copy.table is None and table:
                                rule_copy.table = table
                            if rule_copy.column is None:
                                rule_copy.column = col.name
                            rules.append(rule_copy)

        # Add dataset-specific rules (more specific matches override global)
        # Only process if it's a different dataset than the global one
        dataset = self.find_matching_dataset(database, schema, table)
        if dataset and dataset != global_dataset:
            # Get table-level rules from validation.rules
            if dataset.validation and dataset.validation.rules:
                for rule in dataset.validation.rules:
                    # Set table name if not provided
                    rule_copy = deepcopy(rule)
                    if rule_copy.table is None and table:
                        rule_copy.table = table
                    rules.append(rule_copy)

            # Get column-level rules from columns[].validation.rules (Phase 3.5)
            if dataset.columns:
                for col in dataset.columns:
                    if col.validation and col.validation.rules:
                        for rule in col.validation.rules:
                            rule_copy = deepcopy(rule)
                            # Set table and column from context
                            if rule_copy.table is None and table:
                                rule_copy.table = table
                            if rule_copy.column is None:
                                rule_copy.column = col.name
                            rules.append(rule_copy)

        return rules

    def get_anomaly_column_configs(
        self, database: Optional[str], schema: Optional[str], table: Optional[str]
    ) -> List[ColumnConfig]:
        """Get anomaly column configs from dataset.

        Column configs are read from the unified `columns` field (Phase 3.5).

        Args:
            database: Database name
            schema: Schema name
            table: Table name

        Returns:
            List of ColumnConfig with anomaly settings
        """
        dataset = self.find_matching_dataset(database, schema, table)
        if not dataset or not dataset.columns:
            return []

        # Filter columns that have anomaly config
        anomaly_cols = [col for col in dataset.columns if col.anomaly]
        return [deepcopy(col) for col in anomaly_cols]

    def get_drift_column_configs(
        self, database: Optional[str], schema: Optional[str], table: Optional[str]
    ) -> List[ColumnConfig]:
        """Get drift column configs from dataset.

        Column configs are read from the unified `columns` field (Phase 3.5).

        Args:
            database: Database name
            schema: Schema name
            table: Table name

        Returns:
            List of ColumnConfig with drift settings
        """
        dataset = self.find_matching_dataset(database, schema, table)
        if not dataset or not dataset.columns:
            return []

        # Filter columns that have drift config
        drift_cols = [col for col in dataset.columns if col.drift]
        return [deepcopy(col) for col in drift_cols]

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

        profiling_config = self.merge_profiling_config(table_pattern, db, schema, table)
        return {
            "profiling": profiling_config,
            "drift": self.merge_drift_config(db, schema, table),
            "validation_rules": self.get_validation_rules(db, schema, table),
            "anomaly_columns": self.get_anomaly_column_configs(db, schema, table),
            "drift_columns": self.get_drift_column_configs(db, schema, table),
        }
