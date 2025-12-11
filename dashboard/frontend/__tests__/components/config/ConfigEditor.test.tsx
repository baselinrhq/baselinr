/**
 * Unit tests for ConfigEditor component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ConfigEditor } from '@/components/config/ConfigEditor'
import { useConfig } from '@/hooks/useConfig'
import type { BaselinrConfig } from '@/types/config'

// Mock useConfig hook
vi.mock('@/hooks/useConfig')

// Mock YAMLPreview
vi.mock('@/components/config/YAMLPreview', () => ({
  YAMLPreview: ({ yaml, onChange }: any) => (
    <div data-testid="yaml-preview">
      <textarea
        data-testid="yaml-input"
        value={yaml}
        onChange={(e) => onChange && onChange(e.target.value)}
      />
    </div>
  ),
}))

// Mock YAML utilities
vi.mock('@/lib/utils/yaml', () => ({
  toYAML: (config: any) => {
    return `environment: ${config.environment || 'development'}\nsource:\n  type: ${config.source?.type || 'postgres'}`
  },
  parseYAML: (yaml: string) => {
    if (yaml.includes('invalid')) {
      throw new Error('Invalid YAML')
    }
    return {
      environment: 'development',
      source: { type: 'postgres', database: 'test_db' },
      storage: { connection: { type: 'postgres', database: 'storage_db' } },
    }
  },
}))

describe('ConfigEditor', () => {
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

  const mockUpdateConfig = vi.fn()
  const mockLoadConfig = vi.fn()
  const mockSaveConfig = vi.fn()
  const mockValidateConfig = vi.fn()
  const mockResetConfig = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    ;(useConfig as any).mockReturnValue({
      currentConfig: mockConfig,
      modifiedConfig: null,
      loadConfig: mockLoadConfig,
      updateConfig: mockUpdateConfig,
      resetConfig: mockResetConfig,
      saveConfig: mockSaveConfig,
      validateConfig: mockValidateConfig,
      isLoading: false,
      error: null,
      validationErrors: [],
      validationWarnings: [],
      isDirty: false,
    })
  })

  it('renders config editor', () => {
    render(<ConfigEditor />)
    expect(screen.getByText('Configuration Editor')).toBeInTheDocument()
  })

  it('displays view mode toggle buttons', () => {
    render(<ConfigEditor />)
    expect(screen.getByText('Split')).toBeInTheDocument()
    expect(screen.getByText('Visual')).toBeInTheDocument()
    expect(screen.getByText('YAML')).toBeInTheDocument()
  })

  it('switches to visual-only view', () => {
    render(<ConfigEditor />)
    const visualButton = screen.getByText('Visual')
    fireEvent.click(visualButton)
    
    expect(screen.queryByTestId('yaml-preview')).not.toBeInTheDocument()
  })

  it('switches to YAML-only view', () => {
    render(<ConfigEditor />)
    const yamlButton = screen.getByText('YAML')
    fireEvent.click(yamlButton)
    
    expect(screen.getByTestId('yaml-preview')).toBeInTheDocument()
  })

  it('displays save and validate buttons', () => {
    render(<ConfigEditor />)
    expect(screen.getByText('Save')).toBeInTheDocument()
    expect(screen.getByText('Validate')).toBeInTheDocument()
  })

  it('calls saveConfig when save button is clicked', async () => {
    ;(useConfig as any).mockReturnValue({
      currentConfig: mockConfig,
      modifiedConfig: null,
      loadConfig: mockLoadConfig,
      updateConfig: mockUpdateConfig,
      resetConfig: mockResetConfig,
      saveConfig: mockSaveConfig,
      validateConfig: mockValidateConfig,
      isLoading: false,
      error: null,
      validationErrors: [],
      validationWarnings: [],
      isDirty: true,
    })

    render(<ConfigEditor />)
    
    const saveButton = screen.getByText('Save')
    fireEvent.click(saveButton)
    
    await waitFor(() => {
      expect(mockSaveConfig).toHaveBeenCalled()
    })
  })

  it('calls validateConfig when validate button is clicked', async () => {
    mockValidateConfig.mockResolvedValue(true)
    
    render(<ConfigEditor />)
    
    const validateButton = screen.getByText('Validate')
    fireEvent.click(validateButton)
    
    await waitFor(() => {
      expect(mockValidateConfig).toHaveBeenCalled()
    })
  })

  it('disables save button when config is not dirty', () => {
    ;(useConfig as any).mockReturnValue({
      currentConfig: mockConfig,
      modifiedConfig: null,
      loadConfig: mockLoadConfig,
      updateConfig: mockUpdateConfig,
      resetConfig: mockResetConfig,
      saveConfig: mockSaveConfig,
      validateConfig: mockValidateConfig,
      isLoading: false,
      error: null,
      validationErrors: [],
      validationWarnings: [],
      isDirty: false,
    })

    render(<ConfigEditor />)
    
    const saveButton = screen.getByText('Save').closest('button')
    // Save button is disabled when not dirty OR when saving
    // Check both the disabled attribute and the toBeDisabled matcher
    expect(saveButton).toHaveAttribute('disabled')
    expect(saveButton).toBeDisabled()
  })

  it('shows validation errors', () => {
    ;(useConfig as any).mockReturnValue({
      currentConfig: mockConfig,
      modifiedConfig: null,
      loadConfig: mockLoadConfig,
      updateConfig: mockUpdateConfig,
      resetConfig: mockResetConfig,
      saveConfig: mockSaveConfig,
      validateConfig: mockValidateConfig,
      isLoading: false,
      error: null,
      validationErrors: ['Error 1', 'Error 2'],
      validationWarnings: [],
      isDirty: false,
    })

    render(<ConfigEditor />)
    
    expect(screen.getByText(/2 error/i)).toBeInTheDocument()
  })

  it('shows loading state', () => {
    ;(useConfig as any).mockReturnValue({
      currentConfig: null,
      modifiedConfig: null,
      loadConfig: mockLoadConfig,
      updateConfig: mockUpdateConfig,
      resetConfig: mockResetConfig,
      saveConfig: mockSaveConfig,
      validateConfig: mockValidateConfig,
      isLoading: true,
      error: null,
      validationErrors: [],
      validationWarnings: [],
      isDirty: false,
    })

    render(<ConfigEditor />)
    
    expect(screen.getByText('Loading configuration...')).toBeInTheDocument()
  })

  it('loads config on mount if not loaded', async () => {
    ;(useConfig as any).mockReturnValue({
      currentConfig: null,
      modifiedConfig: null,
      loadConfig: mockLoadConfig,
      updateConfig: mockUpdateConfig,
      resetConfig: mockResetConfig,
      saveConfig: mockSaveConfig,
      validateConfig: mockValidateConfig,
      isLoading: false,
      error: null,
      validationErrors: [],
      validationWarnings: [],
      isDirty: false,
    })

    render(<ConfigEditor />)
    
    // loadConfig is called in useEffect, may need to wait
    await waitFor(() => {
      expect(mockLoadConfig).toHaveBeenCalled()
    }, { timeout: 1000 })
  })
})

