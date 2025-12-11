/**
 * Unit tests for ConfigHistory component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigHistory } from '@/components/config/ConfigHistory'
import { getConfigHistory, ConfigError } from '@/lib/api/config'

// Mock the API
vi.mock('@/lib/api/config', () => ({
  getConfigHistory: vi.fn(),
  ConfigError: class extends Error {
    constructor(message: string, public statusCode?: number) {
      super(message)
      this.name = 'ConfigError'
    }
  },
}))

const mockVersions = [
  {
    version_id: 'version-1',
    created_at: new Date().toISOString(),
    created_by: 'user1',
    comment: 'Initial config',
  },
  {
    version_id: 'version-2',
    created_at: new Date(Date.now() - 86400000).toISOString(),
    created_by: 'user2',
    comment: 'Updated storage config',
  },
]

describe('ConfigHistory', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })
    vi.clearAllMocks()
  })

  const renderWithQuery = (component: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>
    )
  }

  it('renders config history', async () => {
    ;(getConfigHistory as any).mockResolvedValue({
      versions: mockVersions,
      total: 2,
    })

    renderWithQuery(<ConfigHistory />)

    await waitFor(() => {
      expect(screen.getByText(/Configuration History/i)).toBeInTheDocument()
    })
  })

  it('displays version list', async () => {
    ;(getConfigHistory as any).mockResolvedValue({
      versions: mockVersions,
      total: 2,
    })

    renderWithQuery(<ConfigHistory />)

    await waitFor(() => {
      expect(screen.getByText('Initial config')).toBeInTheDocument()
      expect(screen.getByText('Updated storage config')).toBeInTheDocument()
    })
  })

  it('shows current version badge', async () => {
    ;(getConfigHistory as any).mockResolvedValue({
      versions: mockVersions,
      total: 2,
    })

    renderWithQuery(<ConfigHistory />)

    await waitFor(() => {
      const badges = screen.getAllByText('Current')
      expect(badges.length).toBeGreaterThan(0)
    })
  })

  it('calls onVersionSelect when view button is clicked', async () => {
    ;(getConfigHistory as any).mockResolvedValue({
      versions: mockVersions,
      total: 2,
    })

    const mockOnSelect = vi.fn()
    renderWithQuery(<ConfigHistory onVersionSelect={mockOnSelect} />)

    await waitFor(() => {
      const viewButtons = screen.queryAllByText('View')
      expect(viewButtons.length).toBeGreaterThan(0)
    })

    const viewButtons = screen.getAllByText('View')
    fireEvent.click(viewButtons[0])

    await waitFor(() => {
      expect(mockOnSelect).toHaveBeenCalledWith('version-1')
    })
  })

  it('calls onCompare when compare button is clicked', async () => {
    ;(getConfigHistory as any).mockResolvedValue({
      versions: mockVersions,
      total: 2,
    })

    const mockOnCompare = vi.fn()
    renderWithQuery(<ConfigHistory onCompare={mockOnCompare} />)

    await waitFor(() => {
      const compareButtons = screen.queryAllByText('Compare')
      expect(compareButtons.length).toBeGreaterThan(0)
    })

    const compareButtons = screen.getAllByText('Compare')
    fireEvent.click(compareButtons[0])

    await waitFor(() => {
      expect(mockOnCompare).toHaveBeenCalledWith('version-2')
    })
  })

  it('calls onRestore when restore button is clicked', async () => {
    ;(getConfigHistory as any).mockResolvedValue({
      versions: mockVersions,
      total: 2,
    })

    const mockOnRestore = vi.fn()
    renderWithQuery(<ConfigHistory onRestore={mockOnRestore} />)

    await waitFor(() => {
      const restoreButtons = screen.queryAllByText('Restore')
      expect(restoreButtons.length).toBeGreaterThan(0)
    })

    const restoreButtons = screen.getAllByText('Restore')
    fireEvent.click(restoreButtons[0])

    await waitFor(() => {
      expect(mockOnRestore).toHaveBeenCalledWith('version-2')
    })
  })

  it('shows loading state', () => {
    ;(getConfigHistory as any).mockImplementation(() => new Promise(() => {}))

    renderWithQuery(<ConfigHistory />)

    expect(screen.getByText('Loading history...')).toBeInTheDocument()
  })

  it('shows error state', async () => {
    ;(getConfigHistory as any).mockRejectedValue(new ConfigError('Failed to load'))

    renderWithQuery(<ConfigHistory />)

    await waitFor(() => {
      expect(screen.getByText(/Error loading history/i)).toBeInTheDocument()
    })
  })

  it('shows empty state when no versions', async () => {
    ;(getConfigHistory as any).mockResolvedValue({
      versions: [],
      total: 0,
    })

    renderWithQuery(<ConfigHistory />)

    await waitFor(() => {
      expect(screen.getByText(/No Configuration History/i)).toBeInTheDocument()
    })
  })

  it('handles refresh button click', async () => {
    ;(getConfigHistory as any).mockResolvedValue({
      versions: mockVersions,
      total: 2,
    })

    renderWithQuery(<ConfigHistory />)

    await waitFor(() => {
      expect(screen.getByText('Refresh')).toBeInTheDocument()
    })

    const refreshButton = screen.getByText('Refresh')
    fireEvent.click(refreshButton)

    // Should refetch
    await waitFor(() => {
      expect(getConfigHistory).toHaveBeenCalledTimes(2)
    })
  })
})

