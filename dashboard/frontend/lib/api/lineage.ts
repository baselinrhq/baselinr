/**
 * API client for lineage visualization endpoints
 */

import {
  LineageGraphResponse,
  NodeDetailsResponse,
  TableInfoResponse,
  DriftPathResponse,
} from '@/types/lineage';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface GetLineageGraphParams {
  table: string;
  schema?: string;
  column?: string;
  direction?: 'upstream' | 'downstream' | 'both';
  depth?: number;
  confidenceThreshold?: number;
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
  const response = await fetch(url);

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API error: ${response.status} ${response.statusText} - ${errorText}`);
  }

  return response.json();
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











