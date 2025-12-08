import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import DriftPage from '@/app/config/drift/page'
import { useConfig } from '@/hooks/useConfig'

vi.mock('@/hooks/useConfig')
vi.mock('@tanstack/react-query', () => ({
  useMutation: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
}))

describe('DriftConfig Integration', () => {
  const mockUseConfig = vi.mocked(useConfig)
  const mockUpdateConfigPath = vi.fn()
  const mockSaveConfig = vi.fn()
  const mockLoadConfig = vi.fn()

  beforeEach(() => {
    mockLoadConfig.mockResolvedValue(undefined)
    mockUseConfig.mockReturnValue({
      currentConfig: {
        drift_detection: {
          strategy: 'absolute_threshold',
          absolute_threshold: {
            low_threshold: 5.0,
            medium_threshold: 15.0,
            high_threshold: 30.0,
          },
          baselines: {
            strategy: 'last_run',
            windows: {
              moving_average: 7,
              prior_period: 7,
              min_runs: 3,
            },
          },
          enable_type_specific_thresholds: true,
        },
      },
      modifiedConfig: {},
      loadConfig: mockLoadConfig,
      updateConfigPath: mockUpdateConfigPath,
      saveConfig: mockSaveConfig,
      isLoading: false,
      error: null,
      canSave: true,
    })
  })

  it('renders drift detection page', () => {
    render(<DriftPage />)
    
    expect(screen.getByText(/drift detection configuration/i)).toBeInTheDocument()
  })

  it('renders all configuration sections', () => {
    render(<DriftPage />)
    
    expect(screen.getByRole('heading', { name: /drift detection strategy/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /baseline selection/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /type-specific thresholds/i })).toBeInTheDocument()
  })

  it('calls updateConfigPath when strategy changes', async () => {
    const user = userEvent.setup()
    render(<DriftPage />)
    
    const strategyButton = screen.getByRole('button', { name: /absolute threshold/i })
    await user.click(strategyButton)
    
    const standardDevOption = screen.getAllByText(/standard deviation/i)[0]
    await user.click(standardDevOption)
    
    await waitFor(() => {
      expect(mockUpdateConfigPath).toHaveBeenCalled()
    })
  })

  it('calls updateConfigPath when baseline changes', async () => {
    const user = userEvent.setup()
    render(<DriftPage />)
    
    const baselineButton = screen.getByRole('button', { name: /last run/i })
    await user.click(baselineButton)
    
    const autoOption = screen.getByText(/auto/i)
    await user.click(autoOption)
    
    await waitFor(() => {
      expect(mockUpdateConfigPath).toHaveBeenCalled()
    })
  })

  it('shows save button', () => {
    render(<DriftPage />)
    
    expect(screen.getByRole('button', { name: /save configuration/i })).toBeInTheDocument()
  })

  it('handles loading state', () => {
    mockUseConfig.mockReturnValue({
      currentConfig: null,
      modifiedConfig: {},
      loadConfig: mockLoadConfig,
      updateConfigPath: mockUpdateConfigPath,
      saveConfig: mockSaveConfig,
      isLoading: true,
      error: null,
      canSave: false,
    })
    
    render(<DriftPage />)
    
    // Should show loading spinner (Loader2 component)
    const loader = document.querySelector('.animate-spin')
    expect(loader).toBeTruthy()
  })

  it('handles error state', () => {
    mockUseConfig.mockReturnValue({
      currentConfig: null,
      modifiedConfig: {},
      loadConfig: mockLoadConfig,
      updateConfigPath: mockUpdateConfigPath,
      saveConfig: mockSaveConfig,
      isLoading: false,
      error: new Error('Failed to load'),
      canSave: false,
    })
    
    render(<DriftPage />)
    
    expect(screen.getByText(/failed to load configuration/i)).toBeInTheDocument()
  })
})

