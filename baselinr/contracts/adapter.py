"""
ODCS to Baselinr Adapter.

Converts ODCS data contracts to internal Baselinr processing formats.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .odcs_schema import (
    ODCSColumn,
    ODCSColumnQuality,
    ODCSContract,
    ODCSDataset,
    ODCSQuality,
    ODCSServiceLevel,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Internal Data Structures
# =============================================================================


@dataclass
class ProfilingTarget:
    """A table/dataset to be profiled."""

    database: Optional[str] = None
    schema: Optional[str] = None
    table: str = ""
    columns: Optional[List[str]] = None
    exclude_columns: Optional[List[str]] = None
    primary_keys: Optional[List[str]] = None
    partition_column: Optional[str] = None

    # Source contract info
    contract_id: Optional[str] = None
    contract_version: Optional[str] = None

    def get_full_name(self) -> str:
        """Get fully qualified table name."""
        parts = []
        if self.database:
            parts.append(self.database)
        if self.schema:
            parts.append(self.schema)
        parts.append(self.table)
        return ".".join(parts)


@dataclass
class ValidationRule:
    """A validation rule to be executed."""

    type: str  # not_null, unique, format, range, enum, referential
    table: str
    column: Optional[str] = None
    severity: str = "error"
    enabled: bool = True

    # Rule-specific parameters
    pattern: Optional[str] = None  # For format rules
    min_value: Optional[float] = None  # For range rules
    max_value: Optional[float] = None  # For range rules
    allowed_values: Optional[List[Any]] = None  # For enum rules
    reference_table: Optional[str] = None  # For referential rules
    reference_column: Optional[str] = None  # For referential rules
    threshold: Optional[float] = None  # For threshold-based rules

    # Metadata
    description: Optional[str] = None
    dimension: Optional[str] = None  # Quality dimension
    contract_id: Optional[str] = None


@dataclass
class DriftConfig:
    """Drift detection configuration for a dataset."""

    table: str
    enabled: bool = True
    columns: Optional[List[str]] = None
    exclude_columns: Optional[List[str]] = None

    # Override thresholds (if specified in contract)
    low_threshold: Optional[float] = None
    medium_threshold: Optional[float] = None
    high_threshold: Optional[float] = None

    contract_id: Optional[str] = None


@dataclass
class SLAConfig:
    """SLA configuration for a dataset."""

    table: str
    freshness_hours: Optional[int] = None
    latency_hours: Optional[int] = None
    availability_percent: Optional[float] = None
    retention_days: Optional[int] = None

    # Raw SLA properties
    properties: List[Dict[str, Any]] = field(default_factory=list)

    contract_id: Optional[str] = None


@dataclass
class ColumnMetadata:
    """Column metadata extracted from ODCS."""

    name: str
    logical_type: Optional[str] = None
    physical_type: Optional[str] = None
    description: Optional[str] = None
    is_primary_key: bool = False
    is_nullable: bool = True
    classification: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # Partition/cluster info
    is_partition_key: bool = False
    is_cluster_key: bool = False


@dataclass
class DatasetMetadata:
    """Dataset metadata extracted from ODCS."""

    name: str
    physical_name: Optional[str] = None
    description: Optional[str] = None
    columns: List[ColumnMetadata] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    # Ownership
    owner: Optional[str] = None
    domain: Optional[str] = None

    contract_id: Optional[str] = None
    contract_version: Optional[str] = None


# =============================================================================
# Adapter Class
# =============================================================================


class ODCSAdapter:
    """
    Converts ODCS contracts to internal Baselinr formats.

    Example:
        >>> adapter = ODCSAdapter()
        >>> targets = adapter.to_profiling_targets(contract)
        >>> rules = adapter.to_validation_rules(contract)
    """

    # Mapping from ODCS quality rules to Baselinr validation types
    QUALITY_RULE_MAPPING: Dict[str, str] = {
        "not_null": "not_null",
        "notnull": "not_null",
        "notNull": "not_null",
        "unique": "unique",
        "format": "format",
        "regex": "format",
        "range": "range",
        "between": "range",
        "enum": "enum",
        "in": "enum",
        "allowed_values": "enum",
        "referential": "referential",
        "foreign_key": "referential",
        "foreignKey": "referential",
    }

    def __init__(self):
        """Initialize the adapter."""
        pass

    def to_profiling_targets(self, contract: ODCSContract) -> List[ProfilingTarget]:
        """
        Extract profiling targets from an ODCS contract.

        Args:
            contract: The ODCS contract

        Returns:
            List of ProfilingTarget objects
        """
        targets: List[ProfilingTarget] = []

        if not contract.dataset:
            return targets

        # Extract server info for database/schema
        database, schema = self._extract_server_info(contract)

        for dataset in contract.dataset:
            target = self._dataset_to_profiling_target(
                dataset,
                database=database,
                schema=schema,
                contract_id=contract.id,
                contract_version=contract.version,
            )
            targets.append(target)

        return targets

    def to_validation_rules(self, contract: ODCSContract) -> List[ValidationRule]:
        """
        Convert ODCS quality rules to Baselinr validation rules.

        Args:
            contract: The ODCS contract

        Returns:
            List of ValidationRule objects
        """
        rules: List[ValidationRule] = []

        # Contract-level quality rules
        if contract.quality:
            for quality in contract.quality:
                rule = self._quality_to_validation_rule(
                    quality,
                    table=self._get_default_table(contract),
                    contract_id=contract.id,
                )
                if rule:
                    rules.append(rule)

        # Dataset-level quality rules
        if contract.dataset:
            for dataset in contract.dataset:
                table_name = dataset.physicalName or dataset.name or ""

                # Dataset-level quality
                if dataset.quality:
                    for quality in dataset.quality:
                        rule = self._quality_to_validation_rule(
                            quality,
                            table=table_name,
                            contract_id=contract.id,
                        )
                        if rule:
                            rules.append(rule)

                # Column-level quality
                if dataset.columns:
                    for column in dataset.columns:
                        if column.quality:
                            for quality_item in column.quality:
                                rule = self._column_quality_to_validation_rule(
                                    quality_item,
                                    table=table_name,
                                    column=column.name,
                                    contract_id=contract.id,
                                )
                                if rule:
                                    rules.append(rule)

                        # Implicit rules from column properties
                        rules.extend(self._implicit_column_rules(column, table_name, contract.id))

        return rules

    def to_drift_configs(self, contract: ODCSContract) -> List[DriftConfig]:
        """
        Extract drift detection configurations from an ODCS contract.

        Args:
            contract: The ODCS contract

        Returns:
            List of DriftConfig objects
        """
        configs: List[DriftConfig] = []

        if not contract.dataset:
            return configs

        for dataset in contract.dataset:
            table_name = dataset.physicalName or dataset.name or ""

            # Get columns to monitor
            columns = None
            if dataset.columns:
                columns = [c.name for c in dataset.columns if c.name]

            config = DriftConfig(
                table=table_name,
                enabled=True,
                columns=columns,
                contract_id=contract.id,
            )
            configs.append(config)

        return configs

    def to_sla_configs(self, contract: ODCSContract) -> List[SLAConfig]:
        """
        Extract SLA configurations from an ODCS contract.

        Args:
            contract: The ODCS contract

        Returns:
            List of SLAConfig objects
        """
        configs: List[SLAConfig] = []

        if not contract.servicelevels:
            return configs

        # Group SLAs by table
        table_slas: Dict[str, List[ODCSServiceLevel]] = {}
        default_table = self._get_default_table(contract)

        for sla in contract.servicelevels:
            table = sla.column.split(".")[0] if sla.column and "." in sla.column else default_table
            if table not in table_slas:
                table_slas[table] = []
            table_slas[table].append(sla)

        # Convert to SLAConfig objects
        for table, slas in table_slas.items():
            config = self._slas_to_config(table, slas, contract.id)
            configs.append(config)

        return configs

    def to_dataset_metadata(self, contract: ODCSContract) -> List[DatasetMetadata]:
        """
        Extract dataset metadata from an ODCS contract.

        Args:
            contract: The ODCS contract

        Returns:
            List of DatasetMetadata objects
        """
        metadata_list: List[DatasetMetadata] = []

        if not contract.dataset:
            return metadata_list

        # Get owner/domain from info
        owner = None
        domain = None
        if contract.info:
            owner = contract.info.owner
            domain = contract.info.domain

        for dataset in contract.dataset:
            columns = []
            if dataset.columns:
                for col in dataset.columns:
                    col_meta = ColumnMetadata(
                        name=col.name,
                        logical_type=col.logicalType,
                        physical_type=col.physicalType,
                        description=col.description,
                        is_primary_key=col.isPrimaryKey or False,
                        is_nullable=col.isNullable if col.isNullable is not None else True,
                        classification=col.classification,
                        tags=col.tags or [],
                        is_partition_key=col.partitionStatus or False,
                        is_cluster_key=col.clusterStatus or False,
                    )
                    columns.append(col_meta)

            metadata = DatasetMetadata(
                name=dataset.name or "",
                physical_name=dataset.physicalName,
                description=dataset.description,
                columns=columns,
                tags=dataset.tags or [],
                owner=owner,
                domain=domain,
                contract_id=contract.id,
                contract_version=contract.version,
            )
            metadata_list.append(metadata)

        return metadata_list

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _extract_server_info(self, contract: ODCSContract) -> Tuple[Optional[str], Optional[str]]:
        """Extract database and schema from server config or legacy fields."""
        database = None
        schema = None

        # Try servers config first
        if contract.servers:
            env = contract.servers.production or contract.servers.development
            if env:
                database = env.database
                schema = env.schema_

        # Fall back to legacy fields
        if not database:
            database = contract.database or contract.datasetProject

        return database, schema

    def _get_default_table(self, contract: ODCSContract) -> str:
        """Get the default table name from contract."""
        if contract.dataset and len(contract.dataset) > 0:
            ds = contract.dataset[0]
            return ds.physicalName or ds.name or ""
        return contract.datasetName or ""

    def _dataset_to_profiling_target(
        self,
        dataset: ODCSDataset,
        database: Optional[str],
        schema: Optional[str],
        contract_id: Optional[str],
        contract_version: Optional[str],
    ) -> ProfilingTarget:
        """Convert ODCSDataset to ProfilingTarget."""
        table_name = dataset.name or ""

        # Extract physical name components if provided
        if dataset.physicalName:
            parts = dataset.physicalName.split(".")
            if len(parts) == 3:
                database = parts[0]
                schema = parts[1]
                table_name = parts[2]
            elif len(parts) == 2:
                schema = parts[0]
                table_name = parts[1]
            else:
                table_name = dataset.physicalName

        # Get column names and primary keys
        columns = None
        primary_keys = None
        partition_column = None

        if dataset.columns:
            columns = [c.name for c in dataset.columns if c.name]
            primary_keys = [c.name for c in dataset.columns if c.name and c.isPrimaryKey]
            partition_cols = [c.name for c in dataset.columns if c.name and c.partitionStatus]
            if partition_cols:
                partition_column = partition_cols[0]

        return ProfilingTarget(
            database=database,
            schema=schema,
            table=table_name,
            columns=columns,
            primary_keys=primary_keys if primary_keys else None,
            partition_column=partition_column,
            contract_id=contract_id,
            contract_version=contract_version,
        )

    def _quality_to_validation_rule(
        self,
        quality: ODCSQuality,
        table: str,
        contract_id: Optional[str],
    ) -> Optional[ValidationRule]:
        """Convert ODCSQuality to ValidationRule."""
        # Determine rule type
        rule_type = self._determine_rule_type(quality)
        if not rule_type:
            logger.debug(f"Could not determine rule type for quality: {quality}")
            return None

        # Get column
        column = None
        if quality.column:
            column = quality.column
        elif quality.specification and quality.specification.column:
            column = quality.specification.column

        rule = ValidationRule(
            type=rule_type,
            table=table,
            column=column,
            severity=quality.severity or "error",
            description=quality.description,
            dimension=quality.dimension,
            contract_id=contract_id,
        )

        # Set rule-specific parameters
        if quality.specification:
            spec = quality.specification
            rule.pattern = spec.pattern
            rule.min_value = spec.minValue
            rule.max_value = spec.maxValue
            rule.allowed_values = spec.values
            rule.reference_table = spec.referenceTable
            rule.reference_column = spec.referenceColumn
            rule.threshold = spec.threshold

        return rule

    def _column_quality_to_validation_rule(
        self,
        quality: ODCSColumnQuality,
        table: str,
        column: str,
        contract_id: Optional[str],
    ) -> Optional[ValidationRule]:
        """Convert column-level quality to ValidationRule."""
        rule_type = quality.rule or quality.type
        if rule_type:
            rule_type = self.QUALITY_RULE_MAPPING.get(rule_type, rule_type)
        else:
            return None

        return ValidationRule(
            type=rule_type,
            table=table,
            column=column,
            severity=quality.severity or "error",
            description=quality.description if hasattr(quality, "description") else None,
            contract_id=contract_id,
        )

    def _implicit_column_rules(
        self,
        column: ODCSColumn,
        table: str,
        contract_id: Optional[str],
    ) -> List[ValidationRule]:
        """Generate implicit validation rules from column properties."""
        rules: List[ValidationRule] = []

        # Not null constraint
        if column.isNullable is False:
            rules.append(
                ValidationRule(
                    type="not_null",
                    table=table,
                    column=column.name,
                    severity="error",
                    description=f"Column {column.name} must not be null",
                    dimension="completeness",
                    contract_id=contract_id,
                )
            )

        # Unique constraint for primary keys
        if column.isPrimaryKey:
            rules.append(
                ValidationRule(
                    type="unique",
                    table=table,
                    column=column.name,
                    severity="error",
                    description=f"Primary key {column.name} must be unique",
                    dimension="uniqueness",
                    contract_id=contract_id,
                )
            )

        # Explicit unique constraint
        if column.isUnique and not column.isPrimaryKey:
            rules.append(
                ValidationRule(
                    type="unique",
                    table=table,
                    column=column.name,
                    severity="error",
                    description=f"Column {column.name} must be unique",
                    dimension="uniqueness",
                    contract_id=contract_id,
                )
            )

        return rules

    def _determine_rule_type(self, quality: ODCSQuality) -> Optional[str]:
        """Determine the validation rule type from ODCSQuality."""
        # Check explicit rule field
        if quality.rule:
            return self.QUALITY_RULE_MAPPING.get(quality.rule, quality.rule)

        # Check specification
        if quality.specification and quality.specification.rule:
            return self.QUALITY_RULE_MAPPING.get(
                quality.specification.rule, quality.specification.rule
            )

        # Infer from type field
        if quality.type:
            return self.QUALITY_RULE_MAPPING.get(quality.type, quality.type)

        # Infer from dimension
        if quality.dimension:
            dimension_mapping = {
                "completeness": "not_null",
                "uniqueness": "unique",
                "validity": "format",
            }
            return dimension_mapping.get(quality.dimension.lower())

        return None

    def _slas_to_config(
        self,
        table: str,
        slas: List[ODCSServiceLevel],
        contract_id: Optional[str],
    ) -> SLAConfig:
        """Convert list of SLAs to SLAConfig."""
        config = SLAConfig(
            table=table,
            contract_id=contract_id,
            properties=[],
        )

        for sla in slas:
            prop = {
                "property": sla.property,
                "value": sla.value,
                "unit": sla.unit,
            }
            config.properties.append(prop)

            # Extract specific SLA types
            prop_lower = sla.property.lower()

            if prop_lower in ("freshness", "timeliness"):
                config.freshness_hours = self._to_hours(sla.value, sla.unit)
            elif prop_lower == "latency":
                config.latency_hours = self._to_hours(sla.value, sla.unit)
            elif prop_lower in ("availability", "uptime"):
                config.availability_percent = float(sla.value)
            elif prop_lower == "retention":
                config.retention_days = self._to_days(sla.value, sla.unit)

        return config

    def _to_hours(self, value: Any, unit: Optional[str]) -> Optional[int]:
        """Convert a time value to hours."""
        try:
            val = float(value)
        except (TypeError, ValueError):
            return None

        if not unit:
            return int(val)

        unit_lower = unit.lower()
        if unit_lower in ("h", "hour", "hours"):
            return int(val)
        elif unit_lower in ("d", "day", "days"):
            return int(val * 24)
        elif unit_lower in ("m", "min", "minute", "minutes"):
            return int(val / 60)
        elif unit_lower in ("s", "sec", "second", "seconds"):
            return int(val / 3600)

        return int(val)

    def _to_days(self, value: Any, unit: Optional[str]) -> Optional[int]:
        """Convert a time value to days."""
        try:
            val = float(value)
        except (TypeError, ValueError):
            return None

        if not unit:
            return int(val)

        unit_lower = unit.lower()
        if unit_lower in ("d", "day", "days"):
            return int(val)
        elif unit_lower in ("y", "yr", "year", "years"):
            return int(val * 365)
        elif unit_lower in ("m", "mo", "month", "months"):
            return int(val * 30)
        elif unit_lower in ("w", "wk", "week", "weeks"):
            return int(val * 7)

        return int(val)


# =============================================================================
# Convenience Functions
# =============================================================================


def convert_contract_to_targets(contract: ODCSContract) -> List[ProfilingTarget]:
    """
    Convenience function to convert contract to profiling targets.

    Args:
        contract: The ODCS contract

    Returns:
        List of ProfilingTarget objects
    """
    adapter = ODCSAdapter()
    return adapter.to_profiling_targets(contract)


def convert_contract_to_rules(contract: ODCSContract) -> List[ValidationRule]:
    """
    Convenience function to convert contract to validation rules.

    Args:
        contract: The ODCS contract

    Returns:
        List of ValidationRule objects
    """
    adapter = ODCSAdapter()
    return adapter.to_validation_rules(contract)
