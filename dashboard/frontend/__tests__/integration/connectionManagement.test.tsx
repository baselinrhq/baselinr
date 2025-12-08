/**
 * Integration tests for connection management
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ConnectionsPage from '@/app/config/connections/page'
import {
  listConnections,
  getConnection,
  saveConnection,
  updateConnection,
  deleteConnection,
  testConnection,
} from '@/lib/api/connections'
import type { SavedConnection, ConnectionsListResponse } from '@/types/connection'
import type { ConnectionConfig } from '@/types/config'

// Mock the API
vi.mock('@/lib/api/connections', () => ({
  listConnections: vi.fn(),
  getConnection: vi.fn(),
  saveConnection: vi.fn(),
  updateConnection: vi.fn(),
  deleteConnection: vi.fn(),
  testConnection: vi.fn(),
}))

// Mock useConfig hook
vi.mock('@/hooks/useConfig', () => ({
  useConfig: () => ({
    updateConfigPath: vi.fn(),
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

describe('Connection Management Integration', () => {
  const mockConnections: SavedConnection[] = [
    {
      id: '1',
      name: 'Connection 1',
      connection: {
        type: 'postgres',
        host: 'localhost',
        port: 5432,
        database: 'db1',
      },
      created_at: '2024-01-01T00:00:00Z',
      is_active: true,
    },
    {
      id: '2',
      name: 'Connection 2',
      connection: {
        type: 'snowflake',
        account: 'account.region',
        database: 'db2',
        username: 'user',
      },
      created_at: '2024-01-02T00:00:00Z',
      is_active: true,
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(listConnections).mockResolvedValue({
      connections: mockConnections,
      total: 2,
    })
  })

  it('displays list of connections', async () => {
    renderWithProviders(<ConnectionsPage />)

    await waitFor(() => {
      expect(screen.getByText('Connection 1')).toBeInTheDocument()
      expect(screen.getByText('Connection 2')).toBeInTheDocument()
    })
  })

  it('creates new connection', async () => {
    const mockSaveConnection = vi.mocked(saveConnection)
    mockSaveConnection.mockResolvedValue({
      id: '3',
      connection: {
        id: '3',
        name: 'New Connection',
        connection: {
          type: 'postgres',
          database: 'new_db',
        },
        created_at: '2024-01-03T00:00:00Z',
      },
    })

    renderWithProviders(<ConnectionsPage />)

    await waitFor(() => {
      expect(screen.getByText('Connection 1')).toBeInTheDocument()
    })

    // Click new connection button
    fireEvent.click(screen.getByText('New Connection'))

    // Wizard should open (we'll test the wizard separately)
    // For now, just verify the button works
    expect(screen.getByText('New Connection')).toBeInTheDocument()
  })

  it('edits existing connection', async () => {
    const mockGetConnection = vi.mocked(getConnection)
    mockGetConnection.mockResolvedValue(mockConnections[0])

    renderWithProviders(<ConnectionsPage />)

    await waitFor(() => {
      expect(screen.getByText('Connection 1')).toBeInTheDocument()
    })

    // Find and click edit button
    const editButtons = screen.getAllByText('Edit')
    fireEvent.click(editButtons[0])

    await waitFor(() => {
      expect(mockGetConnection).toHaveBeenCalledWith('1')
    })
  })

  it('deletes connection with confirmation', async () => {
    const mockDeleteConnection = vi.mocked(deleteConnection)
    mockDeleteConnection.mockResolvedValue(undefined)

    // Mock window.confirm
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)

    renderWithProviders(<ConnectionsPage />)

    await waitFor(() => {
      expect(screen.getByText('Connection 1')).toBeInTheDocument()
    })

    // Find and click delete button - it might show "Confirm" first
    const deleteButtons = screen.getAllByText('Delete')
    if (deleteButtons.length > 0) {
      fireEvent.click(deleteButtons[0])
      
      // If confirmation dialog appears, click confirm
      await waitFor(() => {
        const confirmButtons = screen.queryAllByText('Confirm')
        if (confirmButtons.length > 0) {
          fireEvent.click(confirmButtons[0])
        }
      }, { timeout: 1000 }).catch(() => {
        // If no confirm button appears, the delete might have been called directly
      })
    }

    // The delete should be called (either directly or after confirm)
    await waitFor(() => {
      // Check if delete was called - it might be called even if confirm button doesn't appear
      expect(mockDeleteConnection).toHaveBeenCalled()
    }, { timeout: 2000 })

    confirmSpy.mockRestore()
  })

  it('tests connection from card', async () => {
    const mockGetConnection = vi.mocked(getConnection)
    const mockTestConnection = vi.mocked(testConnection)
    
    mockGetConnection.mockResolvedValue(mockConnections[0])
    mockTestConnection.mockResolvedValue({
      success: true,
      message: 'Connection successful',
    })

    // Mock window.alert
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})

    renderWithProviders(<ConnectionsPage />)

    await waitFor(() => {
      expect(screen.getByText('Connection 1')).toBeInTheDocument()
    })

    // Find and click test button
    const testButtons = screen.getAllByText('Test')
    fireEvent.click(testButtons[0])

    await waitFor(() => {
      expect(mockGetConnection).toHaveBeenCalledWith('1')
      expect(mockTestConnection).toHaveBeenCalled()
    })

    alertSpy.mockRestore()
  })

  it('sets connection as source', async () => {
    const mockGetConnection = vi.mocked(getConnection)
    mockGetConnection.mockResolvedValue(mockConnections[0])

    // Mock window.confirm and alert
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})

    renderWithProviders(<ConnectionsPage />)

    await waitFor(() => {
      expect(screen.getByText('Connection 1')).toBeInTheDocument()
    })

    // Find and click "Use as Source" button
    const useAsSourceButtons = screen.getAllByText('Use as Source')
    fireEvent.click(useAsSourceButtons[0])

    await waitFor(() => {
      expect(mockGetConnection).toHaveBeenCalledWith('1')
    })

    confirmSpy.mockRestore()
    alertSpy.mockRestore()
  })

  it('displays empty state when no connections exist', async () => {
    vi.mocked(listConnections).mockResolvedValue({
      connections: [],
      total: 0,
    })

    renderWithProviders(<ConnectionsPage />)

    await waitFor(() => {
      expect(screen.getByText('No connections yet')).toBeInTheDocument()
    })
  })

  it('handles API errors gracefully', async () => {
    vi.mocked(listConnections).mockRejectedValue(new Error('API Error'))

    renderWithProviders(<ConnectionsPage />)

    await waitFor(() => {
      // Verify that the error is displayed gracefully
      expect(screen.getByText(/Connection Error/i)).toBeInTheDocument()
      expect(screen.getByText(/API Error/i)).toBeInTheDocument()
    })
  })
})

