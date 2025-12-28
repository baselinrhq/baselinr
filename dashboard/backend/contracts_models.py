"""
ODCS Contracts API models for Baselinr Dashboard.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# =============================================================================
# Request/Response Models
# =============================================================================


class ODCSLink(BaseModel):
    """External link reference."""
    url: str
    type: Optional[str] = None
    title: Optional[str] = None


class ODCSContact(BaseModel):
    """Contact information."""
    name: Optional[str] = None
    email: Optional[str] = None
    url: Optional[str] = None
    role: Optional[str] = None


class ODCSInfo(BaseModel):
    """Contract information/metadata."""
    title: str
    description: Optional[str] = None
    version: Optional[str] = None
    owner: Optional[str] = None
    domain: Optional[str] = None
    dataProduct: Optional[str] = None
    tenant: Optional[str] = None
    contact: Optional[ODCSContact] = None
    links: Optional[List[ODCSLink]] = None


class ODCSServerEnvironment(BaseModel):
    """Server/connection configuration for an environment."""
    type: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    account: Optional[str] = None
    database: Optional[str] = None
    schema_: Optional[str] = Field(None, alias="schema")
    catalog: Optional[str] = None
    warehouse: Optional[str] = None
    project: Optional[str] = None
    dataset: Optional[str] = None
    location: Optional[str] = None
    bucket: Optional[str] = None
    path: Optional[str] = None
    url: Optional[str] = None

    model_config = {"populate_by_name": True}


class ODCSServer(BaseModel):
    """Server configurations for different environments."""
    production: Optional[ODCSServerEnvironment] = None
    development: Optional[ODCSServerEnvironment] = None
    staging: Optional[ODCSServerEnvironment] = None
    test: Optional[ODCSServerEnvironment] = None


class ODCSQualitySpecification(BaseModel):
    """Specification for a quality rule."""
    column: Optional[str] = None
    columns: Optional[List[str]] = None
    rule: Optional[str] = None
    pattern: Optional[str] = None
    minValue: Optional[float] = None
    maxValue: Optional[float] = None
    values: Optional[List[Any]] = None
    referenceTable: Optional[str] = None
    referenceColumn: Optional[str] = None
    threshold: Optional[float] = None
    query: Optional[str] = None
    expression: Optional[str] = None


class ODCSQuality(BaseModel):
    """Data quality rule definition."""
    type: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    dimension: Optional[str] = None
    severity: Optional[str] = "error"
    specification: Optional[ODCSQualitySpecification] = None
    column: Optional[str] = None
    rule: Optional[str] = None


class ODCSColumnQuality(BaseModel):
    """Column-level quality rule."""
    type: Optional[str] = None
    rule: Optional[str] = None
    severity: Optional[str] = "error"
    description: Optional[str] = None


class ODCSColumn(BaseModel):
    """Column definition within a dataset."""
    name: str = Field(..., alias="column")
    businessName: Optional[str] = None
    logicalType: Optional[str] = None
    physicalType: Optional[str] = None
    description: Optional[str] = None
    isPrimaryKey: Optional[bool] = False
    primaryKeyPosition: Optional[int] = None
    isNullable: Optional[bool] = True
    isUnique: Optional[bool] = False
    classification: Optional[str] = None
    tags: Optional[List[str]] = None
    partitionStatus: Optional[bool] = False
    clusterStatus: Optional[bool] = False
    sampleValues: Optional[List[Any]] = None
    defaultValue: Optional[Any] = None
    quality: Optional[List[ODCSColumnQuality]] = None
    criticalDataElementStatus: Optional[bool] = False

    model_config = {"populate_by_name": True}


class ODCSDataset(BaseModel):
    """Dataset (table/view) definition."""
    name: Optional[str] = Field(None, alias="table")
    physicalName: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = "table"
    columns: Optional[List[ODCSColumn]] = None
    dataGranularity: Optional[str] = None
    quality: Optional[List[ODCSQuality]] = None
    tags: Optional[List[str]] = None

    model_config = {"populate_by_name": True}


class ODCSServiceLevel(BaseModel):
    """Service level agreement property."""
    property: str
    value: Any
    unit: Optional[str] = None
    column: Optional[str] = None
    description: Optional[str] = None


class ODCSStakeholder(BaseModel):
    """Stakeholder information."""
    username: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    dateIn: Optional[str] = None
    dateOut: Optional[str] = None
    comment: Optional[str] = None


class ODCSRole(BaseModel):
    """Access role definition."""
    role: str
    access: Optional[str] = None
    description: Optional[str] = None


class ODCSPrice(BaseModel):
    """Pricing information."""
    priceAmount: Optional[float] = None
    priceCurrency: Optional[str] = None
    priceUnit: Optional[str] = None
    description: Optional[str] = None


class ODCSContract(BaseModel):
    """Full ODCS Contract model."""
    kind: str = "DataContract"
    apiVersion: str = "v3.1.0"
    id: Optional[str] = None
    uuid: Optional[str] = None
    version: Optional[str] = None
    status: Optional[str] = "active"
    info: Optional[ODCSInfo] = None
    servers: Optional[ODCSServer] = None
    dataset: Optional[List[ODCSDataset]] = None
    quality: Optional[List[ODCSQuality]] = None
    servicelevels: Optional[List[ODCSServiceLevel]] = None
    stakeholders: Optional[List[ODCSStakeholder]] = None
    roles: Optional[List[ODCSRole]] = None
    price: Optional[ODCSPrice] = None
    tags: Optional[List[str]] = None
    customProperties: Optional[List[Dict[str, Any]]] = None


# =============================================================================
# Summary and List Response Models
# =============================================================================


class ContractSummary(BaseModel):
    """Summary of a contract for list views."""
    id: Optional[str] = None
    title: Optional[str] = None
    status: Optional[str] = None
    owner: Optional[str] = None
    domain: Optional[str] = None
    datasets: List[str] = Field(default_factory=list)
    quality_rules_count: int = 0
    service_levels_count: int = 0
    stakeholders_count: int = 0


class ContractsListResponse(BaseModel):
    """Response for list contracts endpoint."""
    contracts: List[ContractSummary]
    total: int


class ContractDetailResponse(BaseModel):
    """Response for get contract endpoint."""
    contract: ODCSContract


class ValidationIssue(BaseModel):
    """A validation issue."""
    message: str
    severity: str
    path: Optional[str] = None
    code: Optional[str] = None


class ContractValidationResponse(BaseModel):
    """Response for contract validation endpoint."""
    valid: bool
    contracts_checked: int
    errors: List[Dict[str, str]] = Field(default_factory=list)
    warnings: List[Dict[str, str]] = Field(default_factory=list)


class ValidationRuleFromContract(BaseModel):
    """A validation rule extracted from a contract."""
    type: str
    table: str
    column: Optional[str] = None
    severity: str = "error"
    dimension: Optional[str] = None
    description: Optional[str] = None
    contract_id: Optional[str] = None


class ContractRulesResponse(BaseModel):
    """Response for contract rules endpoint."""
    rules: List[ValidationRuleFromContract]
    total: int


# =============================================================================
# Request Models
# =============================================================================


class CreateContractRequest(BaseModel):
    """Request to create a new contract."""
    contract: ODCSContract


class UpdateContractRequest(BaseModel):
    """Request to update an existing contract."""
    contract: ODCSContract

