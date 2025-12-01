/**
 * TypeScript types for lineage visualization
 */

export interface LineageNode {
  id: string;
  type: 'table' | 'column';
  label: string;
  schema?: string;
  table?: string;
  column?: string;
  database?: string;
  metadata: Record<string, any>;
  metrics?: Record<string, number>;
}

export interface LineageEdge {
  source: string;
  target: string;
  relationship_type: string;
  confidence: number;
  transformation?: string;
  provider: string;
  metadata: Record<string, any>;
}

export interface LineageGraphResponse {
  nodes: LineageNode[];
  edges: LineageEdge[];
  root_id?: string;
  direction: string;
}

export interface NodeDetailsResponse {
  id: string;
  type: string;
  label: string;
  schema?: string;
  table?: string;
  column?: string;
  upstream_count: number;
  downstream_count: number;
  providers: string[];
  metadata?: Record<string, any>;
}

export interface TableInfoResponse {
  schema: string;
  table: string;
  database?: string;
}

export interface DriftPathResponse {
  table: string;
  schema?: string;
  has_drift: boolean;
  drift_severity?: string;
  affected_downstream: TableInfoResponse[];
  lineage_path: LineageGraphResponse;
}
