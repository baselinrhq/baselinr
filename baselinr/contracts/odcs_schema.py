"""
ODCS (Open Data Contract Standard) v3.1.0 Schema Models.

This module provides Pydantic models for the Open Data Contract Standard v3.1.0.
These models are used to load, validate, and work with ODCS data contracts.

Reference: https://bitol-io.github.io/open-data-contract-standard/
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

# =============================================================================
# Enums
# =============================================================================


class ODCSKind(str, Enum):
    """Kind of ODCS document."""

    DATA_CONTRACT = "DataContract"


class ODCSStatus(str, Enum):
    """Status of a data contract."""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class ODCSDatasetType(str, Enum):
    """Type of dataset."""

    TABLE = "table"
    VIEW = "view"
    MATERIALIZED_VIEW = "materializedView"
    STREAM = "stream"
    OBJECT = "object"
    FILE = "file"
    TOPIC = "topic"


class ODCSLogicalType(str, Enum):
    """Logical data types for columns."""

    STRING = "string"
    TEXT = "text"
    INTEGER = "integer"
    BIGINT = "bigint"
    SMALLINT = "smallint"
    TINYINT = "tinyint"
    FLOAT = "float"
    DOUBLE = "double"
    DECIMAL = "decimal"
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    DATE = "date"
    TIME = "time"
    TIMESTAMP = "timestamp"
    TIMESTAMP_TZ = "timestamptz"
    BINARY = "binary"
    ARRAY = "array"
    MAP = "map"
    STRUCT = "struct"
    JSON = "json"
    UUID = "uuid"
    GEOGRAPHY = "geography"
    GEOMETRY = "geometry"
    VARIANT = "variant"
    OBJECT = "object"


class ODCSClassification(str, Enum):
    """Data classification levels."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    PII = "pii"
    PHI = "phi"
    PCI = "pci"


class ODCSQualityDimension(str, Enum):
    """Data quality dimensions."""

    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    VALIDITY = "validity"
    UNIQUENESS = "uniqueness"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    INTEGRITY = "integrity"


class ODCSQualitySeverity(str, Enum):
    """Severity level for quality rules."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ODCSServerType(str, Enum):
    """Database/server types."""

    POSTGRES = "postgres"
    POSTGRESQL = "postgresql"
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    REDSHIFT = "redshift"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    DATABRICKS = "databricks"
    SPARK = "spark"
    KAFKA = "kafka"
    S3 = "s3"
    GCS = "gcs"
    AZURE_BLOB = "azureBlob"
    JDBC = "jdbc"
    CUSTOM = "custom"


# =============================================================================
# Supporting Models
# =============================================================================


class ODCSLink(BaseModel):
    """External link reference."""

    url: str = Field(..., description="URL of the link")
    type: Optional[str] = Field(
        None,
        description="Type of link (e.g., 'documentation', 'repository', 'wiki')",
    )
    title: Optional[str] = Field(None, description="Human-readable title")

    model_config = {"extra": "allow"}


class ODCSContact(BaseModel):
    """Contact information."""

    name: Optional[str] = Field(None, description="Contact name")
    email: Optional[str] = Field(None, description="Contact email")
    url: Optional[str] = Field(None, description="Contact URL or profile")
    role: Optional[str] = Field(None, description="Role of the contact")

    model_config = {"extra": "allow"}


class ODCSInfo(BaseModel):
    """Contract information/metadata."""

    title: str = Field(..., description="Human-readable title of the data contract")
    description: Optional[str] = Field(
        None, description="Detailed description of the data contract"
    )
    version: Optional[str] = Field(
        None, description="Version of the data contract (semantic versioning)"
    )
    owner: Optional[str] = Field(
        None, description="Owner of the data contract (email or team name)"
    )
    domain: Optional[str] = Field(None, description="Business domain")
    dataProduct: Optional[str] = Field(None, description="Data product name")
    tenant: Optional[str] = Field(None, description="Tenant identifier")
    contact: Optional[ODCSContact] = Field(None, description="Primary contact")
    links: Optional[List[ODCSLink]] = Field(None, description="Related links")

    model_config = {"extra": "allow", "populate_by_name": True}


class ODCSServerEnvironment(BaseModel):
    """Server/connection configuration for an environment."""

    type: Optional[str] = Field(None, description="Server/database type")
    host: Optional[str] = Field(None, description="Server hostname")
    port: Optional[int] = Field(None, description="Server port")
    account: Optional[str] = Field(None, description="Account identifier (Snowflake)")
    database: Optional[str] = Field(None, description="Database name")
    schema_: Optional[str] = Field(None, alias="schema", description="Schema name")
    catalog: Optional[str] = Field(None, description="Catalog name (Databricks/Spark)")
    driver: Optional[str] = Field(None, description="JDBC driver")
    warehouse: Optional[str] = Field(None, description="Warehouse name (Snowflake)")
    project: Optional[str] = Field(None, description="Project ID (BigQuery)")
    dataset: Optional[str] = Field(None, description="Dataset name (BigQuery)")
    location: Optional[str] = Field(None, description="Location/region")
    bucket: Optional[str] = Field(None, description="Bucket name (S3/GCS)")
    path: Optional[str] = Field(None, description="Path within bucket or filesystem")
    url: Optional[str] = Field(None, description="Connection URL")

    model_config = {"extra": "allow", "populate_by_name": True}


class ODCSServer(BaseModel):
    """Server configurations for different environments."""

    production: Optional[ODCSServerEnvironment] = Field(None, description="Production environment")
    development: Optional[ODCSServerEnvironment] = Field(
        None, description="Development environment"
    )
    staging: Optional[ODCSServerEnvironment] = Field(None, description="Staging environment")
    test: Optional[ODCSServerEnvironment] = Field(None, description="Test environment")

    model_config = {"extra": "allow"}


class ODCSQualitySpecification(BaseModel):
    """Specification for a quality rule."""

    column: Optional[str] = Field(None, description="Column this rule applies to")
    columns: Optional[List[str]] = Field(None, description="Multiple columns this rule applies to")
    rule: Optional[str] = Field(
        None,
        description="Rule type (not_null, unique, format, range, enum, referential)",
    )
    pattern: Optional[str] = Field(None, description="Regex pattern for format rules")
    minValue: Optional[Union[int, float]] = Field(None, description="Minimum value for range rules")
    maxValue: Optional[Union[int, float]] = Field(None, description="Maximum value for range rules")
    values: Optional[List[Any]] = Field(None, description="Allowed values for enum rules")
    referenceTable: Optional[str] = Field(None, description="Reference table for referential rules")
    referenceColumn: Optional[str] = Field(
        None, description="Reference column for referential rules"
    )
    threshold: Optional[float] = Field(None, description="Threshold value (e.g., null percentage)")
    query: Optional[str] = Field(None, description="Custom SQL query for validation")
    expression: Optional[str] = Field(None, description="Expression for custom validation")

    model_config = {"extra": "allow", "populate_by_name": True}


class ODCSQuality(BaseModel):
    """Data quality rule definition."""

    type: Optional[str] = Field(None, description="Quality check type")
    code: Optional[str] = Field(None, description="Unique code for the quality rule")
    name: Optional[str] = Field(None, description="Human-readable name")
    description: Optional[str] = Field(None, description="Description of the rule")
    dimension: Optional[str] = Field(
        None,
        description="Quality dimension (completeness, accuracy, validity, etc.)",
    )
    severity: Optional[str] = Field(
        "error", description="Severity level (info, warning, error, critical)"
    )
    specification: Optional[ODCSQualitySpecification] = Field(
        None, description="Rule specification"
    )
    column: Optional[str] = Field(None, description="Column this rule applies to (shorthand)")
    rule: Optional[str] = Field(None, description="Rule type (shorthand)")

    # Tool-specific fields
    toolName: Optional[str] = Field(None, description="Tool name for execution")
    toolRuleName: Optional[str] = Field(None, description="Rule name in the tool")
    scheduleCronExpression: Optional[str] = Field(
        None, description="Cron expression for scheduling"
    )
    businessImpact: Optional[str] = Field(None, description="Business impact description")
    customProperties: Optional[List[Dict[str, Any]]] = Field(None, description="Custom properties")

    model_config = {"extra": "allow", "populate_by_name": True}


class ODCSColumnQuality(BaseModel):
    """Column-level quality rule (simplified)."""

    type: Optional[str] = Field(None, description="Quality check type")
    rule: Optional[str] = Field(None, description="Rule type")
    severity: Optional[str] = Field("error", description="Severity level")
    description: Optional[str] = Field(None, description="Description")

    model_config = {"extra": "allow"}


class ODCSColumn(BaseModel):
    """Column definition within a dataset."""

    name: str = Field(..., alias="column", description="Column name")
    businessName: Optional[str] = Field(None, description="Business-friendly column name")
    logicalType: Optional[str] = Field(None, description="Logical data type")
    physicalType: Optional[str] = Field(None, description="Physical data type")
    description: Optional[str] = Field(None, description="Column description")
    isPrimaryKey: Optional[bool] = Field(False, description="Whether this is a primary key")
    primaryKeyPosition: Optional[int] = Field(None, description="Position in composite primary key")
    isNullable: Optional[bool] = Field(True, description="Whether column allows nulls")
    isUnique: Optional[bool] = Field(False, description="Whether values must be unique")
    classification: Optional[str] = Field(
        None, description="Data classification (public, pii, etc.)"
    )
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")

    # Partitioning/clustering
    partitionStatus: Optional[bool] = Field(False, description="Whether this is a partition column")
    partitionKeyPosition: Optional[int] = Field(None, description="Position in partition key")
    clusterStatus: Optional[bool] = Field(False, description="Whether this is a cluster column")
    clusterKeyPosition: Optional[int] = Field(None, description="Position in cluster key")

    # Data lineage
    transformSourceTables: Optional[List[str]] = Field(
        None, description="Source tables for this column"
    )
    transformLogic: Optional[str] = Field(None, description="Transformation logic/SQL")
    transformDescription: Optional[str] = Field(
        None, description="Business description of transformation"
    )

    # Examples and validation
    sampleValues: Optional[List[Any]] = Field(None, description="Sample values")
    defaultValue: Optional[Any] = Field(None, description="Default value")

    # Column-level quality rules
    quality: Optional[List[ODCSColumnQuality]] = Field(
        None, description="Column-level quality rules"
    )

    # Critical data element flag
    criticalDataElementStatus: Optional[bool] = Field(
        False, description="Whether this is a critical data element"
    )

    # Encryption
    encryptedColumnName: Optional[str] = Field(
        None, description="Name of encrypted version of this column"
    )

    # Links to authoritative definitions
    authoritativeDefinitions: Optional[List[ODCSLink]] = Field(
        None, description="Links to authoritative definitions"
    )

    model_config = {"extra": "allow", "populate_by_name": True}

    @model_validator(mode="before")
    @classmethod
    def normalize_column_name(cls, data: Any) -> Any:
        """Normalize column field to name."""
        if isinstance(data, dict):
            # Support both 'column' and 'name' fields
            if "column" in data and "name" not in data:
                data["name"] = data["column"]
        return data


class ODCSDataset(BaseModel):
    """Dataset (table/view) definition."""

    name: Optional[str] = Field(None, alias="table", description="Logical dataset/table name")
    physicalName: Optional[str] = Field(None, description="Physical name (schema.table)")
    description: Optional[str] = Field(None, description="Dataset description")
    type: Optional[str] = Field("table", description="Dataset type (table, view, etc.)")

    # Schema information
    columns: Optional[List[ODCSColumn]] = Field(None, description="Column definitions")

    # Granularity
    dataGranularity: Optional[str] = Field(None, description="Description of data granularity")

    # Quality rules at dataset level
    quality: Optional[List[ODCSQuality]] = Field(None, description="Dataset-level quality rules")

    # Tags
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")

    # Prior table name (for migrations)
    priorTableName: Optional[str] = Field(
        None, description="Previous table name (for tracking renames)"
    )

    # Authoritative definitions
    authoritativeDefinitions: Optional[List[ODCSLink]] = Field(
        None, description="Links to authoritative definitions"
    )

    model_config = {"extra": "allow", "populate_by_name": True}

    @model_validator(mode="before")
    @classmethod
    def normalize_table_name(cls, data: Any) -> Any:
        """Normalize table field to name."""
        if isinstance(data, dict):
            # Support both 'table' and 'name' fields
            if "table" in data and "name" not in data:
                data["name"] = data["table"]
        return data


class ODCSServiceLevel(BaseModel):
    """Service level agreement property."""

    property: str = Field(..., description="SLA property name")
    value: Union[int, float, str] = Field(..., description="SLA value")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    column: Optional[str] = Field(None, description="Column this SLA applies to")
    description: Optional[str] = Field(None, description="Description of the SLA")
    driver: Optional[str] = Field(None, description="Driver/reason (regulatory, analytics, etc.)")

    model_config = {"extra": "allow"}


class ODCSStakeholder(BaseModel):
    """Stakeholder information."""

    username: Optional[str] = Field(None, description="Username or email")
    name: Optional[str] = Field(None, description="Full name")
    role: Optional[str] = Field(None, description="Role/title")
    email: Optional[str] = Field(None, description="Email address")
    dateIn: Optional[str] = Field(None, description="Start date")
    dateOut: Optional[str] = Field(None, description="End date")
    replacedByUsername: Optional[str] = Field(None, description="Username of replacement")
    comment: Optional[str] = Field(None, description="Additional comments")

    model_config = {"extra": "allow"}


class ODCSRole(BaseModel):
    """Access role definition."""

    role: str = Field(..., description="Role name")
    access: Optional[str] = Field(None, description="Access level (read, write, admin)")
    description: Optional[str] = Field(None, description="Role description")
    firstLevelApprovers: Optional[str] = Field(None, description="First level approvers")
    secondLevelApprovers: Optional[str] = Field(None, description="Second level approvers")

    model_config = {"extra": "allow"}


class ODCSPrice(BaseModel):
    """Pricing information."""

    priceAmount: Optional[float] = Field(None, description="Price amount")
    priceCurrency: Optional[str] = Field(None, description="Currency code (USD, EUR)")
    priceUnit: Optional[str] = Field(None, description="Unit of pricing (query, row, GB)")
    description: Optional[str] = Field(None, description="Pricing description")

    model_config = {"extra": "allow"}


class ODCSCustomProperty(BaseModel):
    """Custom property key-value pair."""

    property: str = Field(..., description="Property name")
    value: Any = Field(..., description="Property value")

    model_config = {"extra": "allow"}


# =============================================================================
# Main Contract Model
# =============================================================================


class ODCSContract(BaseModel):
    """
    ODCS (Open Data Contract Standard) v3.1.0 Contract.

    This is the top-level model for an ODCS data contract.

    Example:
        >>> contract = ODCSContract(
        ...     kind="DataContract",
        ...     apiVersion="v3.1.0",
        ...     id="customers-contract",
        ...     info=ODCSInfo(title="Customers Dataset"),
        ...     dataset=[ODCSDataset(name="customers")]
        ... )
    """

    # Required fields
    kind: str = Field(
        "DataContract",
        description="Kind of document (must be 'DataContract')",
    )
    apiVersion: str = Field(
        "v3.1.0",
        description="ODCS version (e.g., 'v3.1.0')",
    )

    # Identity
    id: Optional[str] = Field(None, description="Unique identifier for this contract")
    uuid: Optional[str] = Field(None, description="UUID for this contract")
    version: Optional[str] = Field(None, description="Contract version (semantic versioning)")
    status: Optional[str] = Field(
        "active", description="Contract status (draft, active, deprecated, retired)"
    )

    # Metadata
    info: Optional[ODCSInfo] = Field(None, description="Contract information")

    # Legacy fields (v2.x compatibility)
    datasetDomain: Optional[str] = Field(None, description="Domain (legacy)")
    quantumName: Optional[str] = Field(None, description="Data product name (legacy)")
    userConsumptionMode: Optional[str] = Field(None, description="Consumption mode (legacy)")
    tenant: Optional[str] = Field(None, description="Tenant (legacy)")

    # Description (legacy - prefer info.description)
    description: Optional[Dict[str, str]] = Field(None, description="Description object (legacy)")

    # Support channels
    productDl: Optional[str] = Field(None, description="Product distribution list")
    productSlackChannel: Optional[str] = Field(None, description="Slack channel")
    productFeedbackUrl: Optional[str] = Field(None, description="Feedback URL")

    # Source system info
    sourcePlatform: Optional[str] = Field(None, description="Source platform")
    sourceSystem: Optional[str] = Field(None, description="Source system")
    datasetProject: Optional[str] = Field(None, description="Dataset project")
    datasetName: Optional[str] = Field(None, description="Dataset name")

    # Type
    type: Optional[str] = Field(None, description="Contract type (tables, objects, etc.)")

    # Server/connection configuration
    servers: Optional[ODCSServer] = Field(None, description="Server configurations by environment")

    # Legacy connection fields (v2.x)
    driver: Optional[str] = Field(None, description="JDBC driver (legacy)")
    driverVersion: Optional[str] = Field(None, description="Driver version (legacy)")
    server: Optional[str] = Field(None, description="Server host:port (legacy)")
    database: Optional[str] = Field(None, description="Database name (legacy)")
    username: Optional[str] = Field(None, description="Username template (legacy)")
    password: Optional[str] = Field(None, description="Password template (legacy)")
    schedulerAppName: Optional[str] = Field(None, description="Scheduler app name (legacy)")

    # Dataset definitions
    dataset: Optional[List[ODCSDataset]] = Field(
        None, description="Dataset (table/view) definitions"
    )

    # Quality rules (contract-level)
    quality: Optional[List[ODCSQuality]] = Field(None, description="Contract-level quality rules")

    # Service level agreements
    servicelevels: Optional[List[ODCSServiceLevel]] = Field(
        None, alias="slaProperties", description="Service level agreements"
    )
    slaDefaultColumn: Optional[str] = Field(None, description="Default column for SLAs")

    # Stakeholders
    stakeholders: Optional[List[ODCSStakeholder]] = Field(None, description="Stakeholders")

    # Access roles
    roles: Optional[List[ODCSRole]] = Field(None, description="Access roles")

    # Pricing
    price: Optional[ODCSPrice] = Field(None, description="Pricing information")

    # Tags
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")

    # Custom properties
    customProperties: Optional[List[ODCSCustomProperty]] = Field(
        None, description="Custom properties"
    )

    # Timestamps
    contractCreatedTs: Optional[str] = Field(None, description="Contract creation timestamp")
    systemInstance: Optional[str] = Field(None, description="System instance")

    model_config = {"extra": "allow", "populate_by_name": True}

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, v: str) -> str:
        """Validate kind is DataContract."""
        if v != "DataContract":
            raise ValueError(f"kind must be 'DataContract', got '{v}'")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate status value."""
        if v is not None:
            valid_statuses = ["draft", "active", "deprecated", "retired", "current"]
            if v.lower() not in valid_statuses:
                raise ValueError(f"status must be one of {valid_statuses}, got '{v}'")
        return v

    def get_dataset_names(self) -> List[str]:
        """Get list of dataset/table names in this contract."""
        if not self.dataset:
            return []
        return [d.name for d in self.dataset if d.name]

    def get_dataset(self, name: str) -> Optional[ODCSDataset]:
        """Get a specific dataset by name."""
        if not self.dataset:
            return None
        for ds in self.dataset:
            if ds.name == name or ds.physicalName == name:
                return ds
        return None

    def get_all_quality_rules(self) -> List[ODCSQuality]:
        """Get all quality rules (contract-level and dataset-level)."""
        rules = []

        # Contract-level rules
        if self.quality:
            rules.extend(self.quality)

        # Dataset-level rules
        if self.dataset:
            for ds in self.dataset:
                if ds.quality:
                    rules.extend(ds.quality)

        return rules

    def get_columns_for_dataset(self, dataset_name: str) -> List[ODCSColumn]:
        """Get columns for a specific dataset."""
        ds = self.get_dataset(dataset_name)
        return ds.columns if ds and ds.columns else []
