/**
 * TypeScript type definitions for Baselinr configuration
 * 
 * These types match the Python Pydantic models in baselinr/config/schema.py
 */

// Database type enum
export type DatabaseType = 
  | 'postgres'
  | 'snowflake'
  | 'sqlite'
  | 'mysql'
  | 'bigquery'
  | 'redshift'

// Connection configuration
export interface ConnectionConfig {
  type: DatabaseType
  host?: string | null
  port?: number | null
  database: string
  username?: string | null
  password?: string | null
  schema?: string | null
  
  // Snowflake-specific
  account?: string | null
  warehouse?: string | null
  role?: string | null
  
  // SQLite-specific
  filepath?: string | null
  
  // Additional connection parameters
  extra_params?: Record<string, any>
}

// Partition configuration
export interface PartitionConfig {
  key?: string | null
  strategy: 'latest' | 'recent_n' | 'sample' | 'all' | 'specific_values'
  recent_n?: number | null
  values?: any[] | null
  metadata_fallback?: boolean
}

// Sampling configuration
export interface SamplingConfig {
  enabled: boolean
  method: 'random' | 'stratified' | 'topk'
  fraction: number
  max_rows?: number | null
}

// Column-level drift configuration
export interface ColumnDriftConfig {
  enabled?: boolean | null
  strategy?: 'absolute_threshold' | 'standard_deviation' | 'statistical' | null
  thresholds?: Record<string, number> | null
  baselines?: Record<string, any> | null
}

// Column-level anomaly configuration
export interface ColumnAnomalyConfig {
  enabled?: boolean | null
  methods?: string[] | null
  thresholds?: Record<string, number> | null
}

// Column-level profiling configuration
export interface ColumnProfilingConfig {
  enabled?: boolean | null
}

// Column configuration
export interface ColumnConfig {
  name: string
  pattern_type?: 'wildcard' | 'regex' | null
  metrics?: string[] | null
  profiling?: ColumnProfilingConfig | null
  drift?: ColumnDriftConfig | null
  anomaly?: ColumnAnomalyConfig | null
}

// Table pattern configuration
export interface TablePattern {
  database?: string | null
  schema?: string | null
  table?: string | null
  pattern?: string | null
  pattern_type?: 'wildcard' | 'regex' | null
  schema_pattern?: string | null
  select_all_schemas?: boolean | null
  select_schema?: boolean | null
  tags?: string[] | null
  tags_any?: string[] | null
  dbt_ref?: string | null
  dbt_selector?: string | null
  dbt_project_path?: string | null
  dbt_manifest_path?: string | null
  exclude_patterns?: string[] | null
  table_types?: string[] | null
  min_rows?: number | null
  max_rows?: number | null
  required_columns?: string[] | null
  modified_since_days?: number | null
  override_priority?: number | null
}

// Schema-level configuration
export interface SchemaConfig {
  database?: string | null
  schema?: string | null
  table_types?: string[] | null
  min_rows?: number | null
  max_rows?: number | null
  required_columns?: string[] | null
  modified_since_days?: number | null
  exclude_patterns?: string[] | null
}

// Database-level configuration
export interface DatabaseConfig {
  database: string
  table_types?: string[] | null
  min_rows?: number | null
  max_rows?: number | null
  required_columns?: string[] | null
  modified_since_days?: number | null
  exclude_patterns?: string[] | null
}

// Discovery options configuration
export interface DiscoveryOptionsConfig {
  include_schemas?: string[] | null
  exclude_schemas?: string[] | null
  include_table_types?: string[] | null
  exclude_table_types?: string[] | null
  cache_discovery?: boolean
  cache_ttl_seconds?: number
  max_tables_per_pattern?: number
  max_schemas_per_database?: number
  discovery_limit_action?: 'warn' | 'error' | 'skip'
  validate_regex?: boolean
  tag_provider?: string | null
  dbt_manifest_path?: string | null
}

// Profiling configuration
export interface ProfilingConfig {
  tables?: TablePattern[]
  schemas?: SchemaConfig[] | null
  databases?: DatabaseConfig[] | null
  max_distinct_values?: number
  compute_histograms?: boolean
  histogram_bins?: number
  metrics?: string[]
  default_sample_ratio?: number
  table_discovery?: boolean
  discovery_options?: DiscoveryOptionsConfig
  enable_enrichment?: boolean
  enable_approx_distinct?: boolean
  enable_schema_tracking?: boolean
  enable_type_inference?: boolean
  enable_column_stability?: boolean
  stability_window?: number
  type_inference_sample_size?: number
  extract_lineage?: boolean
}

// Storage configuration
export interface StorageConfig {
  connection: ConnectionConfig
  results_table?: string
  runs_table?: string
  create_tables?: boolean
  enable_expectation_learning?: boolean
  learning_window_days?: number
  min_samples?: number
  ewma_lambda?: number
  enable_anomaly_detection?: boolean
  anomaly_enabled_methods?: string[]
  anomaly_iqr_threshold?: number
  anomaly_mad_threshold?: number
  anomaly_ewma_deviation_threshold?: number
  anomaly_seasonality_enabled?: boolean
  anomaly_regime_shift_enabled?: boolean
  anomaly_regime_shift_window?: number
  anomaly_regime_shift_sensitivity?: number
}

// Drift detection configuration
export interface DriftDetectionConfig {
  strategy?: string
  absolute_threshold?: Record<string, number>
  standard_deviation?: Record<string, number>
  ml_based?: Record<string, any>
  statistical?: Record<string, any>
  baselines?: Record<string, any>
  enable_type_specific_thresholds?: boolean
  type_specific_thresholds?: Record<string, Record<string, any>>
}

// Hook configuration
export interface HookConfig {
  type: 'logging' | 'sql' | 'snowflake' | 'slack' | 'custom'
  enabled?: boolean
  log_level?: string | null
  connection?: ConnectionConfig | null
  table_name?: string | null
  webhook_url?: string | null
  channel?: string | null
  username?: string | null
  min_severity?: string | null
  alert_on_drift?: boolean | null
  alert_on_schema_change?: boolean | null
  alert_on_profiling_failure?: boolean | null
  timeout?: number | null
  module?: string | null
  class_name?: string | null
  params?: Record<string, any>
}

// Hooks configuration
export interface HooksConfig {
  enabled?: boolean
  hooks?: HookConfig[]
}

// Retry configuration
export interface RetryConfig {
  enabled?: boolean
  retries?: number
  backoff_strategy?: 'exponential' | 'fixed'
  min_backoff?: number
  max_backoff?: number
}

// Monitoring configuration
export interface MonitoringConfig {
  enable_metrics?: boolean
  port?: number
  keep_alive?: boolean
}

// Execution configuration
export interface ExecutionConfig {
  max_workers?: number
  batch_size?: number
  queue_size?: number
  warehouse_limits?: Record<string, number>
}

// Change detection configuration
export interface ChangeDetectionConfig {
  enabled?: boolean
  metadata_table?: string
  connector_overrides?: Record<string, Record<string, any>>
  snapshot_ttl_minutes?: number
}

// Partial profiling configuration
export interface PartialProfilingConfig {
  enabled?: boolean
  allow_partition_pruning?: boolean
  max_partitions_per_run?: number
  mergeable_metrics?: string[]
}

// Adaptive scheduling configuration
export interface AdaptiveSchedulingConfig {
  enabled?: boolean
  default_interval_minutes?: number
  min_interval_minutes?: number
  max_interval_minutes?: number
  priority_overrides?: Record<string, number>
  staleness_penalty_minutes?: number
}

// Cost control configuration
export interface CostControlConfig {
  enabled?: boolean
  max_bytes_scanned?: number | null
  max_rows_scanned?: number | null
  fallback_strategy?: 'sample' | 'defer' | 'full'
  sample_fraction?: number
}

// Incremental configuration
export interface IncrementalConfig {
  enabled?: boolean
  change_detection?: ChangeDetectionConfig
  partial_profiling?: PartialProfilingConfig
  adaptive_scheduling?: AdaptiveSchedulingConfig
  cost_controls?: CostControlConfig
}

// Schema change suppression rule
export interface SchemaChangeSuppressionRule {
  table?: string | null
  schema?: string | null
  change_type?: string | null
}

// Schema change configuration
export interface SchemaChangeConfig {
  enabled?: boolean
  similarity_threshold?: number
  suppression?: SchemaChangeSuppressionRule[]
}

// Query history configuration
export interface QueryHistoryConfig {
  enabled?: boolean
  incremental?: boolean
  lookback_days?: number
  min_query_count?: number
  exclude_patterns?: string[] | null
  edge_expiration_days?: number | null
  warn_stale_days?: number
  snowflake?: Record<string, any> | null
  bigquery?: Record<string, any> | null
  postgres?: Record<string, any> | null
  redshift?: Record<string, any> | null
  mysql?: Record<string, any> | null
}

// Lineage configuration
export interface LineageConfig {
  enabled?: boolean
  extract_column_lineage?: boolean
  providers?: string[] | null
  dbt?: Record<string, any> | null
  dagster?: Record<string, any> | null
  query_history?: QueryHistoryConfig | null
}

// Chat configuration
export interface ChatConfig {
  enabled?: boolean
  max_history_messages?: number
  max_iterations?: number
  tool_timeout?: number
  cache_tool_results?: boolean
  enable_context_enhancement?: boolean
}

// LLM configuration
export interface LLMConfig {
  enabled?: boolean
  provider?: 'openai' | 'anthropic' | 'azure' | 'ollama'
  api_key?: string | null
  model?: string
  temperature?: number
  max_tokens?: number
  timeout?: number
  rate_limit?: Record<string, any>
  fallback_to_template?: boolean
  chat?: ChatConfig
}

// Visualization styles configuration
export interface VisualizationStylesConfig {
  node_colors?: Record<string, string>
}

// Visualization configuration
export interface VisualizationConfig {
  enabled?: boolean
  max_depth?: number
  direction?: 'upstream' | 'downstream' | 'both'
  confidence_threshold?: number
  layout?: 'hierarchical' | 'circular' | 'force_directed' | 'grid'
  web_viewer_port?: number
  theme?: 'dark' | 'light'
  styles?: VisualizationStylesConfig
}

// RCA collector configuration
export interface RCACollectorConfig {
  dbt?: boolean | null
  manifest_path?: string | null
  project_dir?: string | null
  dagster?: boolean | null
  dagster_instance_path?: string | null
  dagster_graphql_url?: string | null
  airflow?: boolean | null
  airflow_api_url?: string | null
  airflow_api_version?: string | null
  airflow_username?: string | null
  airflow_password?: string | null
  airflow_metadata_db_connection?: string | null
  airflow_dag_ids?: string[] | null
}

// RCA configuration
export interface RCAConfig {
  enabled?: boolean
  lookback_window_hours?: number
  max_depth?: number
  max_causes_to_return?: number
  min_confidence_threshold?: number
  auto_analyze?: boolean
  enable_pattern_learning?: boolean
  collectors?: RCACollectorConfig
}

// Validation rule configuration
export interface ValidationRuleConfig {
  type: 'format' | 'range' | 'enum' | 'not_null' | 'unique' | 'referential'
  table?: string | null
  column?: string | null
  pattern?: string | null
  min_value?: number | null
  max_value?: number | null
  allowed_values?: any[] | null
  references?: Record<string, string> | null
  severity?: 'low' | 'medium' | 'high'
  enabled?: boolean
}

// Validation configuration
export interface ValidationConfig {
  enabled?: boolean
  providers?: Record<string, any>[]
  rules?: ValidationRuleConfig[]
}

// Main Baselinr configuration
// Quality scoring configuration
export interface QualityScoringWeights {
  completeness?: number
  validity?: number
  consistency?: number
  freshness?: number
  uniqueness?: number
  accuracy?: number
}

export interface QualityScoringThresholds {
  healthy?: number
  warning?: number
  critical?: number
}

export interface QualityScoringFreshness {
  excellent?: number
  good?: number
  acceptable?: number
}

export interface QualityScoringConfig {
  enabled?: boolean
  weights?: QualityScoringWeights
  thresholds?: QualityScoringThresholds
  freshness?: QualityScoringFreshness
  store_history?: boolean
  history_retention_days?: number
}

export interface BaselinrConfig {
  environment?: 'development' | 'test' | 'production'
  source: ConnectionConfig
  storage: StorageConfig
  profiling?: ProfilingConfig
  drift_detection?: DriftDetectionConfig
  hooks?: HooksConfig
  monitoring?: MonitoringConfig
  retry?: RetryConfig
  execution?: ExecutionConfig
  incremental?: IncrementalConfig
  schema_change?: SchemaChangeConfig
  lineage?: LineageConfig | null
  visualization?: VisualizationConfig
  llm?: LLMConfig | null
  smart_selection?: any | null
  rca?: RCAConfig
  validation?: ValidationConfig | null
  quality_scoring?: QualityScoringConfig | null
}

// API Response Types

export interface ConfigResponse {
  config: BaselinrConfig
  version?: string
  last_modified?: string
}

export interface ConfigValidationResponse {
  valid: boolean
  errors?: string[]
  warnings?: string[]
}

export interface ConnectionTestResponse {
  success: boolean
  message?: string
  error?: string
  connection_time_ms?: number
}

export interface ConfigHistoryEntry {
  version_id: string
  created_at: string
  created_by?: string
  comment?: string
  description?: string // Alias for comment (for backwards compatibility)
  is_current?: boolean
}

export interface ConfigHistoryResponse {
  versions: ConfigHistoryEntry[]
  total?: number
}

export interface ConfigDiffResponse {
  version_id: string
  compare_with: string
  added: Record<string, unknown>
  removed: Record<string, unknown>
  changed: Record<string, { old: unknown; new: unknown }>
}

export interface RestoreConfigRequest {
  confirm: boolean
  comment?: string
}

export interface RestoreConfigResponse {
  success: boolean
  message: string
  config: BaselinrConfig
}

export interface ConfigVersionResponse {
  version_id: string
  config: BaselinrConfig
  created_at: string
  created_by?: string
  description?: string
}

/**
 * Storage status response
 */
export interface StorageStatusResponse {
  connection_status: 'connected' | 'disconnected' | 'error'
  connection_error?: string
  results_table_exists: boolean
  runs_table_exists: boolean
  last_checked: string
}

/**
 * Configuration section status
 */
export interface ConfigSectionStatus {
  section: string
  status: 'configured' | 'incomplete' | 'not_configured' | 'error'
  message?: string
  lastUpdated?: string
}

/**
 * Configuration status response
 */
export interface ConfigStatusResponse {
  overall_completion: number // 0-100
  sections: ConfigSectionStatus[]
  total_sections: number
  configured_sections: number
}

// Dataset Configuration Types - REMOVED
// All dataset configuration is now handled via ODCS contracts
// See types/odcs.ts for contract types

export interface MigrationPreviewRequest {
  config?: BaselinrConfig | null
}

export interface MigrationPreviewResponse {
  changes: Record<string, any>
  files_to_create: string[]
  datasets_to_migrate: number
}

export interface MigrationRequest {
  config?: BaselinrConfig | null
  backup: boolean
  output_dir?: string | null
}

export interface MigrationResponse {
  success: boolean
  migrated: number
  files_created: string[]
  backup_path?: string | null
  errors: string[]
}

