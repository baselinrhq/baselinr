"""
ODCS Contract Validator.

Validates ODCS data contracts against the v3.1.0 specification.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional, Set

from .odcs_schema import ODCSColumn, ODCSContract, ODCSDataset, ODCSQuality

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Severity level for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A single validation issue."""

    message: str
    severity: ValidationSeverity
    path: str = ""
    code: Optional[str] = None

    def __str__(self) -> str:
        prefix = f"[{self.severity.value.upper()}]"
        path_str = f" at '{self.path}'" if self.path else ""
        return f"{prefix}{path_str}: {self.message}"


@dataclass
class ValidationResult:
    """Result of contract validation."""

    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[ValidationIssue]:
        """Get only error-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        """Get only warning-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    def __str__(self) -> str:
        if self.valid:
            return "Validation passed"
        error_count = len(self.errors)
        warning_count = len(self.warnings)
        return f"Validation failed: {error_count} error(s), {warning_count} warning(s)"


class ODCSValidationError(Exception):
    """Exception raised when contract validation fails."""

    def __init__(self, message: str, errors: Optional[List[ValidationIssue]] = None):
        self.errors = errors or []
        error_details = "\n".join(str(e) for e in self.errors)
        full_message = f"{message}\n{error_details}" if error_details else message
        super().__init__(full_message)


class ODCSValidator:
    """
    Validates ODCS contracts against the v3.1.0 specification.

    Example:
        >>> validator = ODCSValidator()
        >>> result = validator.validate_full(contract)
        >>> if not result.valid:
        ...     for issue in result.issues:
        ...         print(issue)
    """

    # Valid logical types
    VALID_LOGICAL_TYPES: Set[str] = {
        "string",
        "text",
        "integer",
        "bigint",
        "smallint",
        "tinyint",
        "float",
        "double",
        "decimal",
        "numeric",
        "boolean",
        "date",
        "time",
        "timestamp",
        "timestamptz",
        "binary",
        "array",
        "map",
        "struct",
        "json",
        "uuid",
        "geography",
        "geometry",
        "variant",
        "object",
    }

    # Valid quality dimensions
    VALID_QUALITY_DIMENSIONS: Set[str] = {
        "completeness",
        "accuracy",
        "validity",
        "uniqueness",
        "consistency",
        "timeliness",
        "integrity",
    }

    # Valid severity levels
    VALID_SEVERITIES: Set[str] = {"info", "warning", "error", "critical"}

    # Valid classification levels
    VALID_CLASSIFICATIONS: Set[str] = {
        "public",
        "internal",
        "confidential",
        "restricted",
        "pii",
        "phi",
        "pci",
    }

    # Valid contract statuses
    VALID_STATUSES: Set[str] = {"draft", "active", "deprecated", "retired", "current"}

    def __init__(self, strict: bool = False):
        """
        Initialize the validator.

        Args:
            strict: If True, treat warnings as errors
        """
        self.strict = strict

    def validate(self, contract: ODCSContract) -> List[ValidationIssue]:
        """
        Validate a contract and return list of issues (errors only).

        Args:
            contract: The contract to validate

        Returns:
            List of validation issues (errors only for backward compatibility)
        """
        result = self.validate_full(contract)
        return result.errors

    def validate_full(self, contract: ODCSContract) -> ValidationResult:
        """
        Perform full validation of a contract.

        Args:
            contract: The contract to validate

        Returns:
            ValidationResult with all issues
        """
        issues: List[ValidationIssue] = []

        # Validate required fields
        issues.extend(self._validate_required_fields(contract))

        # Validate kind and apiVersion
        issues.extend(self._validate_kind_and_version(contract))

        # Validate info section
        if contract.info:
            issues.extend(self._validate_info(contract.info))

        # Validate datasets
        if contract.dataset:
            issues.extend(self._validate_datasets(contract.dataset))
        else:
            issues.append(
                ValidationIssue(
                    message="Contract has no datasets defined",
                    severity=ValidationSeverity.WARNING,
                    path="dataset",
                    code="NO_DATASETS",
                )
            )

        # Validate quality rules
        if contract.quality:
            issues.extend(self._validate_quality_rules(contract.quality, "quality"))

        # Validate service levels
        if contract.servicelevels:
            issues.extend(self._validate_service_levels(contract.servicelevels))

        # Validate stakeholders
        if contract.stakeholders:
            issues.extend(self._validate_stakeholders(contract.stakeholders))

        # Validate roles
        if contract.roles:
            issues.extend(self._validate_roles(contract.roles))

        # Validate servers
        if contract.servers:
            issues.extend(self._validate_servers(contract.servers))

        # Determine overall validity
        has_errors = any(i.severity == ValidationSeverity.ERROR for i in issues)
        has_warnings = any(i.severity == ValidationSeverity.WARNING for i in issues)

        valid = not has_errors
        if self.strict and has_warnings:
            valid = False

        return ValidationResult(valid=valid, issues=issues)

    def _validate_required_fields(self, contract: ODCSContract) -> List[ValidationIssue]:
        """Validate required top-level fields."""
        issues: List[ValidationIssue] = []

        if not contract.kind:
            issues.append(
                ValidationIssue(
                    message="Missing required field 'kind'",
                    severity=ValidationSeverity.ERROR,
                    path="kind",
                    code="MISSING_KIND",
                )
            )

        if not contract.apiVersion:
            issues.append(
                ValidationIssue(
                    message="Missing required field 'apiVersion'",
                    severity=ValidationSeverity.ERROR,
                    path="apiVersion",
                    code="MISSING_API_VERSION",
                )
            )

        # ID or uuid recommended
        if not contract.id and not contract.uuid:
            issues.append(
                ValidationIssue(
                    message="Contract should have an 'id' or 'uuid' for identification",
                    severity=ValidationSeverity.WARNING,
                    path="id",
                    code="MISSING_ID",
                )
            )

        return issues

    def _validate_kind_and_version(self, contract: ODCSContract) -> List[ValidationIssue]:
        """Validate kind and apiVersion values."""
        issues: List[ValidationIssue] = []

        if contract.kind and contract.kind != "DataContract":
            issues.append(
                ValidationIssue(
                    message=f"Invalid kind '{contract.kind}', must be 'DataContract'",
                    severity=ValidationSeverity.ERROR,
                    path="kind",
                    code="INVALID_KIND",
                )
            )

        if contract.apiVersion:
            # Check version format (v2.x.x or v3.x.x)
            version_pattern = r"^v\d+\.\d+(\.\d+)?$"
            if not re.match(version_pattern, contract.apiVersion):
                issues.append(
                    ValidationIssue(
                        message=f"Invalid apiVersion format '{contract.apiVersion}'",
                        severity=ValidationSeverity.WARNING,
                        path="apiVersion",
                        code="INVALID_VERSION_FORMAT",
                    )
                )

        if contract.status:
            if contract.status.lower() not in self.VALID_STATUSES:
                issues.append(
                    ValidationIssue(
                        message=(
                            f"Invalid status '{contract.status}', "
                            f"must be one of {self.VALID_STATUSES}"
                        ),
                        severity=ValidationSeverity.ERROR,
                        path="status",
                        code="INVALID_STATUS",
                    )
                )

        return issues

    def _validate_info(self, info: Any) -> List[ValidationIssue]:
        """Validate the info section."""
        issues: List[ValidationIssue] = []

        if not info.title:
            issues.append(
                ValidationIssue(
                    message="info.title is recommended for contract identification",
                    severity=ValidationSeverity.WARNING,
                    path="info.title",
                    code="MISSING_TITLE",
                )
            )

        if info.owner:
            # Check if owner looks like an email
            if "@" in info.owner and not re.match(r"[^@]+@[^@]+\.[^@]+", info.owner):
                issues.append(
                    ValidationIssue(
                        message=f"info.owner appears to be an invalid email: '{info.owner}'",
                        severity=ValidationSeverity.WARNING,
                        path="info.owner",
                        code="INVALID_OWNER_EMAIL",
                    )
                )

        return issues

    def _validate_datasets(self, datasets: List[ODCSDataset]) -> List[ValidationIssue]:
        """Validate dataset definitions."""
        issues: List[ValidationIssue] = []
        seen_names: Set[str] = set()

        for idx, dataset in enumerate(datasets):
            path = f"dataset[{idx}]"

            # Check for name
            if not dataset.name:
                issues.append(
                    ValidationIssue(
                        message="Dataset must have a 'name' or 'table'",
                        severity=ValidationSeverity.ERROR,
                        path=path,
                        code="MISSING_DATASET_NAME",
                    )
                )
                continue

            # Check for duplicate names
            if dataset.name in seen_names:
                issues.append(
                    ValidationIssue(
                        message=f"Duplicate dataset name '{dataset.name}'",
                        severity=ValidationSeverity.ERROR,
                        path=f"{path}.name",
                        code="DUPLICATE_DATASET",
                    )
                )
            seen_names.add(dataset.name)

            # Validate columns
            if dataset.columns:
                issues.extend(self._validate_columns(dataset.columns, f"{path}.columns"))
            else:
                issues.append(
                    ValidationIssue(
                        message=f"Dataset '{dataset.name}' has no columns defined",
                        severity=ValidationSeverity.WARNING,
                        path=f"{path}.columns",
                        code="NO_COLUMNS",
                    )
                )

            # Validate dataset-level quality rules
            if dataset.quality:
                issues.extend(self._validate_quality_rules(dataset.quality, f"{path}.quality"))

        return issues

    def _validate_columns(self, columns: List[ODCSColumn], path: str) -> List[ValidationIssue]:
        """Validate column definitions."""
        issues: List[ValidationIssue] = []
        seen_names: Set[str] = set()
        pk_count = 0

        for idx, column in enumerate(columns):
            col_path = f"{path}[{idx}]"

            # Check for name
            if not column.name:
                issues.append(
                    ValidationIssue(
                        message="Column must have a 'name' or 'column'",
                        severity=ValidationSeverity.ERROR,
                        path=col_path,
                        code="MISSING_COLUMN_NAME",
                    )
                )
                continue

            # Check for duplicate names
            if column.name in seen_names:
                issues.append(
                    ValidationIssue(
                        message=f"Duplicate column name '{column.name}'",
                        severity=ValidationSeverity.ERROR,
                        path=f"{col_path}.name",
                        code="DUPLICATE_COLUMN",
                    )
                )
            seen_names.add(column.name)

            # Validate logical type
            if column.logicalType:
                if column.logicalType.lower() not in self.VALID_LOGICAL_TYPES:
                    issues.append(
                        ValidationIssue(
                            message=(
                                f"Unknown logical type '{column.logicalType}' "
                                f"for column '{column.name}'"
                            ),
                            severity=ValidationSeverity.WARNING,
                            path=f"{col_path}.logicalType",
                            code="UNKNOWN_LOGICAL_TYPE",
                        )
                    )

            # Validate classification
            if column.classification:
                if column.classification.lower() not in self.VALID_CLASSIFICATIONS:
                    issues.append(
                        ValidationIssue(
                            message=(
                                f"Unknown classification '{column.classification}' "
                                f"for column '{column.name}'"
                            ),
                            severity=ValidationSeverity.WARNING,
                            path=f"{col_path}.classification",
                            code="UNKNOWN_CLASSIFICATION",
                        )
                    )

            # Track primary keys
            if column.isPrimaryKey:
                pk_count += 1

            # Validate column-level quality
            if column.quality:
                for q_idx, quality in enumerate(column.quality):
                    q_path = f"{col_path}.quality[{q_idx}]"
                    if quality.severity and quality.severity.lower() not in self.VALID_SEVERITIES:
                        issues.append(
                            ValidationIssue(
                                message=f"Invalid severity '{quality.severity}'",
                                severity=ValidationSeverity.WARNING,
                                path=f"{q_path}.severity",
                                code="INVALID_SEVERITY",
                            )
                        )

        return issues

    def _validate_quality_rules(self, rules: List[ODCSQuality], path: str) -> List[ValidationIssue]:
        """Validate quality rule definitions."""
        issues: List[ValidationIssue] = []

        for idx, rule in enumerate(rules):
            rule_path = f"{path}[{idx}]"

            # Validate dimension
            if rule.dimension:
                if rule.dimension.lower() not in self.VALID_QUALITY_DIMENSIONS:
                    issues.append(
                        ValidationIssue(
                            message=f"Unknown quality dimension '{rule.dimension}'",
                            severity=ValidationSeverity.WARNING,
                            path=f"{rule_path}.dimension",
                            code="UNKNOWN_DIMENSION",
                        )
                    )

            # Validate severity
            if rule.severity:
                if rule.severity.lower() not in self.VALID_SEVERITIES:
                    issues.append(
                        ValidationIssue(
                            message=f"Invalid severity '{rule.severity}'",
                            severity=ValidationSeverity.WARNING,
                            path=f"{rule_path}.severity",
                            code="INVALID_SEVERITY",
                        )
                    )

            # Check for rule specification
            if not rule.specification and not rule.rule and not rule.column:
                issues.append(
                    ValidationIssue(
                        message=(
                            "Quality rule should have 'specification', "
                            "'rule', or 'column' defined"
                        ),
                        severity=ValidationSeverity.WARNING,
                        path=rule_path,
                        code="INCOMPLETE_QUALITY_RULE",
                    )
                )

        return issues

    def _validate_service_levels(self, slas: List[Any]) -> List[ValidationIssue]:
        """Validate service level definitions."""
        issues: List[ValidationIssue] = []

        for idx, sla in enumerate(slas):
            path = f"servicelevels[{idx}]"

            if not sla.property:
                issues.append(
                    ValidationIssue(
                        message="Service level must have a 'property'",
                        severity=ValidationSeverity.ERROR,
                        path=path,
                        code="MISSING_SLA_PROPERTY",
                    )
                )

            if sla.value is None:
                issues.append(
                    ValidationIssue(
                        message="Service level must have a 'value'",
                        severity=ValidationSeverity.ERROR,
                        path=path,
                        code="MISSING_SLA_VALUE",
                    )
                )

        return issues

    def _validate_stakeholders(self, stakeholders: List[Any]) -> List[ValidationIssue]:
        """Validate stakeholder definitions."""
        issues: List[ValidationIssue] = []

        for idx, stakeholder in enumerate(stakeholders):
            path = f"stakeholders[{idx}]"

            if not stakeholder.username and not stakeholder.name and not stakeholder.email:
                issues.append(
                    ValidationIssue(
                        message="Stakeholder should have 'username', 'name', or 'email'",
                        severity=ValidationSeverity.WARNING,
                        path=path,
                        code="INCOMPLETE_STAKEHOLDER",
                    )
                )

        return issues

    def _validate_roles(self, roles: List[Any]) -> List[ValidationIssue]:
        """Validate role definitions."""
        issues: List[ValidationIssue] = []

        for idx, role in enumerate(roles):
            path = f"roles[{idx}]"

            if not role.role:
                issues.append(
                    ValidationIssue(
                        message="Role must have a 'role' name",
                        severity=ValidationSeverity.ERROR,
                        path=path,
                        code="MISSING_ROLE_NAME",
                    )
                )

        return issues

    def _validate_servers(self, servers: Any) -> List[ValidationIssue]:
        """Validate server configurations."""
        issues: List[ValidationIssue] = []

        # Check that at least one environment is configured
        has_env = any(
            [
                servers.production,
                servers.development,
                servers.staging,
                servers.test,
            ]
        )

        if not has_env:
            issues.append(
                ValidationIssue(
                    message="servers should have at least one environment configured",
                    severity=ValidationSeverity.WARNING,
                    path="servers",
                    code="NO_SERVER_ENVIRONMENTS",
                )
            )

        return issues


def validate_contract(contract: ODCSContract, strict: bool = False) -> ValidationResult:
    """
    Convenience function to validate a contract.

    Args:
        contract: The contract to validate
        strict: If True, treat warnings as errors

    Returns:
        ValidationResult
    """
    validator = ODCSValidator(strict=strict)
    return validator.validate_full(contract)
