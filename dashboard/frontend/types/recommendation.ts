/**
 * TypeScript types for recommendation API responses
 */

export interface ColumnCheckRecommendation {
  column: string
  data_type: string
  confidence: number
  signals: string[]
  suggested_checks: Array<Record<string, unknown>>
}

export interface TableRecommendation {
  schema: string
  table: string
  database?: string | null
  confidence: number
  score: number
  reasons: string[]
  warnings: string[]
  suggested_checks: string[]
  column_recommendations: ColumnCheckRecommendation[]
  low_confidence_columns: ColumnCheckRecommendation[]
  query_count: number
  queries_per_day: number
  row_count?: number | null
  last_query_days_ago?: number | null
  column_count: number
  lineage_score: number
  lineage_context?: Record<string, unknown> | null
}

export interface ExcludedTable {
  schema: string
  table: string
  database?: string | null
  reasons: string[]
}

export interface RecommendationReport {
  generated_at: string
  lookback_days: number
  database_type: string
  recommended_tables: TableRecommendation[]
  excluded_tables: ExcludedTable[]
  total_tables_analyzed: number
  total_recommended: number
  total_excluded: number
  confidence_distribution: Record<string, number>
  total_columns_analyzed: number
  total_column_checks_recommended: number
  column_confidence_distribution: Record<string, number>
  low_confidence_suggestions: Array<Record<string, unknown>>
}

export interface ApplyRecommendationsRequest {
  connection_id: string
  selected_tables: Array<{
    schema?: string
    table: string
    database?: string
  }>
  column_checks?: Record<string, string[]>
  comment?: string
}

export interface AppliedTable {
  schema: string
  table: string
  database?: string | null
  column_checks_applied: number
}

export interface ApplyRecommendationsResponse {
  success: boolean
  applied_tables: AppliedTable[]
  total_tables_applied: number
  total_column_checks_applied: number
  message: string
}


