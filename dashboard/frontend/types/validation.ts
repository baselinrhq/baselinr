/**
 * Type definitions for validation dashboard
 */

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

export interface ValidationResult {
  id: number;
  run_id: string;
  table_name: string;
  schema_name?: string;
  column_name?: string;
  rule_type: string;
  passed: boolean;
  failure_reason?: string;
  total_rows?: number;
  failed_rows?: number;
  failure_rate?: number;
  severity?: string;
  validated_at: string;
}

export interface ValidationResultDetails extends ValidationResult {
  rule_config?: Record<string, unknown>;
  run_info?: Record<string, unknown>;
  historical_results: ValidationResult[];
}

export interface ValidationFailureSamples {
  result_id: number;
  total_failures: number;
  sample_failures: Array<Record<string, unknown>>;
  failure_patterns?: Record<string, unknown>;
}

export interface ValidationTrend {
  timestamp: string;
  value: number;
}

export interface ValidationFilters {
  days?: number;
  warehouse?: string;
  table?: string;
  schema?: string;
  rule_type?: string;
  severity?: string;
  passed?: boolean;
  start_date?: string;
  end_date?: string;
}

