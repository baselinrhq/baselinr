"""Configuration merger for applying contract-level overrides from ODCS."""

import logging
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from .schema import (
    BaselinrConfig,
    ColumnAnomalyConfig,
    ColumnConfig,
    ColumnDriftConfig,
    DriftDetectionConfig,
    PartitionConfig,
    SamplingConfig,
    TablePattern,
    ValidationRuleConfig,
)

logger = logging.getLogger(__name__)


class ConfigMerger:
    """Merges contract-level overrides from ODCS with global configs."""

    def __init__(self, config: Optional[BaselinrConfig] = None):
        """Initialize config merger.

        Args:
            config: BaselinrConfig instance (optional)
        """
        self.config = config
        self._contracts_cache: Optional[List[Any]] = None

    def _load_contracts(self) -> List[Any]:
        """Load ODCS contracts if not already cached.

        Loads contracts from the configured directory. Contracts are cached
        to avoid reloading on every merge operation.
        """
        if self._contracts_cache is not None:
            return self._contracts_cache

        if not self.config or not self.config.contracts:
            self._contracts_cache = []
            return []

        try:
            from pathlib import Path

            from ..contracts import ContractLoader

            contracts_dir = self.config.contracts.directory
            # Resolve relative path (assumes current working directory)
            if not Path(contracts_dir).is_absolute():
                contracts_dir = str(Path(contracts_dir).resolve())

            loader = ContractLoader(
                validate_on_load=self.config.contracts.validate_on_load,
                file_patterns=self.config.contracts.file_patterns,
            )
            contracts = loader.load_from_directory(
                contracts_dir,
                recursive=self.config.contracts.recursive,
                exclude_patterns=self.config.contracts.exclude_patterns,
            )
            self._contracts_cache = contracts
            logger.debug(f"Loaded {len(contracts)} contracts for config merging")
            return contracts
        except Exception as e:
            logger.debug(f"Failed to load contracts for config merging: {e}")
            self._contracts_cache = []
            return []

    def _find_matching_contract_dataset(
        self,
        database: Optional[str],
        schema: Optional[str],
        table: Optional[str],
    ) -> Tuple[Optional[Any], Optional[Any]]:
        """Find matching dataset and contract for given database/schema/table.

        Returns:
            Tuple of (dataset, contract) or (None, None) if not found
        """
        contracts = self._load_contracts()

        for contract in contracts:
            if not contract.dataset:
                continue

            for ds in contract.dataset:
                # Match by name or physicalName
                ds_name = ds.name or ""
                ds_physical = ds.physicalName or ""

                # Check if table matches
                table_match = False
                if table:
                    # Match by name
                    if ds_name == table or ds_physical.endswith(f".{table}"):
                        table_match = True
                    # Match by physical name components
                    if ds_physical:
                        parts = ds_physical.split(".")
                        if len(parts) >= 1 and parts[-1] == table:
                            table_match = True

                if not table_match:
                    continue

                # Check schema match if provided
                if schema:
                    if ds_physical:
                        parts = ds_physical.split(".")
                        if len(parts) >= 2:
                            ds_schema = parts[-2] if len(parts) == 2 else parts[-3]
                            if ds_schema != schema:
                                continue

                # Check database match if provided
                if database:
                    if ds_physical:
                        parts = ds_physical.split(".")
                        if len(parts) >= 3:
                            ds_db = parts[0]
                            if ds_db != database:
                                continue

                return (ds, contract)

        return (None, None)

    def merge_profiling_config(
        self,
        table_pattern: TablePattern,
        database_name: Optional[str] = None,
        schema: Optional[str] = None,
        table: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Merge profiling config with contract overrides.

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

        # Find matching contract dataset and contract
        dataset, contract = self._find_matching_contract_dataset(db, schema_name, table_name)

        partition_config = None
        sampling_config = None
        column_configs = None

        if dataset and contract:
            # Extract partition config from columns (partitionStatus flag)
            partition_cols = [col for col in (dataset.columns or []) if col.partitionStatus]
            if partition_cols:
                partition_col = partition_cols[0]
                # Extract partition strategy from customProperties if available
                strategy = "latest"  # Default
                recent_n = None
                values = None

                # Check contract-level customProperties for partition config
                if contract.customProperties:
                    for prop in contract.customProperties:
                        # Handle both dict and ODCSCustomProperty object
                        if isinstance(prop, dict):
                            prop_name = prop.get("property", "")
                            prop_value = prop.get("value")
                        else:
                            prop_name = getattr(prop, "property", "")
                            prop_value = getattr(prop, "value", None)

                        if prop_name == f"baselinr.partition.{table_name}":
                            if isinstance(prop_value, dict):
                                strategy = prop_value.get("strategy", "latest")
                                recent_n = prop_value.get("recent_n")
                                values = prop_value.get("values")
                                break

                partition_config = PartitionConfig(
                    key=partition_col.name,
                    strategy=strategy,
                    recent_n=recent_n,
                    values=values,
                    metadata_fallback=True,
                )

            # Extract sampling from customProperties (Baselinr-specific)
            # ODCS doesn't have native sampling, so we use customProperties
            if contract.customProperties:
                for prop in contract.customProperties:
                    # Handle both dict and ODCSCustomProperty object
                    if isinstance(prop, dict):
                        prop_name = prop.get("property", "")
                        prop_value = prop.get("value")
                    else:
                        prop_name = getattr(prop, "property", "")
                        prop_value = getattr(prop, "value", None)

                    # Support both contract-level and dataset-level customProperties
                    if (
                        prop_name == f"baselinr.sampling.{table_name}"
                        or prop_name == "baselinr.sampling"
                    ):
                        if isinstance(prop_value, dict):
                            sampling_config = SamplingConfig(
                                enabled=prop_value.get("enabled", False),
                                method=prop_value.get("method", "random"),
                                fraction=prop_value.get("fraction", 0.1),
                                max_rows=prop_value.get("max_rows"),
                            )
                            break

            # Extract column configs
            if dataset.columns:
                column_configs = []
                for col in dataset.columns:
                    col_config = ColumnConfig(name=col.name)  # type: ignore[call-arg]
                    # Add profiling config if needed
                    # Note: ODCS doesn't have column-level profiling configs in standard
                    # but we can extract from customProperties if needed
                    column_configs.append(col_config)

        return {
            "partition": partition_config,
            "sampling": sampling_config,
            "columns": column_configs,
        }

    def merge_drift_config(
        self, database: Optional[str], schema: Optional[str], table: Optional[str]
    ) -> Optional[DriftDetectionConfig]:
        """Merge drift detection config with contract overrides.

        Args:
            database: Database name
            schema: Schema name
            table: Table name

        Returns:
            Merged DriftDetectionConfig or None if no config
        """
        # Start with global config (defaults)
        if not self.config:
            return None
        base_config = self.config.drift_detection
        merged = deepcopy(base_config)

        # Find matching contract dataset and contract
        dataset, contract = self._find_matching_contract_dataset(database, schema, table)

        if dataset and contract:
            # Extract drift config from contract customProperties
            if contract.customProperties:
                for prop in contract.customProperties:
                    # Handle both dict and ODCSCustomProperty object
                    if isinstance(prop, dict):
                        prop_name = prop.get("property", "")
                        prop_value = prop.get("value")
                    else:
                        prop_name = getattr(prop, "property", "")
                        prop_value = getattr(prop, "value", None)

                    # Extract drift strategy
                    if (
                        prop_name == f"baselinr.drift.strategy.{table}"
                        or prop_name == "baselinr.drift.strategy"
                    ):
                        if isinstance(prop_value, str):
                            merged.strategy = prop_value

                    # Extract absolute threshold overrides
                    if (
                        prop_name == f"baselinr.drift.absolute_threshold.{table}"
                        or prop_name == "baselinr.drift.absolute_threshold"
                    ):
                        if isinstance(prop_value, dict):
                            merged.absolute_threshold.update(prop_value)

                    # Extract standard deviation overrides
                    if (
                        prop_name == f"baselinr.drift.standard_deviation.{table}"
                        or prop_name == "baselinr.drift.standard_deviation"
                    ):
                        if isinstance(prop_value, dict):
                            merged.standard_deviation.update(prop_value)

                    # Extract statistical test overrides
                    if (
                        prop_name == f"baselinr.drift.statistical.{table}"
                        or prop_name == "baselinr.drift.statistical"
                    ):
                        if isinstance(prop_value, dict):
                            merged.statistical.update(prop_value)

                    # Extract baseline overrides
                    if (
                        prop_name == f"baselinr.drift.baselines.{table}"
                        or prop_name == "baselinr.drift.baselines"
                    ):
                        if isinstance(prop_value, dict):
                            merged.baselines.update(prop_value)

        return merged

    def get_validation_rules(
        self, database: Optional[str], schema: Optional[str], table: Optional[str]
    ) -> List[ValidationRuleConfig]:
        """Get validation rules from contract.

        Validation rules are extracted from ODCS quality rules in the contract.

        Args:
            database: Database name
            schema: Schema name
            table: Table name

        Returns:
            List of ValidationRuleConfig
        """
        # Find matching contract dataset and contract
        dataset, contract = self._find_matching_contract_dataset(database, schema, table)

        if not dataset or not contract:
            return []

        # Use ODCSAdapter to convert quality rules to validation rules
        from ..contracts.adapter import ODCSAdapter

        adapter = ODCSAdapter()
        adapter_rules = adapter.to_validation_rules(contract)

        # Filter rules for this specific table/dataset
        # Match by table name - need to handle both physicalName and name
        table_name = table or ""
        dataset_physical = dataset.physicalName or dataset.name or ""

        validation_rules = []

        for adapter_rule in adapter_rules:
            # Match by table name - check if rule's table matches our target
            rule_table = adapter_rule.table or ""
            table_matches = False

            # Direct match
            if rule_table == table_name or rule_table == dataset_physical:
                table_matches = True
            # Check if rule table ends with our table name (for schema.table format)
            elif table_name and (rule_table.endswith(f".{table_name}") or rule_table == table_name):
                table_matches = True
            # Check if dataset physical name matches
            elif dataset_physical and (
                rule_table == dataset_physical or rule_table.endswith(f".{dataset_physical}")
            ):
                table_matches = True

            if table_matches:
                # Convert adapter rule to ValidationRuleConfig
                # Map ODCS severity (error, warning, info, critical)
                # to Baselinr severity (low, medium, high)
                severity_map = {
                    "error": "high",
                    "critical": "high",
                    "warning": "medium",
                    "info": "low",
                }
                severity_input = (
                    adapter_rule.severity.lower() if adapter_rule.severity else "medium"
                )
                baselinr_severity = severity_map.get(severity_input, "medium")
                rule_config = ValidationRuleConfig(
                    type=adapter_rule.type,
                    column=adapter_rule.column,
                    severity=baselinr_severity,
                    enabled=adapter_rule.enabled,
                )  # type: ignore[call-arg]

                # Add rule-specific parameters
                if adapter_rule.pattern:
                    rule_config.pattern = adapter_rule.pattern
                if adapter_rule.min_value is not None:
                    rule_config.min_value = adapter_rule.min_value
                if adapter_rule.max_value is not None:
                    rule_config.max_value = adapter_rule.max_value
                if adapter_rule.allowed_values:
                    rule_config.allowed_values = adapter_rule.allowed_values
                # Handle referential rules - convert to references dict
                if adapter_rule.reference_table or adapter_rule.reference_column:
                    rule_config.references = {
                        "table": adapter_rule.reference_table or "",
                        "column": adapter_rule.reference_column or "",
                    }
                # Note: threshold is not a direct field in ValidationRuleConfig
                # It may need to be handled differently based on rule type
                if adapter_rule.description:
                    # ValidationRuleConfig doesn't have description field, skip it
                    pass

                validation_rules.append(rule_config)

        return validation_rules

    def get_anomaly_column_configs(
        self, database: Optional[str], schema: Optional[str], table: Optional[str]
    ) -> List[ColumnConfig]:
        """Get anomaly column configs from contract.

        Column-level anomaly detection configs are extracted from contract
        customProperties or column metadata.

        Args:
            database: Database name
            schema: Schema name
            table: Table name

        Returns:
            List of ColumnConfig with anomaly settings
        """
        # Find matching contract dataset and contract
        dataset, contract = self._find_matching_contract_dataset(database, schema, table)

        if not dataset or not contract:
            return []

        column_configs = []

        if dataset.columns:
            for col in dataset.columns:
                col_config = ColumnConfig(name=col.name)  # type: ignore[call-arg]

                # Extract anomaly config from contract customProperties
                if contract.customProperties:
                    for prop in contract.customProperties:
                        # Handle both dict and ODCSCustomProperty object
                        if isinstance(prop, dict):
                            prop_name = prop.get("property", "")
                            prop_value = prop.get("value")
                        else:
                            prop_name = getattr(prop, "property", "")
                            prop_value = getattr(prop, "value", None)

                        # Check for column-specific anomaly config
                        anomaly_prop = f"baselinr.anomaly.{table}.{col.name}"
                        if prop_name == anomaly_prop or prop_name == f"baselinr.anomaly.{col.name}":
                            if isinstance(prop_value, dict):
                                col_config.anomaly = ColumnAnomalyConfig(
                                    enabled=prop_value.get("enabled", True),
                                    methods=prop_value.get("methods"),
                                    thresholds=prop_value.get("thresholds"),
                                )
                                break

                # If no explicit config found but column exists, create default enabled config
                if not col_config.anomaly:
                    col_config.anomaly = ColumnAnomalyConfig(enabled=True)  # type: ignore[call-arg]

                column_configs.append(col_config)

        return column_configs

    def get_drift_column_configs(
        self, database: Optional[str], schema: Optional[str], table: Optional[str]
    ) -> List[ColumnConfig]:
        """Get drift column configs from contract.

        Column-level drift detection configs are extracted from contract
        customProperties or column metadata.

        Args:
            database: Database name
            schema: Schema name
            table: Table name

        Returns:
            List of ColumnConfig with drift settings
        """
        # Find matching contract dataset and contract
        dataset, contract = self._find_matching_contract_dataset(database, schema, table)

        if not dataset or not contract:
            return []

        column_configs = []

        if dataset.columns:
            for col in dataset.columns:
                col_config = ColumnConfig(name=col.name)  # type: ignore[call-arg]

                # Extract drift config from contract customProperties
                if contract.customProperties:
                    for prop in contract.customProperties:
                        # Handle both dict and ODCSCustomProperty object
                        if isinstance(prop, dict):
                            prop_name = prop.get("property", "")
                            prop_value = prop.get("value")
                        else:
                            prop_name = getattr(prop, "property", "")
                            prop_value = getattr(prop, "value", None)

                        # Check for column-specific drift config
                        drift_prop = f"baselinr.drift.{table}.{col.name}"
                        if prop_name == drift_prop or prop_name == f"baselinr.drift.{col.name}":
                            if isinstance(prop_value, dict):
                                col_config.drift = ColumnDriftConfig(
                                    enabled=prop_value.get("enabled", True),
                                    strategy=prop_value.get("strategy"),
                                    thresholds=prop_value.get("thresholds"),
                                    baselines=prop_value.get("baselines"),
                                )
                                break

                # If no explicit config found but column exists, create default enabled config
                if not col_config.drift:
                    col_config.drift = ColumnDriftConfig(enabled=True)  # type: ignore[call-arg]

                column_configs.append(col_config)

        return column_configs

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
