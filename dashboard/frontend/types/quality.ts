/**
 * Type definitions for quality scores API
 */

export type QualityStatus = 'healthy' | 'warning' | 'critical'
export type QualityTrend = 'improving' | 'degrading' | 'stable'

export interface ScoreComponents {
  completeness: number
  validity: number
  consistency: number
  freshness: number
  uniqueness: number
  accuracy: number
}

export interface QualityIssues {
  total: number
  critical: number
  warnings: number
}

export interface QualityScore {
  table_name: string
  schema_name?: string | null
  overall_score: number
  status: QualityStatus
  trend?: QualityTrend | null
  trend_percentage?: number | null
  components: ScoreComponents
  issues: QualityIssues
  calculated_at: string
  run_id?: string | null
}

export interface QualityScoresListResponse {
  scores: QualityScore[]
  total: number
}

export interface ScoreHistoryResponse {
  scores: QualityScore[]
  total: number
}

export interface SchemaScoreResponse {
  schema_name: string
  overall_score: number
  status: QualityStatus
  table_count: number
  healthy_count: number
  warning_count: number
  critical_count: number
  tables: QualityScore[]
}

export interface SystemScoreResponse {
  overall_score: number
  status: QualityStatus
  total_tables: number
  healthy_count: number
  warning_count: number
  critical_count: number
}

export interface ColumnQualityScore {
  table_name: string
  schema_name?: string | null
  column_name: string
  overall_score: number
  status: QualityStatus
  components: ScoreComponents
  calculated_at: string
  run_id?: string | null
  period_start: string
  period_end: string
}

export interface ColumnScoresListResponse {
  scores: ColumnQualityScore[]
  total: number
}

export interface TrendAnalysis {
  direction: QualityTrend
  rate_of_change: number
  confidence: number
  periods_analyzed: number
  overall_change: number
}

export interface ScoreComparison {
  tables: QualityScore[]
  comparison_metrics: {
    best_performer: string
    worst_performer: string
    average_score: number
    score_range: {
      min: number
      max: number
    }
  }
}

