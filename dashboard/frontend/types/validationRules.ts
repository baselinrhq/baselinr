/**
 * Type definitions for validation rules API
 */

export type ValidationRuleType = 'format' | 'range' | 'enum' | 'not_null' | 'unique' | 'referential'
export type ValidationSeverity = 'low' | 'medium' | 'high'

export interface ValidationRule {
  id: string
  rule_type: ValidationRuleType
  table: string
  schema?: string | null
  column?: string | null
  config: Record<string, unknown>
  severity: ValidationSeverity
  enabled: boolean
  created_at: string
  updated_at?: string | null
  last_tested?: string | null
  last_test_result?: boolean | null
}

export interface ValidationRulesListResponse {
  rules: ValidationRule[]
  total: number
}

export interface CreateValidationRuleRequest {
  rule_type: ValidationRuleType
  table: string
  schema?: string | null
  column?: string | null
  config: Record<string, unknown>
  severity?: ValidationSeverity
  enabled?: boolean
}

export interface UpdateValidationRuleRequest {
  rule_type?: ValidationRuleType
  table?: string
  schema?: string | null
  column?: string | null
  config?: Record<string, unknown>
  severity?: ValidationSeverity
  enabled?: boolean
}

export interface TestValidationRuleResponse {
  rule_id: string
  passed: boolean
  failure_reason?: string | null
  total_rows: number
  failed_rows: number
  failure_rate: number
  sample_failures: Array<Record<string, unknown>>
  tested_at: string
}

export interface ValidationRulesFilters {
  table?: string
  schema?: string
  rule_type?: ValidationRuleType
  enabled?: boolean
}

