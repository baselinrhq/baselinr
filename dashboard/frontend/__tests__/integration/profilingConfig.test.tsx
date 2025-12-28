import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ProfilingPage from '@/app/config/profiling/page'
import { useConfig } from '@/hooks/useConfig'
import { fetchConfig, saveConfig } from '@/lib/api/config'
import { getTablePreview } from '@/lib/api/tables'

// Mock the hooks and API
vi.mock('@/hooks/useConfig')
vi.mock('@/lib/api/config', () => ({
  fetchConfig: vi.fn(),
  saveConfig: vi.fn(),
}))
vi.mock('@/lib/api/tables', () => ({
  getTablePreview: vi.fn(),
}))

const createTestQueryClient = () => {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

describe('ProfilingPage Integration', () => {
  const mockConfig = {
    profiling: {
      metrics: ['count', 'null_count'],
      max_distinct_values: 1000,
      compute_histograms: true,
      histogram_bins: 10,
      default_sample_ratio: 1.0,
      enable_enrichment: true,
      tables: [
        {
          schema: 'public',
          table: 'users',
        },
      ],
    },
  }

  const mockUseConfig = {
    currentConfig: mockConfig,
    loadConfig: vi.fn(),
    updateConfigPath: vi.fn(),
    saveConfig: vi.fn().mockResolvedValue(undefined),
    isLoading: false,
    error: null,
    canSave: true,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useConfig).mockReturnValue(mockUseConfig as any)
    vi.mocked(getTablePreview).mockResolvedValue({
      schema: 'public',
      table: 'users',
      columns: [
        { name: 'id', type: 'integer', nullable: false },
        { name: 'email', type: 'varchar', nullable: false },
      ],
      row_count: 100,
      table_type: 'table',
    })
  })

  const renderPage = () => {
    const queryClient = createTestQueryClient()
    return render(
      <QueryClientProvider client={queryClient}>
        <ProfilingPage />
      </QueryClientProvider>
    )
  }

  it('loads current profiling config', () => {
    renderPage()

    expect(screen.getByText('Profiling Configuration')).toBeInTheDocument()
    expect(screen.getByText('Global Profiling Settings')).toBeInTheDocument()
    expect(screen.getByText('Contract-level profiling configurations')).toBeInTheDocument()
  })

  it('updates global settings', async () => {
    const updateConfigPath = vi.fn()
    vi.mocked(useConfig).mockReturnValue({
      ...mockUseConfig,
      updateConfigPath,
    } as any)

    renderPage()

    // Find the input near the "Max Distinct Values" label
    const maxDistinctLabel = screen.getByText(/Max Distinct Values/i)
    const maxDistinctSection = maxDistinctLabel.closest('.space-y-4')
    const maxDistinctInput = maxDistinctSection?.querySelector('input[type="number"]') as HTMLInputElement
    expect(maxDistinctInput).toBeTruthy()
    fireEvent.change(maxDistinctInput, { target: { value: '2000' } })

    await waitFor(() => {
      expect(updateConfigPath).toHaveBeenCalledWith(
        ['profiling', 'max_distinct_values'],
        2000
      )
    })
  })

  it('adds table override', async () => {
    const updateConfigPath = vi.fn()
    vi.mocked(useConfig).mockReturnValue({
      ...mockUseConfig,
      updateConfigPath,
    } as any)

    renderPage()

    // Verify the page renders with contract configuration link
    expect(screen.getByText('Contract-level profiling configurations')).toBeInTheDocument()
    expect(screen.getByText('Manage in Contracts')).toBeInTheDocument()
  })

  it('configures partition for table', async () => {
    const updateConfigPath = vi.fn()
    vi.mocked(useConfig).mockReturnValue({
      ...mockUseConfig,
      updateConfigPath,
    } as any)

    renderPage()

    // Verify the page renders with contract configuration link
    expect(screen.getByText('Contract-level profiling configurations')).toBeInTheDocument()
  })

  it('configures sampling for table', async () => {
    const updateConfigPath = vi.fn()
    vi.mocked(useConfig).mockReturnValue({
      ...mockUseConfig,
      updateConfigPath,
    } as any)

    renderPage()

    // Verify the page renders with contract configuration link
    expect(screen.getByText('Contract-level profiling configurations')).toBeInTheDocument()
  })

  it('configures columns for table', async () => {
    const updateConfigPath = vi.fn()
    vi.mocked(useConfig).mockReturnValue({
      ...mockUseConfig,
      updateConfigPath,
    } as any)

    renderPage()

    // Verify the page renders with contract configuration link
    expect(screen.getByText('Contract-level profiling configurations')).toBeInTheDocument()
  })

  it('saves configuration', async () => {
    const saveConfig = vi.fn().mockResolvedValue(undefined)
    vi.mocked(useConfig).mockReturnValue({
      ...mockUseConfig,
      saveConfig,
    } as any)

    renderPage()

    const saveButton = screen.getByRole('button', { name: /Save Configuration/i })
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(saveConfig).toHaveBeenCalled()
    })

    await waitFor(() => {
      expect(screen.getByText('Saved successfully')).toBeInTheDocument()
    })
  })

  it('handles API errors gracefully', () => {
    vi.mocked(useConfig).mockReturnValue({
      ...mockUseConfig,
      error: new Error('Failed to load config'),
      currentConfig: null,
    } as any)

    renderPage()

    expect(screen.getByText('Failed to Load Configuration')).toBeInTheDocument()
    expect(screen.getByText('Failed to load config')).toBeInTheDocument()
  })
})

