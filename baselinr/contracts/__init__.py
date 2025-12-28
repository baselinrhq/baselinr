"""
ODCS (Open Data Contract Standard) support for Baselinr.

This module provides support for loading, validating, and working with
ODCS v3.1.0 data contracts.
"""

from .adapter import (
    ColumnMetadata,
    DatasetMetadata,
    DriftConfig,
    ODCSAdapter,
    ProfilingTarget,
    SLAConfig,
    ValidationRule,
    convert_contract_to_rules,
    convert_contract_to_targets,
)
from .loader import (
    ContractLoader,
    ContractLoadError,
    load_contract,
    load_contracts,
)
from .odcs_schema import (
    ODCSColumn,
    ODCSContact,
    ODCSContract,
    ODCSDataset,
    ODCSInfo,
    ODCSLink,
    ODCSPrice,
    ODCSQuality,
    ODCSRole,
    ODCSServer,
    ODCSServerEnvironment,
    ODCSServiceLevel,
    ODCSStakeholder,
)
from .validator import (
    ODCSValidationError,
    ODCSValidator,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    validate_contract,
)

__all__ = [
    # Schema models
    "ODCSContract",
    "ODCSInfo",
    "ODCSContact",
    "ODCSServer",
    "ODCSServerEnvironment",
    "ODCSDataset",
    "ODCSColumn",
    "ODCSQuality",
    "ODCSServiceLevel",
    "ODCSStakeholder",
    "ODCSRole",
    "ODCSPrice",
    "ODCSLink",
    # Loader
    "ContractLoader",
    "ContractLoadError",
    "load_contract",
    "load_contracts",
    # Validator
    "ODCSValidator",
    "ODCSValidationError",
    "ValidationResult",
    "ValidationIssue",
    "ValidationSeverity",
    "validate_contract",
    # Adapter
    "ODCSAdapter",
    "ProfilingTarget",
    "ValidationRule",
    "DriftConfig",
    "SLAConfig",
    "ColumnMetadata",
    "DatasetMetadata",
    "convert_contract_to_targets",
    "convert_contract_to_rules",
]
