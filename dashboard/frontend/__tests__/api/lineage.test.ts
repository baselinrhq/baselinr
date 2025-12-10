import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getLineageGraph, getLineageGraphWithFilters, getLineageImpact, getColumnLineageGraph } from '@/lib/api/lineage'

// Mock fetch globally
global.fetch = vi.fn()

describe('Lineage API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getLineageGraph', () => {
    it('fetches lineage graph successfully', async () => {
      const mockGraph = {
        nodes: [
          { id: 'node1', type: 'table', label: 'table1' },
        ],
        edges: [],
        root_id: 'node1',
        direction: 'both',
      }

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockGraph,
      } as Response)

      const result = await getLineageGraph({
        table: 'table1',
        schema: 'public',
        direction: 'both',
        depth: 3,
      })
      expect(result).toEqual(mockGraph)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/lineage/graph')
      )
    })

    it('includes filter parameters', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ nodes: [], edges: [], direction: 'both' }),
      } as Response)

      await getLineageGraph({
        table: 'table1',
        providers: ['dbt_manifest'],
        schemas: ['public'],
        nodeType: 'table',
        hasDrift: true,
      })

      const callUrl = vi.mocked(global.fetch).mock.calls[0][0] as string
      expect(callUrl).toContain('provider=dbt_manifest')
      expect(callUrl).toContain('schemas=public')
      expect(callUrl).toContain('node_type=table')
      expect(callUrl).toContain('has_drift=true')
    })

    it('handles API errors', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        text: async () => 'Error message',
      } as Response)

      await expect(
        getLineageGraph({ table: 'table1' })
      ).rejects.toThrow('API error')
    })
  })

  describe('getLineageGraphWithFilters', () => {
    it('calls getLineageGraph with filters', async () => {
      const mockGraph = {
        nodes: [],
        edges: [],
        direction: 'both',
      }

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockGraph,
      } as Response)

      const result = await getLineageGraphWithFilters({
        table: 'table1',
        providers: ['dbt_manifest'],
        confidence_min: 0.8,
      })

      expect(result).toEqual(mockGraph)
    })
  })

  describe('getLineageImpact', () => {
    it('fetches lineage impact successfully', async () => {
      const mockImpact = {
        table: 'table1',
        schema: 'public',
        affected_tables: [],
        impact_score: 0.5,
        affected_metrics: 10,
        drift_propagation: [],
        recommendations: ['Check downstream tables'],
      }

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockImpact,
      } as Response)

      const result = await getLineageImpact('table1', 'public', true)
      expect(result).toEqual(mockImpact)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/lineage/impact')
      )
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('table=table1')
      )
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('schema=public')
      )
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('include_metrics=true')
      )
    })

    it('handles missing schema', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          table: 'table1',
          affected_tables: [],
          impact_score: 0.0,
          affected_metrics: 0,
          drift_propagation: [],
          recommendations: [],
        }),
      } as Response)

      await getLineageImpact('table1', undefined, false)
      const callUrl = vi.mocked(global.fetch).mock.calls[0][0] as string
      expect(callUrl).not.toContain('schema=')
      expect(callUrl).toContain('include_metrics=false')
    })

    it('handles API errors', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: false,
        status: 503,
        statusText: 'Service Unavailable',
        text: async () => 'Lineage not available',
      } as Response)

      await expect(
        getLineageImpact('table1')
      ).rejects.toThrow('API error')
    })
  })

  describe('getColumnLineageGraph', () => {
    it('fetches column lineage graph successfully', async () => {
      const mockGraph = {
        nodes: [
          { id: 'col1', type: 'column', label: 'column1' },
        ],
        edges: [],
        direction: 'both',
      }

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockGraph,
      } as Response)

      const result = await getColumnLineageGraph({
        table: 'table1',
        column: 'column1',
        schema: 'public',
      })
      expect(result).toEqual(mockGraph)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/lineage/column-graph')
      )
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('column=column1')
      )
    })
  })
})

