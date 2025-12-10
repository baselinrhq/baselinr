import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ValidationOverview from '@/components/validation/ValidationOverview'
import { fetchValidationSummary } from '@/lib/api'

vi.mock('@/lib/api', () => ({
  fetchValidationSummary: vi.fn(),
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

describe('ValidationOverview', () => {
  const mockSummary = {
    total_validations: 100,
    passed_count: 85,
    failed_count: 15,
    pass_rate: 85.0,
    by_rule_type: {
      format: 30,
      range: 40,
      enum: 30,
    },
    by_severity: {
      low: 5,
      medium: 7,
      high: 3,
    },
    by_table: {
      users: 20,
      orders: 30,
      products: 50,
    },
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

  it('renders loading state', () => {
    vi.mocked(fetchValidationSummary).mockImplementation(() => new Promise(() => {}))

    render(<ValidationOverview />, { wrapper: createWrapper() })

    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('renders validation summary', async () => {
    vi.mocked(fetchValidationSummary).mockResolvedValue(mockSummary)

    render(<ValidationOverview />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('100')).toBeInTheDocument() // Total validations
      expect(screen.getByText('85.0%')).toBeInTheDocument() // Pass rate
      expect(screen.getByText('15')).toBeInTheDocument() // Failed count
    })
  })

  it('displays error message on failure', async () => {
    vi.mocked(fetchValidationSummary).mockRejectedValue(new Error('API error'))

    render(<ValidationOverview />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument()
    })
  })
})

