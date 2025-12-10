import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ImpactAnalysis from '@/components/lineage/ImpactAnalysis'
import * as lineageApi from '@/lib/api/lineage'

// Mock the API
vi.mock('@/lib/api/lineage', () => ({
  getLineageImpact: vi.fn(),
}))

describe('ImpactAnalysis', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0, staleTime: 0 },
      },
    })
    vi.clearAllMocks()
  })

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )

  it('renders loading state', () => {
    vi.mocked(lineageApi.getLineageImpact).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    render(
      <ImpactAnalysis
        table="test_table"
        schema="public"
        isOpen={true}
      />,
      { wrapper }
    )

    expect(screen.getByText(/Loading/i)).toBeInTheDocument()
  })

  it('displays impact data', async () => {
    const mockImpact = {
      table: 'test_table',
      schema: 'public',
      affected_tables: [
        { schema: 'public', table: 'downstream1' },
        { schema: 'public', table: 'downstream2' },
      ],
      impact_score: 0.75,
      affected_metrics: 15,
      drift_propagation: ['node1', 'node2'],
      recommendations: [
        'Check downstream tables',
        'Monitor for data quality issues',
      ],
    }

    vi.mocked(lineageApi.getLineageImpact).mockResolvedValue(mockImpact)

    render(
      <ImpactAnalysis
        table="test_table"
        schema="public"
        isOpen={true}
      />,
      { wrapper }
    )

    await waitFor(
      () => {
        expect(screen.getByText('Impact Analysis')).toBeInTheDocument()
        expect(screen.getByText('75%')).toBeInTheDocument()
        expect(screen.getByText('15')).toBeInTheDocument()
        expect(screen.getByText('downstream1')).toBeInTheDocument()
      },
      { timeout: 5000 }
    )
  })

  it('displays recommendations', async () => {
    const mockImpact = {
      table: 'test_table',
      schema: 'public',
      affected_tables: [],
      impact_score: 0.5,
      affected_metrics: 0,
      drift_propagation: [],
      recommendations: ['Recommendation 1', 'Recommendation 2'],
    }

    vi.mocked(lineageApi.getLineageImpact).mockResolvedValue(mockImpact)

    render(
      <ImpactAnalysis
        table="test_table"
        schema="public"
        isOpen={true}
      />,
      { wrapper }
    )

    await waitFor(
      () => {
        expect(screen.getByText('Recommendation 1')).toBeInTheDocument()
        expect(screen.getByText('Recommendation 2')).toBeInTheDocument()
      },
      { timeout: 5000 }
    )
  })

  it('handles empty downstream tables', async () => {
    const mockImpact = {
      table: 'test_table',
      schema: 'public',
      affected_tables: [],
      impact_score: 0.0,
      affected_metrics: 0,
      drift_propagation: [],
      recommendations: [],
    }

    vi.mocked(lineageApi.getLineageImpact).mockResolvedValue(mockImpact)

    render(
      <ImpactAnalysis
        table="test_table"
        schema="public"
        isOpen={true}
      />,
      { wrapper }
    )

    await waitFor(
      () => {
        expect(screen.getByText(/No downstream dependencies found/i)).toBeInTheDocument()
      },
      { timeout: 5000 }
    )
  })

  it('does not render when closed', () => {
    render(
      <ImpactAnalysis
        table="test_table"
        schema="public"
        isOpen={false}
      />,
      { wrapper }
    )

    expect(screen.queryByText('Impact Analysis')).not.toBeInTheDocument()
  })
})

