import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import DriftDetails from '@/components/drift/DriftDetails'
import { fetchDriftDetails, fetchDriftImpact } from '@/lib/api'

vi.mock('@/lib/api', () => ({
  fetchDriftDetails: vi.fn(),
  fetchDriftImpact: vi.fn(),
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

describe('DriftDetails', () => {
  const mockDetails = {
    event: {
      event_id: 'event1',
      run_id: 'run1',
      table_name: 'customers',
      column_name: 'age',
      metric_name: 'mean',
      baseline_value: 30.0,
      current_value: 35.0,
      change_percent: 16.67,
      severity: 'high',
      timestamp: '2024-01-01T00:00:00Z',
      warehouse_type: 'postgres',
    },
    baseline_metrics: {},
    current_metrics: {},
    historical_values: [],
    related_events: [],
  }

  const mockImpact = {
    event_id: 'event1',
    affected_tables: [],
    affected_metrics: 1,
    impact_score: 0.8,
    recommendations: ['High severity drift detected.'],
  }

  it('does not render when not open', () => {
    render(
      <DriftDetails
        eventId="event1"
        isOpen={false}
        onClose={vi.fn()}
      />,
      { wrapper: createWrapper() }
    )
    expect(screen.queryByText('Drift Event Details')).not.toBeInTheDocument()
  })

  it('renders loading state', () => {
    vi.mocked(fetchDriftDetails).mockImplementation(() => new Promise(() => {}))
    
    render(
      <DriftDetails
        eventId="event1"
        isOpen={true}
        onClose={vi.fn()}
      />,
      { wrapper: createWrapper() }
    )
    // Loading spinner should be present
    expect(document.querySelector('.animate-spin') || screen.getByRole('status')).toBeTruthy()
  })

  it('renders event details when loaded', async () => {
    vi.mocked(fetchDriftDetails).mockResolvedValue(mockDetails as any)
    vi.mocked(fetchDriftImpact).mockResolvedValue(mockImpact as any)
    
    render(
      <DriftDetails
        eventId="event1"
        isOpen={true}
        onClose={vi.fn()}
      />,
      { wrapper: createWrapper() }
    )
    
    await waitFor(() => {
      expect(screen.getByText('Drift Event Details')).toBeInTheDocument()
    })
    
    // Wait for tab content to render
    await waitFor(() => {
      expect(screen.getByText('customers')).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('renders error state', async () => {
    vi.mocked(fetchDriftDetails).mockRejectedValue(new Error('API Error'))
    
    render(
      <DriftDetails
        eventId="event1"
        isOpen={true}
        onClose={vi.fn()}
      />,
      { wrapper: createWrapper() }
    )
    
    await waitFor(() => {
      expect(screen.getByText(/Failed to load drift details/i)).toBeInTheDocument()
    })
  })
})

