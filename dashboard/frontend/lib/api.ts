/**
 * API client for Baselinr Dashboard Backend
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface FetchOptions {
  warehouse?: string;
  schema?: string;
  table?: string;
  status?: string;
  severity?: string;
  days?: number;
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
  successful_runs: number;
  failed_runs: number;
  total_tables: number;
  total_drift_alerts: number;
  high_severity_alerts: number;
  trends: Array<{
    date: string;
    runs: number;
    alerts: number;
  }>;
  warehouse_summary: Array<{
    warehouse: string;
    runs: number;
    tables: number;
    alerts: number;
  }>;
}

export async function fetchDashboardMetrics(
  options: { warehouse?: string; days?: number } = {}
): Promise<DashboardMetrics> {
  return fetchAPI<DashboardMetrics>('/api/dashboard/metrics', options);
}

export interface Run {
  run_id: string;
  warehouse: string;
  schema: string;
  table: string;
  status: string;
  started_at: string;
  completed_at?: string;
  duration_seconds?: number;
  rows_profiled?: number;
  metrics_count?: number;
}

export async function fetchRuns(options: FetchOptions = {}): Promise<Run[]> {
  return fetchAPI<Run[]>('/api/runs', options);
}

export interface RunDetails {
  run_id: string;
  warehouse: string;
  schema: string;
  table: string;
  status: string;
  started_at: string;
  completed_at?: string;
  duration_seconds?: number;
  rows_profiled?: number;
  metrics: Array<{
    column: string;
    metric_name: string;
    metric_value: number | string;
    data_type?: string;
  }>;
}

export async function fetchRunDetails(runId: string): Promise<RunDetails> {
  return fetchAPI<RunDetails>(`/api/runs/${runId}`);
}

export interface DriftAlert {
  alert_id: string;
  run_id: string;
  warehouse: string;
  schema: string;
  table: string;
  column?: string;
  severity: 'low' | 'medium' | 'high';
  drift_type: string;
  detected_at: string;
  baseline_value?: number | string;
  current_value?: number | string;
  change_percentage?: number;
  message?: string;
}

export async function fetchDriftAlerts(options: FetchOptions = {}): Promise<DriftAlert[]> {
  return fetchAPI<DriftAlert[]>('/api/drift', options);
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

