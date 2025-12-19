/**
 * API client for validation rules endpoints
 */

import type {
  ValidationRule,
  ValidationRulesListResponse,
  CreateValidationRuleRequest,
  UpdateValidationRuleRequest,
  TestValidationRuleResponse,
  ValidationRulesFilters,
} from '@/types/validationRules'
import { getApiUrl } from '../demo-mode'

const API_URL = getApiUrl()

export class ValidationRulesError extends Error {
  constructor(message: string, public statusCode?: number) {
    super(message)
    this.name = 'ValidationRulesError'
  }
}

/**
 * List validation rules with optional filters
 */
export async function listValidationRules(
  filters?: ValidationRulesFilters
): Promise<ValidationRulesListResponse> {
  const params = new URLSearchParams()
  if (filters?.table) params.append('table', filters.table)
  if (filters?.schema) params.append('schema', filters.schema)
  if (filters?.rule_type) params.append('rule_type', filters.rule_type)
  if (filters?.enabled !== undefined) params.append('enabled', filters.enabled.toString())

  const url = `${API_URL}/api/validation/rules${params.toString() ? `?${params.toString()}` : ''}`
  const response = await fetch(url)

  if (!response.ok) {
    const errorText = await response.text()
    throw new ValidationRulesError(
      `API error: ${response.status} ${response.statusText} - ${errorText}`,
      response.status
    )
  }

  return response.json()
}

/**
 * Get a specific validation rule by ID
 */
export async function getValidationRule(ruleId: string): Promise<ValidationRule> {
  const url = `${API_URL}/api/validation/rules/${ruleId}`
  const response = await fetch(url)

  if (!response.ok) {
    const errorText = await response.text()
    throw new ValidationRulesError(
      `API error: ${response.status} ${response.statusText} - ${errorText}`,
      response.status
    )
  }

  return response.json()
}

/**
 * Create a new validation rule
 */
export async function createValidationRule(
  request: CreateValidationRuleRequest
): Promise<ValidationRule> {
  const url = `${API_URL}/api/validation/rules`
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new ValidationRulesError(
      `API error: ${response.status} ${response.statusText} - ${errorText}`,
      response.status
    )
  }

  return response.json()
}

/**
 * Update an existing validation rule
 */
export async function updateValidationRule(
  ruleId: string,
  request: UpdateValidationRuleRequest
): Promise<ValidationRule> {
  const url = `${API_URL}/api/validation/rules/${ruleId}`
  const response = await fetch(url, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new ValidationRulesError(
      `API error: ${response.status} ${response.statusText} - ${errorText}`,
      response.status
    )
  }

  return response.json()
}

/**
 * Delete a validation rule
 */
export async function deleteValidationRule(ruleId: string): Promise<void> {
  const url = `${API_URL}/api/validation/rules/${ruleId}`
  const response = await fetch(url, {
    method: 'DELETE',
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new ValidationRulesError(
      `API error: ${response.status} ${response.statusText} - ${errorText}`,
      response.status
    )
  }
}

/**
 * Test a validation rule
 */
export async function testValidationRule(ruleId: string): Promise<TestValidationRuleResponse> {
  const url = `${API_URL}/api/validation/rules/${ruleId}/test`
  const response = await fetch(url, {
    method: 'POST',
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new ValidationRulesError(
      `API error: ${response.status} ${response.statusText} - ${errorText}`,
      response.status
    )
  }

  return response.json()
}

