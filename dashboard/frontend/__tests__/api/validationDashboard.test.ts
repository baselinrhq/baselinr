import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  fetchValidationSummary,
  fetchValidationResults,
  fetchValidationResultDetails,
  fetchValidationFailureSamples,
} from '@/lib/api'

// Mock fetch globally
global.fetch = vi.fn()

describe('Validation Dashboard API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('fetchValidationSummary', () => {
    it('fetches validation summary successfully', async () => {
      const mockSummary = {
        total_validations: 100,
        passed_count: 85,
        failed_count: 15,
        pass_rate: 85.0,
        by_rule_type: { format: 30, range: 40, enum: 30 },
        by_severity: { low: 5, medium: 7, high: 3 },
        by_table: { users: 20, orders: 30, products: 50 },
        trending: [
          { timestamp: '2024-01-01T00:00:00Z', value: 80.0 },
          { timestamp: '2024-01-02T00:00:00Z', value: 85.0 },
        ],
        recent_runs: [
          {
            run_id: 'run1',
            validated_at: '2024-01-02T00:00:00Z',
            total: 50,
            passed: 45,
            failed: 5,
          },
        ],
      }

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockSummary,
      } as Response)

      const result = await fetchValidationSummary({ days: 30 })
      expect(result).toEqual(mockSummary)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/validation/summary')
      )
    })

    it('handles API errors', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      } as Response)

      await expect(fetchValidationSummary()).rejects.toThrow('API error')
    })

    it('includes query parameters', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      } as Response)

      await fetchValidationSummary({ days: 7, warehouse: 'postgres' })
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('days=7')
      )
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('warehouse=postgres')
      )
    })
  })

  describe('fetchValidationResults', () => {
    it('fetches validation results successfully', async () => {
      const mockResults = {
        results: [
          {
            id: 1,
            run_id: 'run1',
            table_name: 'users',
            schema_name: 'public',
            column_name: 'email',
            rule_type: 'format',
            passed: false,
            failure_reason: 'Invalid format',
            total_rows: 1000,
            failed_rows: 5,
            failure_rate: 0.5,
            severity: 'high',
            validated_at: '2024-01-02T00:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        page_size: 50,
      }

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResults,
      } as Response)

      const result = await fetchValidationResults({ page: 1, page_size: 50 })
      expect(result).toEqual(mockResults)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/validation/results')
      )
    })

    it('includes filter parameters', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ results: [], total: 0, page: 1, page_size: 50 }),
      } as Response)

      await fetchValidationResults({
        table: 'users',
        schema: 'public',
        rule_type: 'format',
        severity: 'high',
        passed: false,
        page: 1,
      })

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('table=users')
      )
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('schema=public')
      )
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('rule_type=format')
      )
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('severity=high')
      )
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('passed=false')
      )
    })

    it('handles API errors', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      } as Response)

      await expect(fetchValidationResults()).rejects.toThrow('API error')
    })
  })

  describe('fetchValidationResultDetails', () => {
    it('fetches validation result details successfully', async () => {
      const mockDetails = {
        result: {
          id: 1,
          run_id: 'run1',
          table_name: 'users',
          schema_name: 'public',
          column_name: 'email',
          rule_type: 'format',
          passed: false,
          failure_reason: 'Invalid format',
          total_rows: 1000,
          failed_rows: 5,
          failure_rate: 0.5,
          severity: 'high',
          validated_at: '2024-01-02T00:00:00Z',
        },
        rule_config: { pattern: 'email' },
        run_info: { run_id: 'run1', dataset_name: 'users' },
        historical_results: [],
      }

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockDetails,
      } as Response)

      const result = await fetchValidationResultDetails(1)
      expect(result).toEqual(mockDetails)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/validation/results/1')
      )
    })

    it('handles API errors', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
      } as Response)

      await expect(fetchValidationResultDetails(999)).rejects.toThrow('API error')
    })
  })

  describe('fetchValidationFailureSamples', () => {
    it('fetches failure samples successfully', async () => {
      const mockSamples = {
        result_id: 1,
        total_failures: 5,
        sample_failures: [
          { row_id: 1, email: 'invalid-email', failure_reason: 'Invalid format' },
          { row_id: 2, email: 'bad@', failure_reason: 'Invalid format' },
        ],
        failure_patterns: { common_pattern: 'missing @ symbol' },
      }

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockSamples,
      } as Response)

      const result = await fetchValidationFailureSamples(1)
      expect(result).toEqual(mockSamples)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/validation/results/1/failures')
      )
    })

    it('handles API errors', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
      } as Response)

      await expect(fetchValidationFailureSamples(999)).rejects.toThrow('API error')
    })
  })
})

