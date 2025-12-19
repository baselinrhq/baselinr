/**
 * API client for Baselinr Dashboard Backend
 */

import type { 
  DriftAlert,
  DriftSummary, 
  DriftDetails, 
  DriftImpact 
} from '@/types/drift';
import type {
  QualityScore,
  QualityScoresListResponse,
  ScoreHistoryResponse,
  SchemaScoreResponse,
  SystemScoreResponse,
  ColumnScoresListResponse,
  TrendAnalysis,
  ScoreComparison,
} from '@/types/quality';
import { getApiUrl } from './demo-mode';

const API_URL = getApiUrl();

interface FetchOptions {
  warehouse?: string;
  schema?: string;
  table?: string;
  status?: string;
  severity?: string;
  days?: number;
  start_date?: string;
  end_date?: string;
  min_duration?: number;
  max_duration?: number;
  sort_by?: string;
  sort_order?: string;
  limit?: number;
  offset?: number;
}

async function fetchAPI<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
  const params = new URLSearchParams();
  
  if (options.warehouse) params.append('warehouse', options.warehouse);
  if (options.schema) params.append('schema', options.schema);
  if (options.table) params.append('table', options.table);
  if (options.status) params.append('status', options.status);
  if (options.severity) params.append('severity', options.severity);
  if (options.days) params.append('days', options.days.toString());
  if (options.start_date) params.append('start_date', options.start_date);
  if (options.end_date) params.append('end_date', options.end_date);
  if (options.min_duration !== undefined) params.append('min_duration', options.min_duration.toString());
  if (options.max_duration !== undefined) params.append('max_duration', options.max_duration.toString());
  if (options.sort_by) params.append('sort_by', options.sort_by);
  if (options.sort_order) params.append('sort_order', options.sort_order);
  if (options.limit) params.append('limit', options.limit.toString());
  if (options.offset) params.append('offset', options.offset.toString());

  const url = `${API_URL}${endpoint}${params.toString() ? `?${params.toString()}` : ''}`;
  
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

export interface DashboardMetrics {
  total_runs: number;
  total_tables: number;
  total_drift_events: number;
  avg_row_count: number;
  kpis: Array<{
    name: string;
    value: string | number;
    change_percent?: number | null;
    trend: string;
  }>;
  run_trend: Array<{
    timestamp: string;
    value: number;
  }>;
  drift_trend: Array<{
    timestamp: string;
    value: number;
  }>;
  warehouse_breakdown: Record<string, number>;
  recent_runs: Run[];
  recent_drift: DriftAlert[];
  // Enhanced metrics
  validation_pass_rate?: number | null;
  total_validation_rules: number;
  failed_validation_rules: number;
  active_alerts: number;
  data_freshness_hours?: number | null;
  stale_tables_count: number;
  validation_trend: Array<{
    timestamp: string;
    value: number;
  }>;
  // Quality scoring metrics
  system_quality_score?: number | null;
  quality_score_status?: string | null;
  quality_trend?: string | null;
}

export async function fetchDashboardMetrics(
  options: { warehouse?: string; days?: number } = {}
): Promise<DashboardMetrics> {
  return fetchAPI<DashboardMetrics>('/api/dashboard/metrics', options);
}

export interface Run {
  run_id: string;
  dataset_name: string;
  schema_name?: string;
  warehouse_type: string;
  profiled_at: string;
  status: string;
  row_count?: number;
  column_count?: number;
  duration_seconds?: number;
  has_drift: boolean;
}

export async function fetchRuns(options: FetchOptions = {}): Promise<Run[]> {
  return fetchAPI<Run[]>('/api/runs', options);
}

export interface ColumnMetric {
  column_name: string;
  column_type?: string;
  null_count?: number;
  null_percent?: number;
  distinct_count?: number;
  distinct_percent?: number;
  min_value?: number | string;
  max_value?: number | string;
  mean?: number;
  stddev?: number;
  histogram?: unknown;
}

export interface RunDetails {
  run_id: string;
  dataset_name: string;
  schema_name?: string;
  warehouse_type: string;
  profiled_at: string;
  environment: string;
  row_count: number;
  column_count: number;
  columns: ColumnMetric[];
  metadata?: Record<string, unknown>;
  // Legacy fields for backward compatibility
  error_message?: string;
  error_logs?: string[];
}

export async function fetchRunDetails(runId: string): Promise<RunDetails> {
  return fetchAPI<RunDetails>(`/api/runs/${runId}`);
}

export interface RunComparison {
  runs: Run[];
  comparison: {
    row_count_diff: number;
    column_count_diff: number;
    common_columns: string[];
    unique_columns: Record<string, string[]>;
    metric_differences: Array<{
      column: string;
      metric: string;
      run_id: string;
      baseline_value: number | string;
      current_value: number | string;
      change_percent: number;
    }>;
  };
}

export async function fetchRunComparison(runIds: string[]): Promise<RunComparison> {
  const params = new URLSearchParams();
  params.append('run_ids', runIds.join(','));
  const url = `${API_URL}/api/runs/compare?${params.toString()}`;
  
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

export interface RetryRunResponse {
  status: string;
  message: string;
  run_id: string;
}

export async function retryRun(runId: string): Promise<RetryRunResponse> {
  const url = `${API_URL}/api/runs/${runId}/retry`;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

export async function fetchDriftAlerts(options: FetchOptions = {}): Promise<DriftAlert[]> {
  return fetchAPI<DriftAlert[]>('/api/drift', options);
}

// Enhanced drift API functions
export async function fetchDriftSummary(
  options: { days?: number; warehouse?: string } = {}
): Promise<DriftSummary> {
  const params = new URLSearchParams();
  if (options.days) params.append('days', options.days.toString());
  if (options.warehouse) params.append('warehouse', options.warehouse);
  
  const url = `${API_URL}/api/drift/summary${params.toString() ? `?${params.toString()}` : ''}`;
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

export async function fetchDriftDetails(eventId: string): Promise<DriftDetails> {
  const url = `${API_URL}/api/drift/${eventId}/details`;
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

export async function fetchDriftImpact(eventId: string): Promise<DriftImpact> {
  const url = `${API_URL}/api/drift/${eventId}/impact`;
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

export interface TableMetrics {
  table_name: string;
  schema?: string;
  warehouse: string;
  total_runs: number;
  last_run?: string;
  columns: Array<{
    column_name: string;
    data_type: string;
    latest_value?: number | string;
    trend?: 'up' | 'down' | 'stable';
  }>;
  historical_trends: Array<{
    date: string;
    row_count?: number;
    column_count?: number;
  }>;
}

export async function fetchTableMetrics(
  tableName: string,
  options: { schema?: string; warehouse?: string } = {}
): Promise<TableMetrics> {
  const params = new URLSearchParams();
  if (options.schema) params.append('schema', options.schema);
  if (options.warehouse) params.append('warehouse', options.warehouse);
  
  const url = `${API_URL}/api/tables/${tableName}/metrics${params.toString() ? `?${params.toString()}` : ''}`;
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

export async function exportRuns(
  format: 'json' | 'csv' = 'json',
  options: { warehouse?: string; days?: number } = {}
): Promise<Blob> {
  const params = new URLSearchParams();
  params.append('format', format);
  if (options.warehouse) params.append('warehouse', options.warehouse);
  if (options.days) params.append('days', options.days.toString());
  
  const url = `${API_URL}/api/export/runs?${params.toString()}`;
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  
  return response.blob();
}

export async function exportDrift(
  format: 'json' | 'csv' = 'json',
  options: { warehouse?: string; days?: number } = {}
): Promise<Blob> {
  const params = new URLSearchParams();
  params.append('format', format);
  if (options.warehouse) params.append('warehouse', options.warehouse);
  if (options.days) params.append('days', options.days.toString());
  
  const url = `${API_URL}/api/export/drift?${params.toString()}`;
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  
  return response.blob();
}

// Table list interfaces and functions
export interface TableListItem {
  table_name: string;
  schema_name?: string | null;
  warehouse_type: string;
  last_profiled?: string | null;
  row_count?: number | null;
  column_count?: number | null;
  total_runs: number;
  drift_count: number;
  validation_pass_rate?: number | null;
  has_recent_drift: boolean;
  has_failed_validations: boolean;
}

export interface TableListResponse {
  tables: TableListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface TableListOptions {
  warehouse?: string;
  schema?: string;
  search?: string;
  has_drift?: boolean;
  has_failed_validations?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export async function fetchTables(options: TableListOptions = {}): Promise<TableListResponse> {
  const params = new URLSearchParams();
  if (options.warehouse) params.append('warehouse', options.warehouse);
  if (options.schema) params.append('schema', options.schema);
  if (options.search) params.append('search', options.search);
  if (options.has_drift !== undefined) params.append('has_drift', options.has_drift.toString());
  if (options.has_failed_validations !== undefined) params.append('has_failed_validations', options.has_failed_validations.toString());
  if (options.sort_by) params.append('sort_by', options.sort_by);
  if (options.sort_order) params.append('sort_order', options.sort_order);
  if (options.page) params.append('page', options.page.toString());
  if (options.page_size) params.append('page_size', options.page_size.toString());
  
  const url = `${API_URL}/api/tables${params.toString() ? `?${params.toString()}` : ''}`;
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

// Table overview interfaces
export interface TableOverview {
  table_name: string;
  schema_name?: string | null;
  warehouse_type: string;
  last_profiled: string;
  row_count: number;
  column_count: number;
  total_runs: number;
  drift_count: number;
  validation_pass_rate?: number | null;
  total_validation_rules: number;
  failed_validation_rules: number;
  row_count_trend: Array<{ timestamp: string; value: number }>;
  null_percent_trend: Array<{ timestamp: string; value: number }>;
  columns: Array<{
    column_name: string;
    column_type: string;
    null_count?: number | null;
    null_percent?: number | null;
    distinct_count?: number | null;
    distinct_percent?: number | null;
    min_value?: string | number | null;
    max_value?: string | number | null;
    mean?: number | null;
    stddev?: number | null;
    histogram?: unknown;
  }>;
  recent_runs: Run[];
}

export async function fetchTableOverview(
  tableName: string,
  options: { schema?: string; warehouse?: string } = {}
): Promise<TableOverview> {
  const params = new URLSearchParams();
  if (options.schema) params.append('schema', options.schema);
  if (options.warehouse) params.append('warehouse', options.warehouse);
  
  const url = `${API_URL}/api/tables/${tableName}/overview${params.toString() ? `?${params.toString()}` : ''}`;
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

// Table drift history interfaces
export interface TableDriftHistory {
  table_name: string;
  schema_name?: string | null;
  drift_events: Array<{
    event_id?: string;
    alert_id?: string;
    run_id: string;
    table_name: string;
    column_name?: string | null;
    metric_name: string;
    baseline_value?: number | null;
    current_value?: number | null;
    change_percent?: number | null;
    change_percentage?: number | null;
    severity: string;
    timestamp?: string;
    detected_at?: string;
    warehouse_type: string;
  }>;
  summary: {
    total_events?: number;
    by_severity?: Record<string, number>;
    by_column?: Record<string, number>;
    recent_count?: number;
  };
}

export async function fetchTableDriftHistory(
  tableName: string,
  options: { schema?: string; warehouse?: string; limit?: number } = {}
): Promise<TableDriftHistory> {
  const params = new URLSearchParams();
  if (options.schema) params.append('schema', options.schema);
  if (options.warehouse) params.append('warehouse', options.warehouse);
  if (options.limit) params.append('limit', options.limit.toString());
  
  const url = `${API_URL}/api/tables/${tableName}/drift-history${params.toString() ? `?${params.toString()}` : ''}`;
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

import type { ValidationResult, ValidationResultDetails, ValidationFailureSamples } from '@/types/validation';

// Table validation results interfaces
export interface TableValidationResults {
  table_name: string;
  schema_name?: string | null;
  validation_results: ValidationResult[];
  summary: {
    total?: number;
    passed?: number;
    failed?: number;
    pass_rate?: number;
    by_rule_type?: Record<string, number>;
    by_severity?: Record<string, number>;
  };
}

export async function fetchTableValidationResults(
  tableName: string,
  options: { schema?: string; limit?: number } = {}
): Promise<TableValidationResults> {
  const params = new URLSearchParams();
  if (options.schema) params.append('schema', options.schema);
  if (options.limit) params.append('limit', options.limit.toString());
  
  const url = `${API_URL}/api/tables/${tableName}/validation-results${params.toString() ? `?${params.toString()}` : ''}`;
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

// Table config interfaces
export interface TableConfig {
  table_name: string;
  schema_name?: string | null;
  config: Record<string, unknown>;
}

export async function fetchTableConfig(
  tableName: string,
  options: { schema?: string } = {}
): Promise<TableConfig> {
  const params = new URLSearchParams();
  if (options.schema) params.append('schema', options.schema);
  
  const url = `${API_URL}/api/tables/${tableName}/config${params.toString() ? `?${params.toString()}` : ''}`;
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

// Validation dashboard interfaces and functions
export interface ValidationSummary {
  total_validations: number;
  passed_count: number;
  failed_count: number;
  pass_rate: number;
  by_rule_type: Record<string, number>;
  by_severity: Record<string, number>;
  by_table: Record<string, number>;
  trending: Array<{ timestamp: string; value: number }>;
  recent_runs: Array<{
    run_id: string;
    validated_at: string;
    total: number;
    passed: number;
    failed: number;
  }>;
}

export async function fetchValidationSummary(
  options: { days?: number; warehouse?: string } = {}
): Promise<ValidationSummary> {
  return fetchAPI<ValidationSummary>('/api/validation/summary', options);
}

export interface ValidationResultsList {
  results: ValidationResult[];
  total: number;
  page: number;
  page_size: number;
}

export async function fetchValidationResults(
  options: {
    table?: string;
    schema?: string;
    rule_type?: string;
    severity?: string;
    passed?: boolean;
    days?: number;
    page?: number;
    page_size?: number;
  } = {}
): Promise<ValidationResultsList> {
  const params = new URLSearchParams();
  if (options.table) params.append('table', options.table);
  if (options.schema) params.append('schema', options.schema);
  if (options.rule_type) params.append('rule_type', options.rule_type);
  if (options.severity) params.append('severity', options.severity);
  if (options.passed !== undefined) params.append('passed', options.passed.toString());
  if (options.days) params.append('days', options.days.toString());
  if (options.page) params.append('page', options.page.toString());
  if (options.page_size) params.append('page_size', options.page_size.toString());
  
  const url = `${API_URL}/api/validation/results${params.toString() ? `?${params.toString()}` : ''}`;
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

export async function fetchValidationResultDetails(
  resultId: number
): Promise<ValidationResultDetails> {
  const url = `${API_URL}/api/validation/results/${resultId}`;
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

export async function fetchValidationFailureSamples(
  resultId: number
): Promise<ValidationFailureSamples> {
  const url = `${API_URL}/api/validation/results/${resultId}/failures`;
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

// Quality Scores API
export async function fetchQualityScores(
  options: { schema?: string; status?: string } = {}
): Promise<QualityScoresListResponse> {
  return fetchAPI<QualityScoresListResponse>('/api/quality/scores', options);
}

export async function fetchTableScore(
  tableName: string,
  schema?: string
): Promise<QualityScore> {
  const options: FetchOptions = {};
  if (schema) {
    options.schema = schema;
  }
  const url = `/api/quality/scores/${encodeURIComponent(tableName)}`;
  console.log(`[API] fetchTableScore: ${url}`, options);
  return fetchAPI<QualityScore>(url, options);
}

export async function fetchScoreHistory(
  tableName: string,
  schema?: string,
  days?: number
): Promise<ScoreHistoryResponse> {
  const options: FetchOptions = {};
  if (schema) {
    options.schema = schema;
  }
  if (days) {
    options.days = days;
  }
  return fetchAPI<ScoreHistoryResponse>(
    `/api/quality/scores/${encodeURIComponent(tableName)}/history`,
    options
  );
}

export async function fetchSchemaScore(schemaName: string): Promise<SchemaScoreResponse> {
  return fetchAPI<SchemaScoreResponse>(
    `/api/quality/scores/schema/${encodeURIComponent(schemaName)}`
  );
}

export async function fetchSystemScore(): Promise<SystemScoreResponse> {
  return fetchAPI<SystemScoreResponse>('/api/quality/scores/system');
}

export async function fetchColumnScores(
  tableName: string,
  schema?: string,
  days?: number
): Promise<ColumnScoresListResponse> {
  const options: FetchOptions = {};
  if (schema) {
    options.schema = schema;
  }
  if (days) {
    options.days = days;
  }
  return fetchAPI<ColumnScoresListResponse>(
    `/api/quality/scores/${encodeURIComponent(tableName)}/columns`,
    options
  );
}

export async function fetchScoreTrend(
  tableName: string,
  schema?: string,
  days?: number
): Promise<TrendAnalysis> {
  const options: FetchOptions = {};
  if (schema) {
    options.schema = schema;
  }
  if (days) {
    options.days = days;
  }
  return fetchAPI<TrendAnalysis>(
    `/api/quality/scores/${encodeURIComponent(tableName)}/trend`,
    options
  );
}

export async function fetchScoreComparison(
  tables: string[],
  schema?: string
): Promise<ScoreComparison> {
  const options: FetchOptions = {};
  if (schema) {
    options.schema = schema;
  }
  const tablesParam = tables.map(encodeURIComponent).join(',');
  return fetchAPI<ScoreComparison>(
    `/api/quality/scores/compare?tables=${tablesParam}`,
    options
  );
}

