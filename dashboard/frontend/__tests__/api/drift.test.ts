import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchDriftSummary, fetchDriftDetails, fetchDriftImpact } from '@/lib/api'

// Mock fetch globally
global.fetch = vi.fn()

describe('Drift API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('fetchDriftSummary', () => {
    it('fetches drift summary successfully', async () => {
      const mockSummary = {
        total_events: 10,
        by_severity: { low: 5, medium: 3, high: 2 },
        trending: [],
        top_affected_tables: [],
        warehouse_breakdown: {},
        recent_activity: [],
      }

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockSummary,
      } as Response)

      const result = await fetchDriftSummary({ days: 30 })
      expect(result).toEqual(mockSummary)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/drift/summary')
      )
    })

    it('handles API errors', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      } as Response)

      await expect(fetchDriftSummary()).rejects.toThrow('API error')
    })

    it('includes query parameters', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      } as Response)

      await fetchDriftSummary({ days: 7, warehouse: 'postgres' })
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('days=7')
      )
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('warehouse=postgres')
      )
    })
  })

  describe('fetchDriftDetails', () => {
    it('fetches drift details successfully', async () => {
      const mockDetails = {
        event: {
          event_id: 'event1',
          table_name: 'customers',
        },
        baseline_metrics: {},
        current_metrics: {},
        historical_values: [],
        related_events: [],
      }

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockDetails,
      } as Response)

      const result = await fetchDriftDetails('event1')
      expect(result).toEqual(mockDetails)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/drift/event1/details')
      )
    })

    it('handles API errors', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
      } as Response)

      await expect(fetchDriftDetails('nonexistent')).rejects.toThrow('API error')
    })
  })

  describe('fetchDriftImpact', () => {
    it('fetches drift impact successfully', async () => {
      const mockImpact = {
        event_id: 'event1',
        affected_tables: [],
        affected_metrics: 1,
        impact_score: 0.8,
        recommendations: [],
      }

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockImpact,
      } as Response)

      const result = await fetchDriftImpact('event1')
      expect(result).toEqual(mockImpact)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/drift/event1/impact')
      )
    })

    it('handles API errors', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      } as Response)

      await expect(fetchDriftImpact('event1')).rejects.toThrow('API error')
    })
  })
})

