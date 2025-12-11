/**
 * Unit tests for ConfigQuickActions component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ConfigQuickActions } from '@/components/config/ConfigQuickActions'
import { useConfig } from '@/hooks/useConfig'
import type { BaselinrConfig } from '@/types/config'

// Mock the useConfig hook
vi.mock('@/hooks/useConfig')

describe('ConfigQuickActions', () => {
  const mockConfig: BaselinrConfig = {
    environment: 'development',
    source: {
      type: 'postgres',
      database: 'test_db',
    },
    storage: {
      connection: {
        type: 'postgres',
        database: 'storage_db',
      },
      results_table: 'results',
      runs_table: 'runs',
    },
  }

  const mockValidateConfig = vi.fn()
  const mockOnValidate = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    ;(useConfig as any).mockReturnValue({
      currentConfig: mockConfig,
      validateConfig: mockValidateConfig,
      validationErrors: [],
      validationWarnings: [],
    })
  })

  it('renders quick actions title', () => {
    render(<ConfigQuickActions />)

    expect(screen.getByText('Quick Actions')).toBeInTheDocument()
  })

  it('displays all action buttons', () => {
    render(<ConfigQuickActions />)

    expect(screen.getByText('Validate Config')).toBeInTheDocument()
    expect(screen.getByText('Export Config')).toBeInTheDocument()
    expect(screen.getByText('Import Config')).toBeInTheDocument()
    expect(screen.getByText('Test Connections')).toBeInTheDocument()
  })

  it('calls validateConfig when validate button is clicked', async () => {
    mockValidateConfig.mockResolvedValue(true)

    render(<ConfigQuickActions onValidate={mockOnValidate} />)

    const validateButton = screen.getByRole('button', { name: /Validate Config/i })
    fireEvent.click(validateButton)

    await waitFor(() => {
      expect(mockValidateConfig).toHaveBeenCalledTimes(1)
    })
  })

  it('disables validate button when no config is loaded', () => {
    ;(useConfig as any).mockReturnValue({
      currentConfig: null,
      validateConfig: mockValidateConfig,
      validationErrors: [],
      validationWarnings: [],
    })

    render(<ConfigQuickActions />)

    const validateButton = screen.getByRole('button', { name: /Validate Config/i })
    expect(validateButton).toBeDisabled()
  })

  it('disables export button when no config is loaded', () => {
    ;(useConfig as any).mockReturnValue({
      currentConfig: null,
      validateConfig: mockValidateConfig,
      validationErrors: [],
      validationWarnings: [],
    })

    render(<ConfigQuickActions />)

    const exportButton = screen.getByRole('button', { name: /Export Config/i })
    expect(exportButton).toBeDisabled()
  })

  it('shows validation success message', async () => {
    mockValidateConfig.mockResolvedValue(true)

    render(<ConfigQuickActions />)

    const validateButton = screen.getByRole('button', { name: /Validate Config/i })
    fireEvent.click(validateButton)

    await waitFor(() => {
      expect(screen.getByText('Configuration is valid')).toBeInTheDocument()
    })
  })

  it('shows validation error message', async () => {
    mockValidateConfig.mockResolvedValue(false)
    ;(useConfig as any).mockReturnValue({
      currentConfig: mockConfig,
      validateConfig: mockValidateConfig,
      validationErrors: ['Error 1', 'Error 2'],
      validationWarnings: [],
    })

    render(<ConfigQuickActions />)

    const validateButton = screen.getByRole('button', { name: /Validate Config/i })
    fireEvent.click(validateButton)

    await waitFor(() => {
      expect(screen.getByText(/Validation failed/)).toBeInTheDocument()
    })
  })

  it('shows validation warnings when present', async () => {
    mockValidateConfig.mockResolvedValue(true)
    ;(useConfig as any).mockReturnValue({
      currentConfig: mockConfig,
      validateConfig: mockValidateConfig,
      validationErrors: [],
      validationWarnings: ['Warning 1'],
    })

    render(<ConfigQuickActions />)

    const validateButton = screen.getByRole('button', { name: /Validate Config/i })
    fireEvent.click(validateButton)

    await waitFor(() => {
      expect(screen.getByText(/with warnings/)).toBeInTheDocument()
    })
  })

  it('handles validation errors', async () => {
    const error = new Error('Validation failed')
    mockValidateConfig.mockRejectedValue(error)

    render(<ConfigQuickActions />)

    const validateButton = screen.getByRole('button', { name: /Validate Config/i })
    fireEvent.click(validateButton)

    await waitFor(() => {
      expect(screen.getByText('Validation failed')).toBeInTheDocument()
    })
  })

  it('calls onValidate callback when provided', async () => {
    mockValidateConfig.mockResolvedValue(true)

    render(<ConfigQuickActions onValidate={mockOnValidate} />)

    const validateButton = screen.getByRole('button', { name: /Validate Config/i })
    fireEvent.click(validateButton)

    await waitFor(() => {
      expect(mockOnValidate).toHaveBeenCalledTimes(1)
    })
  })

  it('shows loading state during validation', async () => {
    mockValidateConfig.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve(true), 100))
    )

    render(<ConfigQuickActions />)

    const validateButton = screen.getByRole('button', { name: /Validate Config/i })
    fireEvent.click(validateButton)

    expect(screen.getByText('Validating...')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.queryByText('Validating...')).not.toBeInTheDocument()
    })
  })

  it('handles export config', () => {
    // Mock URL methods
    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
    global.URL.revokeObjectURL = vi.fn()

    render(<ConfigQuickActions />)

    const exportButton = screen.getByRole('button', { name: /Export Config/i })
    
    // Just verify the button is present and clickable
    expect(exportButton).toBeInTheDocument()
    expect(exportButton).not.toBeDisabled()
    
    // Click should not throw (actual DOM manipulation is hard to test in jsdom)
    expect(() => fireEvent.click(exportButton)).not.toThrow()
  })

  it('handles import config click', () => {
    render(<ConfigQuickActions />)

    const importButton = screen.getByRole('button', { name: /Import Config/i })
    
    // Just verify the button is present and clickable
    expect(importButton).toBeInTheDocument()
    expect(importButton).not.toBeDisabled()
    
    // Click should not throw (actual DOM manipulation is hard to test in jsdom)
    expect(() => fireEvent.click(importButton)).not.toThrow()
  })

  it('handles test connections click', () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})

    render(<ConfigQuickActions />)

    const testButton = screen.getByRole('button', { name: /Test Connections/i })
    fireEvent.click(testButton)

    expect(alertSpy).toHaveBeenCalledWith('Test all connections functionality coming soon')

    alertSpy.mockRestore()
  })
})

