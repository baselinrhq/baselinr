/**
 * Type definitions for drift detection and analysis
 */

export interface DriftAlert {
  event_id: string;
  run_id: string;
  table_name: string;
  column_name?: string | null;
  metric_name: string;
  baseline_value?: number | null;
  current_value?: number | null;
  change_percent?: number | null;
  change_percentage?: number | null;
  severity: 'low' | 'medium' | 'high';
  timestamp: string;
  detected_at?: string;
  warehouse_type: string;
  warehouse?: string;
  schema?: string;
  drift_type?: string;
  message?: string;
}

export interface DriftTrend {
  timestamp: string;
  value: number;
}

export interface TopAffectedTable {
  table_name: string;
  drift_count: number;
  severity_breakdown: {
    low: number;
    medium: number;
    high: number;
  };
}

export interface DriftSummary {
  total_events: number;
  by_severity: {
    low: number;
    medium: number;
    high: number;
  };
  trending: DriftTrend[];
  top_affected_tables: TopAffectedTable[];
  warehouse_breakdown: Record<string, number>;
  recent_activity: DriftAlert[];
}

export interface StatisticalTestResult {
  test_name: string;
  result: string;
  p_value?: number;
  statistic?: number;
  significant?: boolean;
  interpretation?: string;
}

export interface HistoricalValue {
  timestamp: string;
  value: number | null;
}

export interface DriftDetails {
  event: DriftAlert;
  baseline_metrics: Record<string, unknown>;
  current_metrics: Record<string, unknown>;
  statistical_tests?: StatisticalTestResult[];
  historical_values: HistoricalValue[];
  related_events: DriftAlert[];
}

export interface DriftImpact {
  event_id: string;
  affected_tables: string[];
  affected_metrics: number;
  impact_score: number;
  recommendations: string[];
}

export interface DriftFilters {
  warehouse?: string;
  table?: string;
  severity?: string | string[];
  days?: number;
  start_date?: string;
  end_date?: string;
  metric_name?: string;
  column_name?: string;
}

