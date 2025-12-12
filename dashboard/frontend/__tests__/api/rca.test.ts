/**
 * Unit tests for RCA API client
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  listRCAResults,
  getRCAResult,
  analyzeAnomaly,
  reanalyzeAnomaly,
  dismissRCAResult,
  getRCAStatistics,
  getRecentPipelineRuns,
  getRecentDeployments,
  getEventsTimeline,
  RCAError,
} from '@/lib/api/rca'
import type {
  RCAListItem,
  RCAResult,
  AnalyzeRequest,
  RCAStatistics,
  PipelineRun,
  CodeDeployment,
  EventTimelineItem,
} from '@/types/rca'

// Mock fetch globally
global.fetch = vi.fn()

describe('RCA API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listRCAResults', () => {
    it('should fetch RCA results successfully', async () => {
      const mockResponse: RCAListItem[] = [
        {
          anomaly_id: 'anom-1',
          table_name: 'users',
          schema_name: 'public',
          column_name: 'email',
          metric_name: 'null_percent',
          analyzed_at: '2024-01-01T00:00:00Z',
          rca_status: 'analyzed',
          num_causes: 2,
          top_cause: {
            cause_type: 'pipeline_failure',
            confidence_score: 0.85,
            description: 'Pipeline failed before anomaly',
          },
        },
      ]

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await listRCAResults({ status: 'analyzed', limit: 10 })

      expect(result).toEqual(mockResponse)
      const fetchCall = vi.mocked(fetch).mock.calls[0][0] as string
      expect(fetchCall).toContain('/api/rca')
      expect(fetchCall).toContain('status=analyzed')
      expect(fetchCall).toContain('limit=10')
    })

    it('should handle API errors', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        text: async () => 'Server error',
      } as Response)

      await expect(listRCAResults({})).rejects.toThrow(RCAError)
    })
  })

  describe('getRCAResult', () => {
    it('should fetch RCA result successfully', async () => {
      const mockResponse: RCAResult = {
        anomaly_id: 'anom-1',
        table_name: 'users',
        schema_name: 'public',
        column_name: 'email',
        metric_name: 'null_percent',
        analyzed_at: '2024-01-01T00:00:00Z',
        rca_status: 'analyzed',
        probable_causes: [
          {
            cause_type: 'pipeline_failure',
            cause_id: 'cause-1',
            confidence_score: 0.85,
            description: 'Pipeline failed',
            affected_assets: ['pipeline-1'],
            suggested_action: 'Check pipeline logs',
            evidence: {},
          },
        ],
        impact_analysis: {
          upstream_affected: [],
          downstream_affected: ['table-2'],
          blast_radius_score: 0.5,
        },
        metadata: {},
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await getRCAResult('anom-1')

      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/api/rca/anom-1'))
    })
  })

  describe('analyzeAnomaly', () => {
    it('should trigger analysis successfully', async () => {
      const mockRequest: AnalyzeRequest = {
        anomaly_id: 'anom-1',
        table_name: 'users',
        anomaly_timestamp: '2024-01-01T00:00:00Z',
      }

      const mockResponse: RCAResult = {
        anomaly_id: 'anom-1',
        table_name: 'users',
        analyzed_at: '2024-01-01T00:00:00Z',
        rca_status: 'analyzed',
        probable_causes: [],
        metadata: {},
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await analyzeAnomaly(mockRequest)

      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/rca/analyze'),
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(mockRequest),
        })
      )
    })
  })

  describe('reanalyzeAnomaly', () => {
    it('should reanalyze successfully', async () => {
      const mockResponse: RCAResult = {
        anomaly_id: 'anom-1',
        table_name: 'users',
        analyzed_at: '2024-01-01T00:00:00Z',
        rca_status: 'analyzed',
        probable_causes: [],
        metadata: {},
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await reanalyzeAnomaly('anom-1')

      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/rca/anom-1/reanalyze'),
        expect.objectContaining({
          method: 'POST',
        })
      )
    })
  })

  describe('dismissRCAResult', () => {
    it('should dismiss result successfully', async () => {
      const mockResponse = {
        status: 'dismissed',
        anomaly_id: 'anom-1',
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await dismissRCAResult('anom-1', 'Not relevant')

      expect(result).toEqual(mockResponse)
      const fetchCall = vi.mocked(fetch).mock.calls[0][0] as string
      expect(fetchCall).toContain('/api/rca/anom-1')
      expect(fetchCall).toContain('reason=')
      expect(vi.mocked(fetch).mock.calls[0][1]).toMatchObject({
        method: 'DELETE',
      })
    })
  })

  describe('getRCAStatistics', () => {
    it('should fetch statistics successfully', async () => {
      const mockResponse: RCAStatistics = {
        total_analyses: 100,
        analyzed: 80,
        dismissed: 10,
        pending: 10,
        avg_causes_per_anomaly: 2.5,
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await getRCAStatistics()

      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/api/rca/statistics/summary'))
    })
  })

  describe('getRecentPipelineRuns', () => {
    it('should fetch pipeline runs successfully', async () => {
      const mockResponse: PipelineRun[] = [
        {
          run_id: 'run-1',
          pipeline_name: 'pipeline-1',
          pipeline_type: 'etl',
          started_at: '2024-01-01T00:00:00Z',
          status: 'completed',
          affected_tables: ['users'],
        },
      ]

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await getRecentPipelineRuns({ limit: 10 })

      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/rca/pipeline-runs/recent?limit=10')
      )
    })
  })

  describe('getRecentDeployments', () => {
    it('should fetch deployments successfully', async () => {
      const mockResponse: CodeDeployment[] = [
        {
          deployment_id: 'deploy-1',
          deployed_at: '2024-01-01T00:00:00Z',
          deployment_type: 'code',
          changed_files: ['file1.py'],
          affected_pipelines: ['pipeline-1'],
        },
      ]

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await getRecentDeployments({ limit: 10 })

      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/rca/deployments/recent?limit=10')
      )
    })
  })

  describe('getEventsTimeline', () => {
    it('should fetch timeline successfully', async () => {
      const mockResponse: EventTimelineItem[] = [
        {
          timestamp: '2024-01-01T00:00:00Z',
          event_type: 'anomaly',
          event_data: { anomaly_id: 'anom-1' },
          relevance_score: 0.9,
        },
      ]

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await getEventsTimeline({
        start_time: '2024-01-01T00:00:00Z',
        end_time: '2024-01-02T00:00:00Z',
      })

      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/rca/timeline')
      )
    })
  })
})

