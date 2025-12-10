import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import DriftDashboard from '@/components/drift/DriftDashboard'
import { fetchDriftSummary } from '@/lib/api'

vi.mock('@/lib/api', () => ({
  fetchDriftSummary: vi.fn(),
}))

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

describe('DriftDashboard', () => {
  const mockSummary = {
    total_events: 10,
    by_severity: {
      low: 5,
      medium: 3,
      high: 2,
    },
    trending: [
      { timestamp: '2024-01-01T00:00:00Z', value: 2 },
      { timestamp: '2024-01-02T00:00:00Z', value: 3 },
    ],
    top_affected_tables: [
      {
        table_name: 'customers',
        drift_count: 5,
        severity_breakdown: { low: 2, medium: 2, high: 1 },
      },
    ],
    warehouse_breakdown: {
      postgres: 10,
    },
    recent_activity: [],
  }

  it('renders loading state', () => {
    vi.mocked(fetchDriftSummary).mockImplementation(() => new Promise(() => {}))
    
    render(<DriftDashboard />, { wrapper: createWrapper() })
    // Loading spinner should be present
    expect(screen.getByRole('status') || document.querySelector('.animate-spin')).toBeTruthy()
  })

  it('renders KPI cards when data is loaded', async () => {
    vi.mocked(fetchDriftSummary).mockResolvedValue(mockSummary as any)
    
    render(<DriftDashboard />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      expect(screen.getByText('Total Events')).toBeInTheDocument()
      expect(screen.getByText('10')).toBeInTheDocument()
    })
  })

  it('renders top affected tables', async () => {
    vi.mocked(fetchDriftSummary).mockResolvedValue(mockSummary as any)
    
    render(<DriftDashboard />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      expect(screen.getByText('Top Affected Tables')).toBeInTheDocument()
      expect(screen.getByText('customers')).toBeInTheDocument()
    })
  })

  it('handles error state', async () => {
    vi.mocked(fetchDriftSummary).mockRejectedValue(new Error('API Error'))
    
    render(<DriftDashboard />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      expect(screen.getByText(/Failed to load drift summary/i)).toBeInTheDocument()
    })
  })
})

