/**
 * Unit tests for recommendations API client
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  fetchRecommendations,
  fetchColumnRecommendations,
  applyRecommendations,
  refreshRecommendations,
} from '@/lib/api/recommendations'
import type {
  RecommendationReport,
  ColumnCheckRecommendation,
  ApplyRecommendationsRequest,
} from '@/types/recommendation'

// Mock fetch globally
global.fetch = vi.fn()

describe('recommendations API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('fetchRecommendations', () => {
    it('should fetch recommendations successfully', async () => {
      const mockResponse: RecommendationReport = {
        generated_at: '2024-01-01T00:00:00Z',
        lookback_days: 30,
        database_type: 'postgres',
        recommended_tables: [
          {
            schema: 'public',
            table: 'users',
            confidence: 0.85,
            score: 0.9,
            reasons: ['High query frequency'],
            warnings: [],
            suggested_checks: ['completeness'],
            column_recommendations: [],
            low_confidence_columns: [],
            query_count: 100,
            queries_per_day: 10.0,
            row_count: 1000,
            column_count: 5,
            lineage_score: 0.0,
          },
        ],
        excluded_tables: [],
        total_tables_analyzed: 10,
        total_recommended: 1,
        total_excluded: 0,
        confidence_distribution: {},
        total_columns_analyzed: 0,
        total_column_checks_recommended: 0,
        column_confidence_distribution: {},
        low_confidence_suggestions: [],
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await fetchRecommendations({
        connection_id: 'test-conn',
        schema: 'public',
        include_columns: false,
      })

      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/recommendations?connection_id=test-conn&schema=public')
      )
    })

    it('should handle API errors', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        text: async () => 'Connection not found',
      } as Response)

      await expect(
        fetchRecommendations({
          connection_id: 'invalid',
        })
      ).rejects.toThrow('API error')
    })
  })

  describe('fetchColumnRecommendations', () => {
    it('should fetch column recommendations successfully', async () => {
      const mockResponse: ColumnCheckRecommendation[] = [
        {
          column: 'email',
          data_type: 'varchar',
          confidence: 0.9,
          signals: ['Column name pattern'],
          suggested_checks: [{ type: 'format_email' }],
        },
      ]

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await fetchColumnRecommendations({
        connection_id: 'test-conn',
        table: 'users',
        schema: 'public',
      })

      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/recommendations/columns?connection_id=test-conn&table=users&schema=public')
      )
    })

    it('should handle errors', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        text: async () => 'Server error',
      } as Response)

      await expect(
        fetchColumnRecommendations({
          connection_id: 'test-conn',
          table: 'users',
        })
      ).rejects.toThrow('API error')
    })
  })

  describe('applyRecommendations', () => {
    it('should apply recommendations successfully', async () => {
      const mockRequest: ApplyRecommendationsRequest = {
        connection_id: 'test-conn',
        selected_tables: [
          { schema: 'public', table: 'users' },
        ],
        comment: 'Applied from UI',
      }

      const mockResponse = {
        success: true,
        applied_tables: [
          {
            schema: 'public',
            table: 'users',
            database: null,
            column_checks_applied: 0,
          },
        ],
        total_tables_applied: 1,
        total_column_checks_applied: 0,
        message: 'Successfully applied 1 table(s)',
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await applyRecommendations(mockRequest)

      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/recommendations/apply'),
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(mockRequest),
        })
      )
    })

    it('should handle errors', async () => {
      const mockRequest: ApplyRecommendationsRequest = {
        connection_id: 'test-conn',
        selected_tables: [],
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        text: async () => 'No tables selected',
      } as Response)

      await expect(applyRecommendations(mockRequest)).rejects.toThrow('API error')
    })
  })

  describe('refreshRecommendations', () => {
    it('should refresh recommendations successfully', async () => {
      const mockResponse: RecommendationReport = {
        generated_at: '2024-01-01T00:00:00Z',
        lookback_days: 30,
        database_type: 'postgres',
        recommended_tables: [],
        excluded_tables: [],
        total_tables_analyzed: 10,
        total_recommended: 0,
        total_excluded: 0,
        confidence_distribution: {},
        total_columns_analyzed: 0,
        total_column_checks_recommended: 0,
        column_confidence_distribution: {},
        low_confidence_suggestions: [],
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await refreshRecommendations({
        connection_id: 'test-conn',
        refresh: true,
      })

      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/recommendations/refresh'),
        expect.objectContaining({
          method: 'POST',
        })
      )
    })
  })
})


