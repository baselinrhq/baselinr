/**
 * API client for validation operations
 */

import { ValidationRuleConfig } from '@/types/config'
import { getTablePreview } from './tables'

/**
 * Test rule result
 */
export interface RuleTestResult {
  passed: boolean
  failures: Array<{
    row: Record<string, unknown>
    reason: string
  }>
  sample_size: number
  passed_count: number
  failed_count: number
}

/**
 * Sample data response
 */
export interface SampleDataResponse {
  rows: Record<string, unknown>[]
  total: number
}

/**
 * Test a validation rule on sample data
 */
export async function testRule(
  rule: ValidationRuleConfig,
  connectionId?: string,
  sampleSize: number = 10
): Promise<RuleTestResult> {
  if (!rule.table || !rule.column) {
    throw new Error('Table and column are required for rule testing')
  }

  try {
    // For now, we'll use a simple frontend validation approach
    // In Plan 25, this can be replaced with a backend endpoint
    const sampleData = await getSampleData(
      rule.table,
      rule.column,
      sampleSize,
      connectionId
    )

    const failures: Array<{ row: Record<string, unknown>; reason: string }> = []
    let passedCount = 0
    let failedCount = 0

    for (const row of sampleData.rows) {
      const value = row[rule.column!]
      const result = validateRuleValue(rule, value)
      
      if (!result.passed) {
        failures.push({
          row,
          reason: result.reason || 'Validation failed',
        })
        failedCount++
      } else {
        passedCount++
      }
    }

    return {
      passed: failures.length === 0,
      failures,
      sample_size: sampleData.rows.length,
      passed_count: passedCount,
      failed_count: failedCount,
    }
  } catch (error) {
    throw new Error(
      `Failed to test rule: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Get sample data from a table column
 * Note: This is a placeholder. In Plan 25, this should use a dedicated sample data endpoint.
 * @param _limit - Sample size limit (currently unused, reserved for future implementation)
 */
export async function getSampleData(
  table: string,
  column: string,
  _limit: number = 10, // eslint-disable-line @typescript-eslint/no-unused-vars
  connectionId?: string
): Promise<SampleDataResponse> {
  // Parse table name (could be schema.table)
  const parts = table.split('.')
  const schema = parts.length > 1 ? parts[0] : 'public'
  const tableName = parts.length > 1 ? parts[1] : parts[0]

  try {
    // Get table metadata first to validate table exists
    await getTablePreview(schema, tableName, connectionId)
    
    // For now, return empty rows since we don't have a sample data endpoint
    // In Plan 25, this can be replaced with a proper endpoint
    // This is a placeholder that will work with the UI structure
    // The frontend validation will still work, but won't have actual data to test against
    return {
      rows: [],
      total: 0,
    }
  } catch (error) {
    throw new Error(
      `Failed to get sample data: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Validate a single value against a rule (frontend validation)
 */
function validateRuleValue(
  rule: ValidationRuleConfig,
  value: unknown
): { passed: boolean; reason?: string } {
  // Handle null values
  if (value === null || value === undefined) {
    if (rule.type === 'not_null') {
      return { passed: false, reason: 'Value is null' }
    }
    // For other rules, null might be acceptable depending on column nullable status
    // For now, we'll pass null values for non-not_null rules
    return { passed: true }
  }

  switch (rule.type) {
    case 'format':
      if (!rule.pattern) {
        return { passed: false, reason: 'Pattern is required for format validation' }
      }
      const strValue = String(value)
      // Check for predefined patterns
      if (rule.pattern === 'email') {
        const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
        if (!emailRegex.test(strValue)) {
          return { passed: false, reason: 'Value does not match email format' }
        }
      } else if (rule.pattern === 'url') {
        try {
          new URL(strValue)
        } catch {
          return { passed: false, reason: 'Value does not match URL format' }
        }
      } else if (rule.pattern === 'phone') {
        const phoneRegex = /^\+?[\d\s\-()]+$/
        if (!phoneRegex.test(strValue)) {
          return { passed: false, reason: 'Value does not match phone format' }
        }
      } else {
        // Custom regex
        try {
          const regex = new RegExp(rule.pattern)
          if (!regex.test(strValue)) {
            return { passed: false, reason: `Value does not match pattern: ${rule.pattern}` }
          }
        } catch {
          return { passed: false, reason: `Invalid regex pattern: ${rule.pattern}` }
        }
      }
      return { passed: true }

    case 'range':
      const numValue = Number(value)
      if (isNaN(numValue)) {
        return { passed: false, reason: 'Value is not a number' }
      }
      if (rule.min_value !== null && rule.min_value !== undefined && numValue < rule.min_value) {
        return { passed: false, reason: `Value ${numValue} is less than minimum ${rule.min_value}` }
      }
      if (rule.max_value !== null && rule.max_value !== undefined && numValue > rule.max_value) {
        return { passed: false, reason: `Value ${numValue} is greater than maximum ${rule.max_value}` }
      }
      return { passed: true }

    case 'enum':
      if (!rule.allowed_values || rule.allowed_values.length === 0) {
        return { passed: false, reason: 'Allowed values are required for enum validation' }
      }
      if (!rule.allowed_values.includes(value)) {
        return {
          passed: false,
          reason: `Value "${value}" is not in allowed values: ${rule.allowed_values.join(', ')}`,
        }
      }
      return { passed: true }

    case 'not_null':
      if (value === null || value === undefined || value === '') {
        return { passed: false, reason: 'Value is null or empty' }
      }
      return { passed: true }

    case 'unique':
      // Uniqueness can't be validated on a single value
      // This would need to check against all other values in the column
      // For now, we'll just return passed
      return { passed: true }

    case 'referential':
      // Referential integrity can't be validated on a single value
      // This would need to check against the referenced table
      // For now, we'll just return passed
      return { passed: true }

    default:
      return { passed: false, reason: `Unknown rule type: ${rule.type}` }
  }
}

