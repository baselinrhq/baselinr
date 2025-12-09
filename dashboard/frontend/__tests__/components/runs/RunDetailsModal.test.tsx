import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import RunDetailsModal from '@/components/runs/RunDetailsModal'
import { Run } from '@/lib/api'

import * as api from '@/lib/api'

vi.mock('@/lib/api', () => ({
  fetchRunDetails: vi.fn(),
  retryRun: vi.fn(),
}))

describe('RunDetailsModal', () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  const mockRun: Run = {
    run_id: 'run1',
    dataset_name: 'table1',
    schema_name: 'public',
    warehouse_type: 'postgres',
    profiled_at: '2024-01-01T00:00:00Z',
    status: 'completed',
    row_count: 1000,
    column_count: 10,
    has_drift: false,
  }

  const renderWithProvider = (component: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>
    )
  }

  it('renders modal when open', () => {
    const onClose = vi.fn()
    renderWithProvider(
      <RunDetailsModal run={mockRun} isOpen={true} onClose={onClose} />
    )

    expect(screen.getByText(/Run Details/i)).toBeInTheDocument()
  })

  it('does not render when closed', () => {
    const onClose = vi.fn()
    renderWithProvider(
      <RunDetailsModal run={mockRun} isOpen={false} onClose={onClose} />
    )

    expect(screen.queryByText(/Run Details/i)).not.toBeInTheDocument()
  })

  it('displays loading state', () => {
    const onClose = vi.fn()
    vi.mocked(api.fetchRunDetails).mockImplementation(() => new Promise(() => {})) // Never resolves

    renderWithProvider(
      <RunDetailsModal run={mockRun} isOpen={true} onClose={onClose} />
    )

    // Should show loading spinner
    expect(screen.getByRole('status') || screen.queryByText(/loading/i)).toBeTruthy()
  })

  it('calls onClose when close button is clicked', async () => {
    const onClose = vi.fn()
    const mockRunDetails = {
      run_id: 'run1',
      dataset_name: 'table1',
      schema_name: 'public',
      warehouse_type: 'postgres',
      profiled_at: '2024-01-01T00:00:00Z',
      environment: 'production',
      row_count: 1000,
      column_count: 10,
      columns: [],
    }
    vi.mocked(api.fetchRunDetails).mockResolvedValue(mockRunDetails)

    renderWithProvider(
      <RunDetailsModal run={mockRun} isOpen={true} onClose={onClose} />
    )

    // Wait for data to load - check for content that appears after loading
    await waitFor(() => {
      expect(screen.getByText(/table1/i)).toBeInTheDocument()
    }, { timeout: 3000 })

    // Find the close button by aria-label
    const closeButton = screen.getByLabelText(/Close modal/i)
    closeButton.click()
    
    await waitFor(() => {
      expect(onClose).toHaveBeenCalled()
    })
  })
})

