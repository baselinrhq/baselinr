/**
 * Unit tests for validation API client
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { testRule, getSampleData } from '@/lib/api/validation'
import { ValidationRuleConfig } from '@/types/config'
import * as tablesApi from '@/lib/api/tables'

vi.mock('@/lib/api/tables')

describe('validation API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('testRule', () => {
    it('should test format rule successfully', async () => {
      const rule: ValidationRuleConfig = {
        type: 'format',
        table: 'users',
        column: 'email',
        pattern: 'email',
        severity: 'high',
        enabled: true,
      }

      vi.mocked(tablesApi.getTablePreview).mockResolvedValue({
        schema: 'public',
        table: 'users',
        columns: [{ name: 'email', type: 'VARCHAR', nullable: false }],
        row_count: 10,
        table_type: 'table',
      })

      // Since getSampleData returns empty rows, the test will pass
      const result = await testRule(rule)

      expect(result).toHaveProperty('passed')
      expect(result).toHaveProperty('failures')
      expect(result).toHaveProperty('sample_size')
    })

    it('should test range rule', async () => {
      const rule: ValidationRuleConfig = {
        type: 'range',
        table: 'orders',
        column: 'total_amount',
        min_value: 0,
        max_value: 1000,
        severity: 'medium',
        enabled: true,
      }

      vi.mocked(tablesApi.getTablePreview).mockResolvedValue({
        schema: 'public',
        table: 'orders',
        columns: [{ name: 'total_amount', type: 'DECIMAL', nullable: false }],
        row_count: 10,
        table_type: 'table',
      })

      const result = await testRule(rule)

      expect(result).toHaveProperty('passed')
      expect(result).toHaveProperty('failures')
    })

    it('should test enum rule', async () => {
      const rule: ValidationRuleConfig = {
        type: 'enum',
        table: 'orders',
        column: 'status',
        allowed_values: ['pending', 'completed'],
        severity: 'high',
        enabled: true,
      }

      vi.mocked(tablesApi.getTablePreview).mockResolvedValue({
        schema: 'public',
        table: 'orders',
        columns: [{ name: 'status', type: 'VARCHAR', nullable: false }],
        row_count: 10,
        table_type: 'table',
      })

      const result = await testRule(rule)

      expect(result).toHaveProperty('passed')
      expect(result).toHaveProperty('failures')
    })

    it('should throw error if table or column missing', async () => {
      const rule: ValidationRuleConfig = {
        type: 'format',
        pattern: 'email',
        severity: 'high',
        enabled: true,
      }

      await expect(testRule(rule)).rejects.toThrow('Table and column are required')
    })
  })

  describe('getSampleData', () => {
    it('should get sample data', async () => {
      vi.mocked(tablesApi.getTablePreview).mockResolvedValue({
        schema: 'public',
        table: 'users',
        columns: [{ name: 'email', type: 'VARCHAR', nullable: false }],
        row_count: 10,
        table_type: 'table',
      })

      const result = await getSampleData('users', 'email', 10)

      expect(result).toHaveProperty('rows')
      expect(result).toHaveProperty('total')
      expect(tablesApi.getTablePreview).toHaveBeenCalledWith('public', 'users', undefined)
    })

    it('should parse schema.table format', async () => {
      vi.mocked(tablesApi.getTablePreview).mockResolvedValue({
        schema: 'custom',
        table: 'users',
        columns: [{ name: 'email', type: 'VARCHAR', nullable: false }],
        row_count: 10,
        table_type: 'table',
      })

      await getSampleData('custom.users', 'email', 10)

      expect(tablesApi.getTablePreview).toHaveBeenCalledWith('custom', 'users', undefined)
    })
  })
})

