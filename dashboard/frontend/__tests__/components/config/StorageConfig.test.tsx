/**
 * Unit tests for StorageConfig component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StorageConfig } from '@/components/config/StorageConfig'
import { testConnection, ConnectionTestError } from '@/lib/api/config'
import { listConnections } from '@/lib/api/connections'
import type { StorageConfig as StorageConfigType } from '@/types/config'

// Mock the API
vi.mock('@/lib/api/config', () => ({
  testConnection: vi.fn(),
  ConnectionTestError: class ConnectionTestError extends Error {
    connectionError?: string
    constructor(message: string, connectionError?: string) {
      super(message)
      this.name = 'ConnectionTestError'
      this.connectionError = connectionError
    }
  },
}))

vi.mock('@/lib/api/connections', () => ({
  listConnections: vi.fn(),
}))

const createTestQueryClient = () => {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

describe('StorageConfig', () => {
  const mockStorage: StorageConfigType = {
    connection: {
      type: 'postgres',
      host: 'localhost',
      port: 5432,
      database: 'test_db',
    },
    results_table: 'baselinr_results',
    runs_table: 'baselinr_runs',
    create_tables: true,
  }

  const mockOnChange = vi.fn()
  const mockOnTestConnection = vi.fn()

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
  })

  const renderWithQueryClient = (component: React.ReactElement) => {
    const queryClient = createTestQueryClient()
    return render(
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>
    )
  }

  it('renders connection selector', () => {
    renderWithQueryClient(
      <StorageConfig storage={mockStorage} onChange={mockOnChange} />
    )

    expect(screen.getByText('Storage Database Connection')).toBeInTheDocument()
  })

  it('renders table name inputs', () => {
    renderWithQueryClient(
      <StorageConfig storage={mockStorage} onChange={mockOnChange} />
    )

    expect(screen.getByText('Results Table Name')).toBeInTheDocument()
    expect(screen.getByText('Runs Table Name')).toBeInTheDocument()
  })

  it('renders create tables toggle', () => {
    renderWithQueryClient(
      <StorageConfig storage={mockStorage} onChange={mockOnChange} />
    )

    expect(screen.getByText('Auto-create Tables')).toBeInTheDocument()
  })

  it('updates storage config on table name change', async () => {
    renderWithQueryClient(
      <StorageConfig storage={mockStorage} onChange={mockOnChange} />
    )

    const resultsInput = screen.getByPlaceholderText('baselinr_results')
    fireEvent.change(resultsInput, { target: { value: 'custom_results' } })

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalled()
    })
  })

  it('validates table names', async () => {
    const invalidStorage = {
      ...mockStorage,
      results_table: 'invalid-table-name!',
    }

    renderWithQueryClient(
      <StorageConfig storage={invalidStorage} onChange={mockOnChange} />
    )

    await waitFor(() => {
      const errorElements = screen.queryAllByText(/Table name can only contain letters, numbers, and underscores/)
      expect(errorElements.length).toBeGreaterThan(0)
    })
  })

  it('shows custom connection form when Custom is selected', async () => {
    const customStorage: StorageConfigType = {
      ...mockStorage,
      connection: {
        type: 'postgres',
        database: '',
      },
    }

    renderWithQueryClient(
      <StorageConfig storage={customStorage} onChange={mockOnChange} />
    )

    // Wait for connections to load
    await waitFor(() => {
      expect(screen.getByText('Custom Connection')).toBeInTheDocument()
    })

    // Custom connection form should be visible
    expect(screen.getByText('Database Type')).toBeInTheDocument()
  })

  it('calls onTestConnection when test button is clicked', async () => {
    vi.mocked(testConnection).mockResolvedValue({
      success: true,
      message: 'Connection successful',
      connection_time_ms: 100,
    })

    renderWithQueryClient(
      <StorageConfig
        storage={mockStorage}
        onChange={mockOnChange}
        onTestConnection={mockOnTestConnection}
      />
    )

    const testButton = screen.getByRole('button', { name: /Test Connection/i })
    fireEvent.click(testButton)

    await waitFor(() => {
      expect(testConnection).toHaveBeenCalledWith(mockStorage.connection)
      expect(mockOnTestConnection).toHaveBeenCalled()
    })
  })

  it('displays test success message', async () => {
    vi.mocked(testConnection).mockResolvedValue({
      success: true,
      message: 'Connection successful',
      connection_time_ms: 100,
    })

    renderWithQueryClient(
      <StorageConfig storage={mockStorage} onChange={mockOnChange} />
    )

    const testButton = screen.getByRole('button', { name: /Test Connection/i })
    fireEvent.click(testButton)

    await waitFor(() => {
      expect(screen.getByText('Connection successful!')).toBeInTheDocument()
    })
  })

  it('displays test error message', async () => {
    vi.mocked(testConnection).mockRejectedValue(
      new ConnectionTestError('Connection failed', 'Invalid credentials')
    )

    renderWithQueryClient(
      <StorageConfig storage={mockStorage} onChange={mockOnChange} />
    )

    const testButton = screen.getByRole('button', { name: /Test Connection/i })
    fireEvent.click(testButton)

    await waitFor(() => {
      expect(screen.getByText('Connection test failed')).toBeInTheDocument()
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
    })
  })

  it('updates create_tables toggle', async () => {
    renderWithQueryClient(
      <StorageConfig storage={mockStorage} onChange={mockOnChange} />
    )

    // Find the toggle by its label
    const toggle = screen.getByRole('switch', { name: /Create tables automatically/i })
    fireEvent.click(toggle)

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalled()
    })
  })

  it('disables inputs when loading', () => {
    renderWithQueryClient(
      <StorageConfig storage={mockStorage} onChange={mockOnChange} isLoading={true} />
    )

    const resultsInput = screen.getByPlaceholderText('baselinr_results')
    expect(resultsInput).toBeDisabled()
  })
})

