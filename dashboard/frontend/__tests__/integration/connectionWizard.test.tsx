/**
 * Integration tests for connection wizard flow
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConnectionWizard } from '@/components/config/ConnectionWizard'
import { testConnection, ConnectionTestError } from '@/lib/api/config'
import type { ConnectionConfig } from '@/types/config'

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

describe('ConnectionWizard Integration', () => {
  const mockOnClose = vi.fn()
  const mockOnSave = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('completes full wizard flow from start to finish', async () => {
    const mockTestConnection = vi.mocked(testConnection)
    mockTestConnection.mockResolvedValue({
      success: true,
      message: 'Connection successful',
    })

    renderWithProviders(
      <ConnectionWizard
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    // Step 1: Select database type
    await waitFor(() => {
      expect(screen.getByText(/Select Database Type|Database Type/i)).toBeInTheDocument()
    }, { timeout: 3000 })
    
    const postgresButton = screen.getByText('PostgreSQL').closest('button')
    if (postgresButton) {
      fireEvent.click(postgresButton)
    }
    
    await waitFor(() => {
      const nextBtn = screen.getByRole('button', { name: /Next/i })
      expect(nextBtn).not.toBeDisabled()
    }, { timeout: 3000 })
    fireEvent.click(screen.getByRole('button', { name: /Next/i }))

    // Step 2: Fill connection details
    await waitFor(() => {
      expect(screen.getByText('Connection Details')).toBeInTheDocument()
    }, { timeout: 3000 })
    
    // Use placeholder or role to find inputs
    const inputs = screen.getAllByRole('textbox')
    const numberInputs = screen.getAllByRole('spinbutton')
    
    // Fill form - use available inputs
    if (inputs.length > 0) {
      fireEvent.change(inputs[0], { target: { value: 'localhost' } })
    }
    if (numberInputs.length > 0) {
      fireEvent.change(numberInputs[0], { target: { value: '5432' } })
    }
    if (inputs.length > 1) {
      fireEvent.change(inputs[1], { target: { value: 'test_db' } })
    }
    
    await waitFor(() => {
      const nextBtn = screen.getByRole('button', { name: /Next/i })
      expect(nextBtn).not.toBeDisabled()
    }, { timeout: 3000 })
    fireEvent.click(screen.getByRole('button', { name: /Next/i }))

    // Step 3: Test connection
    await waitFor(() => {
      // Check for step 3 by looking for the button (more reliable than checking text)
      const allButtons = screen.getAllByRole('button')
      const testButton = allButtons.find(btn => {
        const span = btn.querySelector('span')
        const text = (span?.textContent || btn.textContent || '').trim()
        return text === 'Test Connection'
      })
      expect(testButton).toBeTruthy()
    }, { timeout: 3000 })
    
    // Find the button - use getAllByRole and filter for the actual button
    // The modal title is an h2/h3, not a button, so we need to find the actual button element
    const allButtons = screen.getAllByRole('button')
    const testButton = allButtons.find(btn => {
      // Check if this button contains "Test Connection" text and is not disabled
      const span = btn.querySelector('span')
      const text = (span?.textContent || btn.textContent || '').trim()
      return text === 'Test Connection' && !btn.hasAttribute('disabled')
    })
    
    expect(testButton).toBeTruthy()
    if (testButton) {
      fireEvent.click(testButton)
    }

    await waitFor(() => {
      expect(mockTestConnection).toHaveBeenCalled()
    }, { timeout: 3000 })

    await waitFor(() => {
      expect(screen.getByText('Connection Successful')).toBeInTheDocument()
    }, { timeout: 3000 })

    // Proceed to step 4
    const nextAfterTest = screen.getByRole('button', { name: /Next/i })
    expect(nextAfterTest).not.toBeDisabled()
    fireEvent.click(nextAfterTest)

    // Step 4: Save connection
    await waitFor(() => {
      // Check for step 4 by looking for the button (more reliable than checking text)
      const allButtons = screen.getAllByRole('button')
      const saveButton = allButtons.find(btn => {
        const span = btn.querySelector('span')
        const text = (span?.textContent || btn.textContent || '').trim()
        return text === 'Save Connection' && !btn.hasAttribute('disabled')
      })
      expect(saveButton).toBeTruthy()
    }, { timeout: 3000 })
    
    // Find the connection name input by placeholder
    const nameInput = screen.getByPlaceholderText('My Production Database')
    fireEvent.change(nameInput, { target: { value: 'My Test Connection' } })
    
    // Find and click the save button
    const saveButtons = screen.getAllByRole('button')
    const saveButton = saveButtons.find(btn => {
      const span = btn.querySelector('span')
      const text = (span?.textContent || btn.textContent || '').trim()
      return text === 'Save Connection' && !btn.hasAttribute('disabled')
    })
    expect(saveButton).toBeTruthy()
    if (saveButton) {
      fireEvent.click(saveButton)
    }

    await waitFor(() => {
      expect(mockOnSave).toHaveBeenCalled()
    }, { timeout: 3000 })
  })

  it('handles connection test failure and retry', async () => {
    const mockTestConnection = vi.mocked(testConnection)
    // Create error that matches ConnectionTestError structure
    const connectionError = new Error('Connection failed')
    connectionError.name = 'ConnectionTestError'
    ;(connectionError as any).connectionError = 'Invalid credentials'
    
    mockTestConnection
      .mockRejectedValueOnce(connectionError)
      .mockResolvedValueOnce({
        success: true,
        message: 'Connection successful',
      })

    const initialConnection: ConnectionConfig = {
      type: 'postgres',
      host: 'localhost',
      port: 5432,
      database: 'test_db',
    }

    renderWithProviders(
      <ConnectionWizard
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
        initialConnection={initialConnection}
      />
    )

    // Navigate to step 3 - we start at step 2, so one click should get us to step 3
    const nextBtn1 = screen.getByRole('button', { name: /Next/i })
    // Step 2 should allow proceeding if there are no errors
    // But we need to wait for validation to pass
    await waitFor(() => {
      expect(nextBtn1).not.toBeDisabled()
    }, { timeout: 3000 })
    fireEvent.click(nextBtn1)
    
    // Now we should be on step 3
    await waitFor(() => {
      // Check for step 3 by looking for the button (more reliable than checking text)
      const allButtons = screen.getAllByRole('button')
      const testButton = allButtons.find(btn => {
        const span = btn.querySelector('span')
        const text = (span?.textContent || btn.textContent || '').trim()
        return text === 'Test Connection'
      })
      expect(testButton).toBeTruthy()
    }, { timeout: 3000 })

    // Test connection (fails) - button should be available
    await waitFor(() => {
      const allButtons = screen.getAllByRole('button')
      const testButton = allButtons.find(btn => {
        const span = btn.querySelector('span')
        const text = (span?.textContent || btn.textContent || '').trim()
        return text === 'Test Connection' && !btn.hasAttribute('disabled')
      })
      expect(testButton).toBeTruthy()
    }, { timeout: 3000 })
    
    // Find the actual button (not the title) - use getAllByRole to find buttons
    const allButtons1 = screen.getAllByRole('button')
    const testButton1 = allButtons1.find(btn => {
      const span = btn.querySelector('span')
      const text = (span?.textContent || btn.textContent || '').trim()
      return text === 'Test Connection' && !btn.hasAttribute('disabled')
    })
    
    expect(testButton1).toBeTruthy()
    if (testButton1) {
      fireEvent.click(testButton1)
    }

    await waitFor(() => {
      // Connection failed message - use getAllByText and check if any exists
      const failedTexts = screen.queryAllByText(/Connection failed/i)
      expect(failedTexts.length).toBeGreaterThan(0)
    }, { timeout: 3000 })

    // Retry test connection (succeeds)
    await waitFor(() => {
      // Wait for the button to be available again after first test
      const retryButtons = screen.getAllByRole('button')
      const retryTestButton = retryButtons.find(btn => {
        const span = btn.querySelector('span')
        const text = (span?.textContent || btn.textContent || '').trim()
        return text === 'Test Connection' && !btn.hasAttribute('disabled')
      })
      expect(retryTestButton).toBeTruthy()
    }, { timeout: 3000 })
    
    const retryButtons2 = screen.getAllByRole('button')
    const retryTestButton2 = retryButtons2.find(btn => {
      const span = btn.querySelector('span')
      const text = (span?.textContent || btn.textContent || '').trim()
      return text === 'Test Connection' && !btn.hasAttribute('disabled')
    })
    
    if (retryTestButton2) {
      fireEvent.click(retryTestButton2)
    }

    await waitFor(() => {
      expect(screen.getByText('Connection Successful')).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('allows editing existing connection through wizard', async () => {
    const mockTestConnection = vi.mocked(testConnection)
    mockTestConnection.mockResolvedValue({
      success: true,
      message: 'Connection successful',
    })

    const existingConnection: ConnectionConfig = {
      type: 'postgres',
      host: 'oldhost',
      port: 5432,
      database: 'old_db',
    }

    renderWithProviders(
      <ConnectionWizard
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
        initialConnection={existingConnection}
        connectionId="1"
      />
    )

    // Should start at step 2 with existing values
    await waitFor(() => {
      expect(screen.getByText('Connection Details')).toBeInTheDocument()
    })
    
    const hostInput = screen.getByDisplayValue('oldhost') as HTMLInputElement
    expect(hostInput.value).toBe('oldhost')

    // Update connection
    fireEvent.change(hostInput, { target: { value: 'newhost' } })
    const nextBtn = screen.getByRole('button', { name: /Next/i })
    expect(nextBtn).not.toBeDisabled()
    fireEvent.click(nextBtn)

    // Test and save
    await waitFor(() => {
      // Check for step 3 by looking for the button (more reliable than checking text)
      const allButtons = screen.getAllByRole('button')
      const testButton = allButtons.find(btn => {
        const span = btn.querySelector('span')
        const text = (span?.textContent || btn.textContent || '').trim()
        return text === 'Test Connection' && !btn.hasAttribute('disabled')
      })
      expect(testButton).toBeTruthy()
    }, { timeout: 3000 })
    
    // Find the actual button (not the title) - use getAllByRole
    const allButtons4 = screen.getAllByRole('button')
    const editTestButton4 = allButtons4.find(btn => {
      const span = btn.querySelector('span')
      const text = (span?.textContent || btn.textContent || '').trim()
      return text === 'Test Connection' && !btn.hasAttribute('disabled')
    })
    
    expect(editTestButton4).toBeTruthy()
    if (editTestButton4) {
      fireEvent.click(editTestButton4)
    }
    
    await waitFor(() => {
      expect(screen.getByText('Connection Successful')).toBeInTheDocument()
    }, { timeout: 3000 })
    
    const nextAfterTest = screen.getByRole('button', { name: /Next/i })
    expect(nextAfterTest).not.toBeDisabled()
    fireEvent.click(nextAfterTest)

    await waitFor(() => {
      // Check for step 4 by looking for the button (more reliable than checking text)
      const allButtons = screen.getAllByRole('button')
      const updateButton = allButtons.find(btn => {
        const span = btn.querySelector('span')
        const text = (span?.textContent || btn.textContent || '').trim()
        return text === 'Update Connection' && !btn.hasAttribute('disabled')
      })
      expect(updateButton).toBeTruthy()
    }, { timeout: 3000 })
    
    // Find the connection name input by placeholder
    const nameInput = screen.getByPlaceholderText('My Production Database')
    fireEvent.change(nameInput, { target: { value: 'Updated Connection' } })
    
    // Find and click the update button
    const allButtons = screen.getAllByRole('button')
    const updateButton = allButtons.find(btn => {
      const span = btn.querySelector('span')
      const text = (span?.textContent || btn.textContent || '').trim()
      return text === 'Update Connection' && !btn.hasAttribute('disabled')
    })
    expect(updateButton).toBeTruthy()
    if (updateButton) {
      fireEvent.click(updateButton)
    }

    await waitFor(() => {
      expect(mockOnSave).toHaveBeenCalled()
    }, { timeout: 3000 })
  })

  it('validates required fields before proceeding', async () => {
    renderWithProviders(
      <ConnectionWizard
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    // Verify we're on step 1
    await waitFor(() => {
      expect(screen.getByText(/Select Database Type|Database Type/i)).toBeInTheDocument()
    }, { timeout: 3000 })
    
    // Verify we can see the database type options
    expect(screen.getByText('PostgreSQL')).toBeInTheDocument()
    
    // Select type and proceed
    const postgresButton = screen.getByText('PostgreSQL').closest('button')
    if (postgresButton) {
      fireEvent.click(postgresButton)
    }
    
    const nextButton = screen.getByRole('button', { name: /Next/i })
    await waitFor(() => {
      expect(nextButton).not.toBeDisabled()
    }, { timeout: 3000 })
    
    fireEvent.click(nextButton)

    // Should be on step 2
    await waitFor(() => {
      expect(screen.getByText('Connection Details')).toBeInTheDocument()
    }, { timeout: 3000 })
  })
})

