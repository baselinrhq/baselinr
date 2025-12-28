/**
 * TypeScript type definitions for ODCS (Open Data Contract Standard) v3.1.0
 * 
 * These types match the Python Pydantic models in baselinr/contracts/odcs_schema.py
 * Reference: https://bitol-io.github.io/open-data-contract-standard/
 */

// =============================================================================
// Enums
// =============================================================================

export type ODCSKind = 'DataContract'

export type ODCSStatus = 'draft' | 'active' | 'deprecated' | 'retired' | 'current'

export type ODCSDatasetType = 
  | 'table'
  | 'view'
  | 'materializedView'
  | 'stream'
  | 'object'
  | 'file'
  | 'topic'

export type ODCSLogicalType =
  | 'string'
  | 'text'
  | 'integer'
  | 'bigint'
  | 'smallint'
  | 'tinyint'
  | 'float'
  | 'double'
  | 'decimal'
  | 'numeric'
  | 'boolean'
  | 'date'
  | 'time'
  | 'timestamp'
  | 'timestamptz'
  | 'binary'
  | 'array'
  | 'map'
  | 'struct'
  | 'json'
  | 'uuid'
  | 'geography'
  | 'geometry'
  | 'variant'
  | 'object'

export type ODCSClassification =
  | 'public'
  | 'internal'
  | 'confidential'
  | 'restricted'
  | 'pii'
  | 'phi'
  | 'pci'

export type ODCSQualityDimension =
  | 'completeness'
  | 'accuracy'
  | 'validity'
  | 'uniqueness'
  | 'consistency'
  | 'timeliness'
  | 'integrity'

export type ODCSQualitySeverity = 'info' | 'warning' | 'error' | 'critical'

export type ODCSServerType =
  | 'postgres'
  | 'postgresql'
  | 'snowflake'
  | 'bigquery'
  | 'redshift'
  | 'mysql'
  | 'sqlite'
  | 'databricks'
  | 'spark'
  | 'kafka'
  | 's3'
  | 'gcs'
  | 'azureBlob'
  | 'jdbc'
  | 'custom'

// =============================================================================
// Supporting Types
// =============================================================================

export interface ODCSLink {
  url: string
  type?: string | null
  title?: string | null
}

export interface ODCSContact {
  name?: string | null
  email?: string | null
  url?: string | null
  role?: string | null
}

export interface ODCSInfo {
  title: string
  description?: string | null
  version?: string | null
  owner?: string | null
  domain?: string | null
  dataProduct?: string | null
  tenant?: string | null
  contact?: ODCSContact | null
  links?: ODCSLink[] | null
}

export interface ODCSServerEnvironment {
  type?: string | null
  host?: string | null
  port?: number | null
  account?: string | null
  database?: string | null
  schema?: string | null
  catalog?: string | null
  driver?: string | null
  warehouse?: string | null
  project?: string | null
  dataset?: string | null
  location?: string | null
  bucket?: string | null
  path?: string | null
  url?: string | null
}

export interface ODCSServer {
  production?: ODCSServerEnvironment | null
  development?: ODCSServerEnvironment | null
  staging?: ODCSServerEnvironment | null
  test?: ODCSServerEnvironment | null
}

export interface ODCSQualitySpecification {
  column?: string | null
  columns?: string[] | null
  rule?: string | null
  pattern?: string | null
  minValue?: number | null
  maxValue?: number | null
  values?: any[] | null
  referenceTable?: string | null
  referenceColumn?: string | null
  threshold?: number | null
  query?: string | null
  expression?: string | null
}

export interface ODCSQuality {
  type?: string | null
  code?: string | null
  name?: string | null
  description?: string | null
  dimension?: ODCSQualityDimension | string | null
  severity?: ODCSQualitySeverity | string | null
  specification?: ODCSQualitySpecification | null
  column?: string | null
  rule?: string | null
  toolName?: string | null
  toolRuleName?: string | null
  scheduleCronExpression?: string | null
  businessImpact?: string | null
  customProperties?: Record<string, any>[] | null
}

export interface ODCSColumnQuality {
  type?: string | null
  rule?: string | null
  severity?: string | null
  description?: string | null
}

export interface ODCSColumn {
  name: string
  column?: string  // Alias for name
  businessName?: string | null
  logicalType?: ODCSLogicalType | string | null
  physicalType?: string | null
  description?: string | null
  isPrimaryKey?: boolean | null
  primaryKeyPosition?: number | null
  isNullable?: boolean | null
  isUnique?: boolean | null
  classification?: ODCSClassification | string | null
  tags?: string[] | null
  partitionStatus?: boolean | null
  partitionKeyPosition?: number | null
  clusterStatus?: boolean | null
  clusterKeyPosition?: number | null
  transformSourceTables?: string[] | null
  transformLogic?: string | null
  transformDescription?: string | null
  sampleValues?: any[] | null
  defaultValue?: any | null
  quality?: ODCSColumnQuality[] | null
  criticalDataElementStatus?: boolean | null
  encryptedColumnName?: string | null
  authoritativeDefinitions?: ODCSLink[] | null
}

export interface ODCSDataset {
  name?: string | null
  table?: string  // Alias for name
  physicalName?: string | null
  description?: string | null
  type?: ODCSDatasetType | string | null
  columns?: ODCSColumn[] | null
  dataGranularity?: string | null
  quality?: ODCSQuality[] | null
  tags?: string[] | null
  priorTableName?: string | null
  authoritativeDefinitions?: ODCSLink[] | null
}

export interface ODCSServiceLevel {
  property: string
  value: number | string
  unit?: string | null
  column?: string | null
  description?: string | null
  driver?: string | null
}

export interface ODCSStakeholder {
  username?: string | null
  name?: string | null
  role?: string | null
  email?: string | null
  dateIn?: string | null
  dateOut?: string | null
  replacedByUsername?: string | null
  comment?: string | null
}

export interface ODCSRole {
  role: string
  access?: string | null
  description?: string | null
  firstLevelApprovers?: string | null
  secondLevelApprovers?: string | null
}

export interface ODCSPrice {
  priceAmount?: number | null
  priceCurrency?: string | null
  priceUnit?: string | null
  description?: string | null
}

export interface ODCSCustomProperty {
  property: string
  value: any
}

// =============================================================================
// Main Contract Type
// =============================================================================

export interface ODCSContract {
  // Required fields
  kind: ODCSKind | string
  apiVersion: string
  
  // Identity
  id?: string | null
  uuid?: string | null
  version?: string | null
  status?: ODCSStatus | string | null
  
  // Metadata
  info?: ODCSInfo | null
  
  // Legacy fields (v2.x compatibility)
  datasetDomain?: string | null
  quantumName?: string | null
  userConsumptionMode?: string | null
  tenant?: string | null
  
  // Description (legacy)
  description?: Record<string, string> | null
  
  // Support channels
  productDl?: string | null
  productSlackChannel?: string | null
  productFeedbackUrl?: string | null
  
  // Source system info
  sourcePlatform?: string | null
  sourceSystem?: string | null
  datasetProject?: string | null
  datasetName?: string | null
  
  // Type
  type?: string | null
  
  // Server/connection configuration
  servers?: ODCSServer | null
  
  // Legacy connection fields (v2.x)
  driver?: string | null
  driverVersion?: string | null
  server?: string | null
  database?: string | null
  username?: string | null
  password?: string | null
  schedulerAppName?: string | null
  
  // Dataset definitions
  dataset?: ODCSDataset[] | null
  
  // Quality rules (contract-level)
  quality?: ODCSQuality[] | null
  
  // Service level agreements
  servicelevels?: ODCSServiceLevel[] | null
  slaProperties?: ODCSServiceLevel[] | null  // Alias
  slaDefaultColumn?: string | null
  
  // Stakeholders
  stakeholders?: ODCSStakeholder[] | null
  
  // Access roles
  roles?: ODCSRole[] | null
  
  // Pricing
  price?: ODCSPrice | null
  
  // Tags
  tags?: string[] | null
  
  // Custom properties
  customProperties?: ODCSCustomProperty[] | null
  
  // Timestamps
  contractCreatedTs?: string | null
  systemInstance?: string | null
}

// =============================================================================
// Helper Types for UI
// =============================================================================

export interface ContractSummary {
  id: string | null
  title: string | null
  status: string | null
  owner: string | null
  domain: string | null
  datasets: string[]
  quality_rules_count: number
  service_levels_count: number
  stakeholders_count: number
}

export interface ContractValidationResult {
  valid: boolean
  contracts_checked: number
  errors: Array<{
    contract?: string
    message: string
  }>
  warnings: Array<{
    contract?: string
    message: string
  }>
}

export interface ValidationRuleFromContract {
  type: string
  table: string
  column: string | null
  severity: string
  dimension: string | null
  description: string | null
  contractId: string | null
}

// =============================================================================
// API Response Types
// =============================================================================

export interface ContractsListResponse {
  contracts: ContractSummary[]
  total: number
}

export interface ContractDetailResponse {
  contract: ODCSContract
}

export interface ContractRulesResponse {
  rules: ValidationRuleFromContract[]
  total: number
}

