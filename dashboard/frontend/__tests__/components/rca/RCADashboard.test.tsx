/**
 * Unit tests for RCADashboard component
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import RCADashboard from '@/components/rca/RCADashboard'
import * as rcaApi from '@/lib/api/rca'

// Mock the API
vi.mock('@/lib/api/rca', () => ({
  getRCAStatistics: vi.fn(),
}))

const mockStatistics = {
  total_analyses: 100,
  analyzed: 80,
  dismissed: 10,
  pending: 10,
  avg_causes_per_anomaly: 2.5,
}

describe('RCADashboard', () => {
  const createWrapper = () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })
    return ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
  }

  it('renders loading state', () => {
    vi.mocked(rcaApi.getRCAStatistics).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    render(<RCADashboard />, { wrapper: createWrapper() })

    // Check for loading spinner (implementation may vary)
    expect(screen.getByText(/loading/i) || screen.queryByRole('progressbar')).toBeDefined()
  })

  it('renders statistics when loaded', async () => {
    vi.mocked(rcaApi.getRCAStatistics).mockResolvedValueOnce(mockStatistics)

    render(<RCADashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('100')).toBeInTheDocument() // total_analyses
      expect(screen.getByText('80')).toBeInTheDocument() // analyzed
      // Check for pending with more context to avoid ambiguity with dismissed
      expect(screen.getByText('Pending')).toBeInTheDocument()
      const pendingCard = screen.getByText('Pending').closest('div')?.parentElement
      expect(pendingCard).toHaveTextContent('10')
      expect(screen.getByText('2.5')).toBeInTheDocument() // avg_causes_per_anomaly
    })
  })

  it('renders error state', async () => {
    vi.mocked(rcaApi.getRCAStatistics).mockRejectedValueOnce(new Error('API Error'))

    render(<RCADashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/Failed to load/i)).toBeInTheDocument()
    })
  })

  it('calls onAnalyzeNew when button is clicked', async () => {
    vi.mocked(rcaApi.getRCAStatistics).mockResolvedValueOnce(mockStatistics)
    const onAnalyzeNew = vi.fn()

    render(<RCADashboard onAnalyzeNew={onAnalyzeNew} />, { wrapper: createWrapper() })

    await waitFor(() => {
      const button = screen.getByText(/Analyze New Anomaly/i)
      expect(button).toBeInTheDocument()
    })

    const button = screen.getByText(/Analyze New Anomaly/i)
    button.click()

    expect(onAnalyzeNew).toHaveBeenCalledTimes(1)
  })
})

