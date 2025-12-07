/**
 * Integration tests for storage configuration page
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import StoragePage from '@/app/config/storage/page'
import { getStorageStatus } from '@/lib/api/config'
import { listConnections } from '@/lib/api/connections'
import type { BaselinrConfig, StorageStatusResponse } from '@/types/config'

// Mock the API
vi.mock('@/lib/api/config', () => ({
  fetchConfig: vi.fn(),
  saveConfig: vi.fn(),
  getStorageStatus: vi.fn(),
  testConnection: vi.fn(),
}))

vi.mock('@/lib/api/connections', () => ({
  listConnections: vi.fn(),
}))

// Mock useConfig hook
const mockUpdateConfigPath = vi.fn()
const mockSaveConfig = vi.fn()
const mockLoadConfig = vi.fn()

vi.mock('@/hooks/useConfig', () => ({
  useConfig: () => ({
    currentConfig: {
      storage: {
        connection: {
          type: 'postgres',
          host: 'localhost',
          port: 5432,
          database: 'test_db',
        },
        results_table: 'baselinr_results',
        runs_table: 'baselinr_runs',
        create_tables: true,
      },
    } as BaselinrConfig,
    loadConfig: mockLoadConfig,
    updateConfigPath: mockUpdateConfigPath,
    saveConfig: mockSaveConfig,
    isLoading: false,
    error: null,
    hasChanges: true,
    canSave: true,
  }),
}))

const createTestQueryClient = () => {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = createTestQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  )
}

describe('Storage Configuration Integration', () => {
  const mockStorageStatus: StorageStatusResponse = {
    connection_status: 'connected',
    results_table_exists: true,
    runs_table_exists: true,
    last_checked: '2024-01-01T12:00:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(listConnections).mockResolvedValue({
      connections: [
        {
          id: '1',
          name: 'Test Connection',
          connection: {
            type: 'postgres',
            host: 'localhost',
            port: 5432,
            database: 'test_db',
          },
          created_at: '2024-01-01T00:00:00Z',
        },
      ],
      total: 1,
    })
    vi.mocked(getStorageStatus).mockResolvedValue(mockStorageStatus)
    mockSaveConfig.mockResolvedValue({
      config: {
        storage: {
          connection: {
            type: 'postgres',
            host: 'localhost',
            port: 5432,
            database: 'test_db',
          },
          results_table: 'baselinr_results',
          runs_table: 'baselinr_runs',
          create_tables: true,
        },
      },
    })
  })

  it('loads and displays storage configuration', async () => {
    renderWithProviders(<StoragePage />)

    await waitFor(() => {
      expect(screen.getByText('Storage Configuration')).toBeInTheDocument()
      expect(screen.getByText('Storage Database Connection')).toBeInTheDocument()
    })
  })

  it('updates storage connection', async () => {
    renderWithProviders(<StoragePage />)

    await waitFor(() => {
      expect(screen.getByText('Storage Database Connection')).toBeInTheDocument()
    })

    // The connection selector should be visible
    const connectionSelect = screen.getByText('Custom Connection')
    expect(connectionSelect).toBeInTheDocument()
  })

  it('updates table names', async () => {
    renderWithProviders(<StoragePage />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText('baselinr_results')).toBeInTheDocument()
    })

    const resultsInput = screen.getByPlaceholderText('baselinr_results')
    fireEvent.change(resultsInput, { target: { value: 'custom_results' } })

    await waitFor(() => {
      expect(mockUpdateConfigPath).toHaveBeenCalled()
    })
  })

  it('toggles create_tables', async () => {
    renderWithProviders(<StoragePage />)

    await waitFor(() => {
      expect(screen.getByRole('switch', { name: /Create tables automatically/i })).toBeInTheDocument()
    })

    const toggle = screen.getByRole('switch', { name: /Create tables automatically/i })
    fireEvent.click(toggle)

    await waitFor(() => {
      expect(mockUpdateConfigPath).toHaveBeenCalled()
    })
  })

  it('saves configuration', async () => {
    renderWithProviders(<StoragePage />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Save Configuration/i })).toBeInTheDocument()
    })

    const saveButton = screen.getByRole('button', { name: /Save Configuration/i })
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(mockSaveConfig).toHaveBeenCalled()
    })
  })

  it('displays storage status', async () => {
    renderWithProviders(<StoragePage />)

    await waitFor(() => {
      expect(screen.getByText('Storage Status')).toBeInTheDocument()
      expect(screen.getByText('Connected')).toBeInTheDocument()
    })
  })

  it('checks storage status on refresh', async () => {
    renderWithProviders(<StoragePage />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Refresh/i })).toBeInTheDocument()
    })

    const refreshButton = screen.getByRole('button', { name: /Refresh/i })
    fireEvent.click(refreshButton)

    await waitFor(() => {
      expect(getStorageStatus).toHaveBeenCalled()
    })
  })

  it('handles API errors gracefully', async () => {
    vi.mocked(getStorageStatus).mockRejectedValue(new Error('Backend API Not Available'))

    renderWithProviders(<StoragePage />)

    await waitFor(() => {
      // Status should still render, just with error
      expect(screen.getByText('Storage Status')).toBeInTheDocument()
    })
  })
})

