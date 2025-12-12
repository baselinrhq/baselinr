/**
 * Type definitions for Root Cause Analysis (RCA)
 */

export interface ProbableCause {
  cause_type: string
  cause_id: string
  confidence_score: number
  description: string
  affected_assets: string[]
  suggested_action?: string | null
  evidence: Record<string, unknown>
}

export interface ImpactAnalysis {
  upstream_affected: string[]
  downstream_affected: string[]
  blast_radius_score: number
}

export interface RCAResult {
  anomaly_id: string
  table_name: string
  schema_name?: string | null
  column_name?: string | null
  metric_name?: string | null
  analyzed_at: string
  rca_status: 'analyzed' | 'pending' | 'dismissed'
  probable_causes: ProbableCause[]
  impact_analysis?: ImpactAnalysis | null
  metadata: Record<string, unknown>
}

export interface RCAListItem {
  anomaly_id: string
  table_name: string
  schema_name?: string | null
  column_name?: string | null
  metric_name?: string | null
  analyzed_at: string
  rca_status: 'analyzed' | 'pending' | 'dismissed'
  num_causes: number
  top_cause?: {
    cause_type: string
    confidence_score: number
    description: string
  } | null
}

export interface RCAStatistics {
  total_analyses: number
  analyzed: number
  dismissed: number
  pending: number
  avg_causes_per_anomaly: number
}

export interface PipelineRun {
  run_id: string
  pipeline_name: string
  pipeline_type: string
  started_at: string
  completed_at?: string | null
  duration_seconds?: number | null
  status: string
  input_row_count?: number | null
  output_row_count?: number | null
  git_commit_sha?: string | null
  git_branch?: string | null
  affected_tables: string[]
}

export interface CodeDeployment {
  deployment_id: string
  deployed_at: string
  git_commit_sha?: string | null
  git_branch?: string | null
  changed_files: string[]
  deployment_type: string
  affected_pipelines: string[]
}

export interface EventTimelineItem {
  timestamp: string
  event_type: 'anomaly' | 'pipeline_run' | 'code_deployment'
  event_data: Record<string, unknown>
  relevance_score: number
}

export interface AnalyzeRequest {
  anomaly_id: string
  table_name: string
  anomaly_timestamp: string
  schema_name?: string | null
  column_name?: string | null
  metric_name?: string | null
  anomaly_type?: string | null
}

export interface RCAFilters {
  status?: 'analyzed' | 'pending' | 'dismissed'
  table?: string
  schema?: string
  days?: number
  start_date?: string
  end_date?: string
}

