/**
 * Unit tests for ConnectionWizard component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ConnectionWizard } from '@/components/config/ConnectionWizard'
import { testConnection } from '@/lib/api/config'
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

describe('ConnectionWizard', () => {
  const mockOnClose = vi.fn()
  const mockOnSave = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders step 1 (database type selection) when opened', () => {
    render(
      <ConnectionWizard
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    expect(screen.getByText('Select Database Type')).toBeInTheDocument()
    expect(screen.getByText('PostgreSQL')).toBeInTheDocument()
  })

  it('does not render when closed', () => {
    render(
      <ConnectionWizard
        isOpen={false}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    expect(screen.queryByText('Select Database Type')).not.toBeInTheDocument()
  })

  it('navigates to step 2 after selecting database type', () => {
    render(
      <ConnectionWizard
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    // Click on PostgreSQL
    const postgresButton = screen.getByText('PostgreSQL').closest('button')
    if (postgresButton) {
      fireEvent.click(postgresButton)
    }

    // Click Next
    const nextButton = screen.getByText('Next')
    fireEvent.click(nextButton)

    expect(screen.getByText('Connection Details')).toBeInTheDocument()
  })

  it('renders step 1 with database type selection', () => {
    render(
      <ConnectionWizard
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    // Verify we're on step 1 - check for database type options
    expect(screen.getByText('PostgreSQL')).toBeInTheDocument()
    expect(screen.getByText('Snowflake')).toBeInTheDocument()
    expect(screen.getByText('MySQL')).toBeInTheDocument()
    
    // Verify Next button exists (it's enabled by default since type defaults to 'postgres')
    expect(screen.getByText('Next')).toBeInTheDocument()
  })

  it('allows going back from step 2 to step 1', () => {
    const initialConnection: ConnectionConfig = {
      type: 'postgres',
      database: 'test_db',
    }

    render(
      <ConnectionWizard
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
        initialConnection={initialConnection}
      />
    )

    // Should start at step 2 (since initialConnection is provided)
    expect(screen.getByText('Connection Details')).toBeInTheDocument()

    // Click Back
    const backButton = screen.getByText('Back')
    fireEvent.click(backButton)

    expect(screen.getByText('Select Database Type')).toBeInTheDocument()
  })

  it('tests connection in step 3', async () => {
    const mockTestConnection = vi.mocked(testConnection)
    mockTestConnection.mockResolvedValue({
      success: true,
      message: 'Connection successful',
    })

    const initialConnection: ConnectionConfig = {
      type: 'postgres',
      host: 'localhost',
      port: 5432,
      database: 'test_db',
    }

    render(
      <ConnectionWizard
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
        initialConnection={initialConnection}
      />
    )

    // Should start at step 2, navigate to step 3
    const nextButton = screen.getByText('Next')
    fireEvent.click(nextButton)
    
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

    // Click Test Connection button
    const allButtons = screen.getAllByRole('button')
    const testButton = allButtons.find(btn => {
      const span = btn.querySelector('span')
      const text = (span?.textContent || btn.textContent || '').trim()
      return text === 'Test Connection' && !btn.hasAttribute('disabled')
    })
    
    expect(testButton).toBeTruthy()
    if (testButton) {
      fireEvent.click(testButton)

      await waitFor(() => {
        expect(mockTestConnection).toHaveBeenCalledWith(initialConnection)
      }, { timeout: 3000 })

      await waitFor(() => {
        expect(screen.getByText('Connection Successful')).toBeInTheDocument()
      }, { timeout: 3000 })
    }
  })

  it('handles connection test failure', async () => {
    const mockTestConnection = vi.mocked(testConnection)
    // Create error that will be handled properly
    const error = new Error('Connection failed: Invalid credentials')
    error.name = 'ConnectionTestError'
    mockTestConnection.mockRejectedValue(error)

    const initialConnection: ConnectionConfig = {
      type: 'postgres',
      host: 'localhost',
      port: 5432,
      database: 'test_db',
    }

    render(
      <ConnectionWizard
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
        initialConnection={initialConnection}
      />
    )

    // Navigate to step 3
    const nextButton = screen.getByText('Next')
    fireEvent.click(nextButton)
    
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

    // Click Test Connection button
    const allButtons = screen.getAllByRole('button')
    const testButton = allButtons.find(btn => {
      const span = btn.querySelector('span')
      const text = (span?.textContent || btn.textContent || '').trim()
      return text === 'Test Connection' && !btn.hasAttribute('disabled')
    })
    expect(testButton).toBeTruthy()
    if (testButton) {
      fireEvent.click(testButton)
    }

    await waitFor(() => {
      // Look for any failure indication - use queryAllByText to handle multiple matches
      const failedTexts = screen.queryAllByText(/Connection failed/i)
      expect(failedTexts.length).toBeGreaterThan(0)
    }, { timeout: 3000 })
  })

  it('requires connection name in step 4', async () => {
    const mockTestConnection = vi.mocked(testConnection)
    mockTestConnection.mockResolvedValue({
      success: true,
      message: 'Connection successful',
    })

    const initialConnection: ConnectionConfig = {
      type: 'postgres',
      host: 'localhost',
      port: 5432,
      database: 'test_db',
    }

    render(
      <ConnectionWizard
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
        initialConnection={initialConnection}
      />
    )

    // Navigate to step 3
    const nextButton = screen.getByText('Next')
    fireEvent.click(nextButton)
    
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

    // Test connection - find the button
    const allButtons = screen.getAllByRole('button')
    const testButton = allButtons.find(btn => {
      const span = btn.querySelector('span')
      const text = (span?.textContent || btn.textContent || '').trim()
      return text === 'Test Connection' && !btn.hasAttribute('disabled')
    })
    expect(testButton).toBeTruthy()
    if (testButton) {
      fireEvent.click(testButton)
    }

    await waitFor(() => {
      expect(screen.getByText('Connection Successful')).toBeInTheDocument()
    }, { timeout: 3000 })

    // Advance to step 4
    const nextButtonAfterTest = screen.getByRole('button', { name: /Next/i })
    expect(nextButtonAfterTest).not.toBeDisabled()
    fireEvent.click(nextButtonAfterTest)

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

    // Try to save without name
    const saveButton = screen.getByRole('button', { name: /Save Connection/i })
    fireEvent.click(saveButton)

    // Should show error
    await waitFor(() => {
      // Use queryAllByText to handle multiple matches
      const errorTexts = screen.queryAllByText(/Connection name is required/i)
      expect(errorTexts.length).toBeGreaterThan(0)
    }, { timeout: 3000 })
  })

  it('calls onSave with connection data when saved', async () => {
    const mockTestConnection = vi.mocked(testConnection)
    mockTestConnection.mockResolvedValue({
      success: true,
      message: 'Connection successful',
    })

    const initialConnection: ConnectionConfig = {
      type: 'postgres',
      host: 'localhost',
      port: 5432,
      database: 'test_db',
    }

    render(
      <ConnectionWizard
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
        initialConnection={initialConnection}
      />
    )

    // Navigate to step 3
    const nextButton = screen.getByText('Next')
    fireEvent.click(nextButton)
    
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

    // Test connection - find the button
    const allButtons = screen.getAllByRole('button')
    const testButton = allButtons.find(btn => {
      const span = btn.querySelector('span')
      const text = (span?.textContent || btn.textContent || '').trim()
      return text === 'Test Connection' && !btn.hasAttribute('disabled')
    })
    expect(testButton).toBeTruthy()
    if (testButton) {
      fireEvent.click(testButton)
    }

      await waitFor(() => {
        expect(screen.getByText('Connection Successful')).toBeInTheDocument()
      }, { timeout: 3000 })

      // Advance to step 4
      const nextButtonAfterTest = screen.getByText('Next')
      expect(nextButtonAfterTest).not.toBeDisabled()
      fireEvent.click(nextButtonAfterTest)

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

      // Enter connection name
      const nameInput = screen.getByPlaceholderText('My Production Database')
      fireEvent.change(nameInput, { target: { value: 'My Connection' } })

      // Save - find the button
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

  it('closes wizard when cancel is clicked', () => {
    render(
      <ConnectionWizard
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    const cancelButton = screen.getByText('Cancel')
    fireEvent.click(cancelButton)

    expect(mockOnClose).toHaveBeenCalled()
  })
})

