/**
 * Tests for validation rules API client
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  listValidationRules,
  getValidationRule,
  createValidationRule,
  updateValidationRule,
  deleteValidationRule,
  testValidationRule,
  ValidationRulesError,
} from '@/lib/api/validationRules'
import type {
  ValidationRule,
  CreateValidationRuleRequest,
  UpdateValidationRuleRequest,
} from '@/types/validationRules'

// Mock fetch globally
global.fetch = vi.fn()

describe('validationRules API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listValidationRules', () => {
    it('should list validation rules without filters', async () => {
      const mockRules = {
        rules: [
          {
            id: 'rule-1',
            rule_type: 'format',
            table: 'users',
            schema: 'public',
            column: 'email',
            config: { pattern: 'email' },
            severity: 'high',
            enabled: true,
            created_at: '2024-01-01T00:00:00Z',
            updated_at: null,
            last_tested: null,
            last_test_result: null,
          },
        ],
        total: 1,
      }

      ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockRules,
      })

      const result = await listValidationRules()

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/validation/rules')
      )
      expect(result).toEqual(mockRules)
    })

    it('should list validation rules with filters', async () => {
      const mockRules = { rules: [], total: 0 }

      ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockRules,
      })

      await listValidationRules({
        table: 'users',
        rule_type: 'format',
        enabled: true,
      })

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('table=users')
      )
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('rule_type=format')
      )
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('enabled=true')
      )
    })

    it('should throw ValidationRulesError on API error', async () => {
      ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        text: async () => 'Server error',
      })

      await expect(listValidationRules()).rejects.toThrow(ValidationRulesError)
    })
  })

  describe('getValidationRule', () => {
    it('should get a specific validation rule', async () => {
      const mockRule: ValidationRule = {
        id: 'rule-1',
        rule_type: 'format',
        table: 'users',
        schema: 'public',
        column: 'email',
        config: { pattern: 'email' },
        severity: 'high',
        enabled: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: null,
        last_tested: null,
        last_test_result: null,
      }

      ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockRule,
      })

      const result = await getValidationRule('rule-1')

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/validation/rules/rule-1')
      )
      expect(result).toEqual(mockRule)
    })

    it('should throw ValidationRulesError on 404', async () => {
      ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        text: async () => 'Rule not found',
      })

      await expect(getValidationRule('nonexistent')).rejects.toThrow(ValidationRulesError)
    })
  })

  describe('createValidationRule', () => {
    it('should create a new validation rule', async () => {
      const request: CreateValidationRuleRequest = {
        rule_type: 'format',
        table: 'users',
        schema: 'public',
        column: 'email',
        config: { pattern: 'email' },
        severity: 'high',
        enabled: true,
      }

      const mockRule: ValidationRule = {
        id: 'rule-1',
        ...request,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: null,
        last_tested: null,
        last_test_result: null,
      }

      ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockRule,
      })

      const result = await createValidationRule(request)

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/validation/rules'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(request),
        })
      )
      expect(result).toEqual(mockRule)
    })
  })

  describe('updateValidationRule', () => {
    it('should update an existing validation rule', async () => {
      const request: UpdateValidationRuleRequest = {
        severity: 'medium',
        enabled: false,
      }

      const mockRule: ValidationRule = {
        id: 'rule-1',
        rule_type: 'format',
        table: 'users',
        schema: 'public',
        column: 'email',
        config: { pattern: 'email' },
        severity: 'medium',
        enabled: false,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-02T00:00:00Z',
        last_tested: null,
        last_test_result: null,
      }

      ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockRule,
      })

      const result = await updateValidationRule('rule-1', request)

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/validation/rules/rule-1'),
        expect.objectContaining({
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(request),
        })
      )
      expect(result).toEqual(mockRule)
    })
  })

  describe('deleteValidationRule', () => {
    it('should delete a validation rule', async () => {
      ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
      })

      await deleteValidationRule('rule-1')

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/validation/rules/rule-1'),
        expect.objectContaining({
          method: 'DELETE',
        })
      )
    })
  })

  describe('testValidationRule', () => {
    it('should test a validation rule', async () => {
      const mockTestResult = {
        rule_id: 'rule-1',
        passed: true,
        failure_reason: null,
        total_rows: 100,
        failed_rows: 0,
        failure_rate: 0.0,
        sample_failures: [],
        tested_at: '2024-01-01T00:00:00Z',
      }

      ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockTestResult,
      })

      const result = await testValidationRule('rule-1')

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/validation/rules/rule-1/test'),
        expect.objectContaining({
          method: 'POST',
        })
      )
      expect(result).toEqual(mockTestResult)
    })
  })
})

