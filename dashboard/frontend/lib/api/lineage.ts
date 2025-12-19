/**
 * API client for lineage visualization endpoints
 */

import {
  LineageGraphResponse,
  NodeDetailsResponse,
  TableInfoResponse,
  DriftPathResponse,
  LineageImpactResponse,
  LineageFilters,
} from '@/types/lineage';
import { getApiUrl } from '../demo-mode';

const API_URL = getApiUrl();

export interface GetLineageGraphParams {
  table: string;
  schema?: string;
  column?: string;
  direction?: 'upstream' | 'downstream' | 'both';
  depth?: number;
  confidenceThreshold?: number;
  providers?: string[];
  schemas?: string[];
  databases?: string[];
  nodeType?: 'table' | 'column' | 'both';
  hasDrift?: boolean;
  driftSeverity?: string;
}

/**
 * Get lineage graph for a table
 */
export async function getLineageGraph(
  params: GetLineageGraphParams
): Promise<LineageGraphResponse> {
  const queryParams = new URLSearchParams();
  queryParams.append('table', params.table);
  
  if (params.schema) {
    queryParams.append('schema', params.schema);
  }
  if (params.direction) {
    queryParams.append('direction', params.direction);
  }
  if (params.depth !== undefined) {
    queryParams.append('depth', params.depth.toString());
  }
  if (params.confidenceThreshold !== undefined) {
    queryParams.append('confidence_threshold', params.confidenceThreshold.toString());
  }
  if (params.providers && params.providers.length > 0) {
    queryParams.append('provider', params.providers.join(','));
  }
  if (params.schemas && params.schemas.length > 0) {
    queryParams.append('schemas', params.schemas.join(','));
  }
  if (params.databases && params.databases.length > 0) {
    queryParams.append('databases', params.databases.join(','));
  }
  if (params.nodeType) {
    queryParams.append('node_type', params.nodeType);
  }
  if (params.hasDrift !== undefined) {
    queryParams.append('has_drift', params.hasDrift.toString());
  }
  if (params.driftSeverity) {
    queryParams.append('drift_severity', params.driftSeverity);
  }

  const url = `${API_URL}/api/lineage/graph?${queryParams.toString()}`;
  const response = await fetch(url);

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API error: ${response.status} ${response.statusText} - ${errorText}`);
  }

  return response.json();
}

/**
 * Get column-level lineage graph
 */
export async function getColumnLineageGraph(
  params: GetLineageGraphParams & { column: string }
): Promise<LineageGraphResponse> {
  const queryParams = new URLSearchParams();
  queryParams.append('table', params.table);
  queryParams.append('column', params.column);
  
  if (params.schema) {
    queryParams.append('schema', params.schema);
  }
  if (params.direction) {
    queryParams.append('direction', params.direction);
  }
  if (params.depth !== undefined) {
    queryParams.append('depth', params.depth.toString());
  }
  if (params.confidenceThreshold !== undefined) {
    queryParams.append('confidence_threshold', params.confidenceThreshold.toString());
  }

  const url = `${API_URL}/api/lineage/column-graph?${queryParams.toString()}`;
  const response = await fetch(url);

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API error: ${response.status} ${response.statusText} - ${errorText}`);
  }

  return response.json();
}

/**
 * Get detailed information about a specific node
 */
export async function getNodeDetails(nodeId: string): Promise<NodeDetailsResponse> {
  const url = `${API_URL}/api/lineage/node/${encodeURIComponent(nodeId)}`;
  const response = await fetch(url);

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API error: ${response.status} ${response.statusText} - ${errorText}`);
  }

  return response.json();
}

/**
 * Search for tables by name
 */
export async function searchTables(query: string, limit: number = 20): Promise<TableInfoResponse[]> {
  const queryParams = new URLSearchParams();
  queryParams.append('q', query);
  queryParams.append('limit', limit.toString());

  const url = `${API_URL}/api/lineage/search?${queryParams.toString()}`;
  console.log('Fetching from URL:', url);
  
  const response = await fetch(url);
  console.log('Response status:', response.status, response.statusText);

  if (!response.ok) {
    const errorText = await response.text();
    console.error('API error response:', errorText);
    throw new Error(`API error: ${response.status} ${response.statusText} - ${errorText}`);
  }

  const data = await response.json();
  console.log('Response data:', data);
  return data;
}

/**
 * Get all tables with lineage data
 */
export async function getAllTables(limit: number = 100): Promise<TableInfoResponse[]> {
  const queryParams = new URLSearchParams();
  queryParams.append('limit', limit.toString());

  const url = `${API_URL}/api/lineage/tables?${queryParams.toString()}`;
  const response = await fetch(url);

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API error: ${response.status} ${response.statusText} - ${errorText}`);
  }

  return response.json();
}

/**
 * Get drift propagation path for a table
 */
export async function getDriftPath(
  table: string,
  schema?: string
): Promise<DriftPathResponse> {
  const queryParams = new URLSearchParams();
  queryParams.append('table', table);
  
  if (schema) {
    queryParams.append('schema', schema);
  }

  const url = `${API_URL}/api/lineage/drift-path?${queryParams.toString()}`;
  const response = await fetch(url);

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API error: ${response.status} ${response.statusText} - ${errorText}`);
  }

  return response.json();
}

/**
 * Get lineage graph with filters
 */
export async function getLineageGraphWithFilters(
  params: GetLineageGraphParams & LineageFilters
): Promise<LineageGraphResponse> {
  return getLineageGraph(params);
}

/**
 * Get impact analysis for a table
 */
export async function getLineageImpact(
  table: string,
  schema?: string,
  includeMetrics: boolean = true
): Promise<LineageImpactResponse> {
  const queryParams = new URLSearchParams();
  queryParams.append('table', table);
  
  if (schema) {
    queryParams.append('schema', schema);
  }
  queryParams.append('include_metrics', includeMetrics.toString());

  const url = `${API_URL}/api/lineage/impact?${queryParams.toString()}`;
  const response = await fetch(url);

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API error: ${response.status} ${response.statusText} - ${errorText}`);
  }

  return response.json();
}







