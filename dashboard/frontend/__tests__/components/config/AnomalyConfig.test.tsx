/**
 * Unit tests for AnomalyConfig component
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { AnomalyConfig } from '@/components/config/AnomalyConfig'
import type { StorageConfig } from '@/types/config'

describe('AnomalyConfig', () => {
  const mockStorage: StorageConfig = {
    connection: {
      type: 'postgres',
      database: 'test_db',
    },
    results_table: 'baselinr_results',
    runs_table: 'baselinr_runs',
    create_tables: true,
    enable_anomaly_detection: false,
    anomaly_enabled_methods: ['control_limits', 'iqr'],
    anomaly_iqr_threshold: 1.5,
    anomaly_mad_threshold: 3.0,
    anomaly_ewma_deviation_threshold: 2.0,
    anomaly_seasonality_enabled: true,
    anomaly_regime_shift_enabled: true,
    anomaly_regime_shift_window: 3,
    anomaly_regime_shift_sensitivity: 0.05,
  }

  it('renders anomaly detection section', () => {
    const mockOnChange = vi.fn()
    render(
      <AnomalyConfig
        storage={mockStorage}
        onChange={mockOnChange}
      />
    )

    expect(screen.getByText('Anomaly Detection')).toBeInTheDocument()
    expect(screen.getByText(/Configure automatic anomaly detection/)).toBeInTheDocument()
  })

  it('renders enable toggle', () => {
    const mockOnChange = vi.fn()
    render(
      <AnomalyConfig
        storage={mockStorage}
        onChange={mockOnChange}
      />
    )

    expect(screen.getByText('Enable Anomaly Detection')).toBeInTheDocument()
    const toggle = screen.getByRole('switch', { name: /Enable anomaly detection/i })
    expect(toggle).toBeInTheDocument()
  })

  it('renders all detection methods', () => {
    const mockOnChange = vi.fn()
    const enabledStorage: StorageConfig = {
      ...mockStorage,
      enable_anomaly_detection: true,
    }

    render(
      <AnomalyConfig
        storage={enabledStorage}
        onChange={mockOnChange}
      />
    )

    expect(screen.getByText('Control Limits')).toBeInTheDocument()
    expect(screen.getByText('IQR (Interquartile Range)')).toBeInTheDocument()
    expect(screen.getByText('MAD (Median Absolute Deviation)')).toBeInTheDocument()
    expect(screen.getByText('EWMA (Exponentially Weighted Moving Average)')).toBeInTheDocument()
    expect(screen.getByText('Seasonality Detection')).toBeInTheDocument()
    expect(screen.getByText('Regime Shift Detection')).toBeInTheDocument()
  })

  it('updates enable_anomaly_detection on toggle', async () => {
    const mockOnChange = vi.fn()
    render(
      <AnomalyConfig
        storage={mockStorage}
        onChange={mockOnChange}
      />
    )

    const toggle = screen.getByRole('switch', { name: /Enable anomaly detection/i })
    fireEvent.click(toggle)

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          enable_anomaly_detection: true,
        })
      )
    })
  })

  it('toggles detection methods on checkbox click', async () => {
    const mockOnChange = vi.fn()
    const enabledStorage: StorageConfig = {
      ...mockStorage,
      enable_anomaly_detection: true,
    }

    render(
      <AnomalyConfig
        storage={enabledStorage}
        onChange={mockOnChange}
      />
    )

    // Find the IQR section and then find the checkbox within it
    const iqrLabel = screen.getByText('IQR (Interquartile Range)')
    const iqrSection = iqrLabel.closest('.border')
    const iqrCheckbox = iqrSection?.querySelector('input[type="checkbox"]') as HTMLInputElement
    
    expect(iqrCheckbox).toBeTruthy()
    expect(iqrCheckbox).toBeChecked()

    // Uncheck it
    fireEvent.click(iqrCheckbox)

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalled()
      const call = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0]
      expect(call.anomaly_enabled_methods).not.toContain('iqr')
    })
  })

  it('shows method-specific settings when method is enabled and expanded', async () => {
    const mockOnChange = vi.fn()
    const enabledStorage: StorageConfig = {
      ...mockStorage,
      enable_anomaly_detection: true,
      anomaly_enabled_methods: ['iqr'],
    }

    render(
      <AnomalyConfig
        storage={enabledStorage}
        onChange={mockOnChange}
      />
    )

    // IQR starts expanded by default, so settings should already be visible
    // But let's verify by finding the settings button and checking if settings are shown
    const iqrLabel = screen.getByText('IQR (Interquartile Range)')
    const iqrSection = iqrLabel.closest('.border')
    const settingsButton = iqrSection?.querySelector('button[type="button"]') as HTMLButtonElement
    
    // If button says "Hide settings", settings are already expanded
    if (settingsButton?.textContent?.includes('Hide settings')) {
      // Settings are already visible, just verify
      expect(screen.getByText('IQR Threshold')).toBeInTheDocument()
    } else {
      // Click to expand
      expect(settingsButton).toBeTruthy()
      expect(settingsButton.textContent).toMatch(/Show settings/i)
      fireEvent.click(settingsButton)
      
      await waitFor(() => {
        expect(screen.getByText('IQR Threshold')).toBeInTheDocument()
      })
    }
  })

  it('updates IQR threshold on input change', async () => {
    const mockOnChange = vi.fn()
    const enabledStorage: StorageConfig = {
      ...mockStorage,
      enable_anomaly_detection: true,
      anomaly_enabled_methods: ['iqr'],
    }

    render(
      <AnomalyConfig
        storage={enabledStorage}
        onChange={mockOnChange}
      />
    )

    // IQR starts expanded, so settings should already be visible
    // Find the input (could be "1.5" or "1.50" depending on formatting)
    await waitFor(() => {
      const iqrInputs = screen.getAllByRole('spinbutton')
      const iqrInput = iqrInputs.find(
        (input) => {
          const val = (input as HTMLInputElement).value
          return val === '1.5' || val === '1.50'
        }
      ) as HTMLInputElement
      
      expect(iqrInput).toBeTruthy()
      fireEvent.change(iqrInput, { target: { value: '2.0' } })
    })

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          anomaly_iqr_threshold: 2.0,
        })
      )
    })
  })

  it('updates MAD threshold on input change', async () => {
    const mockOnChange = vi.fn()
    const enabledStorage: StorageConfig = {
      ...mockStorage,
      enable_anomaly_detection: true,
      anomaly_enabled_methods: ['mad'],
    }

    render(
      <AnomalyConfig
        storage={enabledStorage}
        onChange={mockOnChange}
      />
    )

    // Find the MAD section and click "Show settings" button to expand
    const madLabel = screen.getByText('MAD (Median Absolute Deviation)')
    const madSection = madLabel.closest('.border')
    const showSettingsButton = madSection?.querySelector('button[type="button"]') as HTMLButtonElement
    
    expect(showSettingsButton).toBeTruthy()
    fireEvent.click(showSettingsButton)

    await waitFor(() => {
      const madInput = screen.getByDisplayValue('3.0') as HTMLInputElement
      expect(madInput).toBeTruthy()
      fireEvent.change(madInput, { target: { value: '4.0' } })
    })

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          anomaly_mad_threshold: 4.0,
        })
      )
    })
  })

  it('updates seasonality toggle', async () => {
    const mockOnChange = vi.fn()
    const enabledStorage: StorageConfig = {
      ...mockStorage,
      enable_anomaly_detection: true,
      anomaly_enabled_methods: ['seasonality'],
    }

    render(
      <AnomalyConfig
        storage={enabledStorage}
        onChange={mockOnChange}
      />
    )

    // Find the seasonality section and click "Show settings" button to expand
    const seasonalityLabel = screen.getByText('Seasonality Detection')
    const seasonalitySection = seasonalityLabel.closest('.border')
    const showSettingsButton = seasonalitySection?.querySelector('button[type="button"]') as HTMLButtonElement
    
    expect(showSettingsButton).toBeTruthy()
    fireEvent.click(showSettingsButton)

    await waitFor(() => {
      const seasonalityToggle = screen.getByRole('switch', { name: /Enable seasonality and trend detection/i })
      expect(seasonalityToggle).toBeChecked()
      fireEvent.click(seasonalityToggle)
    })

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          anomaly_seasonality_enabled: false,
        })
      )
    })
  })

  it('updates regime shift settings', async () => {
    const mockOnChange = vi.fn()
    const enabledStorage: StorageConfig = {
      ...mockStorage,
      enable_anomaly_detection: true,
      anomaly_enabled_methods: ['regime_shift'],
    }

    render(
      <AnomalyConfig
        storage={enabledStorage}
        onChange={mockOnChange}
      />
    )

    // Find the regime shift section and click "Show settings" button to expand
    const regimeShiftLabel = screen.getByText('Regime Shift Detection')
    const regimeShiftSection = regimeShiftLabel.closest('.border')
    const showSettingsButton = regimeShiftSection?.querySelector('button[type="button"]') as HTMLButtonElement
    
    expect(showSettingsButton).toBeTruthy()
    fireEvent.click(showSettingsButton)

    await waitFor(() => {
      // Find window size input
      const windowInput = screen.getByDisplayValue('3') as HTMLInputElement
      expect(windowInput).toBeTruthy()
      fireEvent.change(windowInput, { target: { value: '5' } })
    })

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          anomaly_regime_shift_window: 5,
        })
      )
    })
  })

  it('shows warning when no methods are enabled', () => {
    const mockOnChange = vi.fn()
    const enabledStorage: StorageConfig = {
      ...mockStorage,
      enable_anomaly_detection: true,
      anomaly_enabled_methods: [],
    }

    render(
      <AnomalyConfig
        storage={enabledStorage}
        onChange={mockOnChange}
      />
    )

    expect(screen.getByText(/At least one detection method must be enabled/)).toBeInTheDocument()
  })

  it('shows info message when anomaly detection is disabled', () => {
    const mockOnChange = vi.fn()
    render(
      <AnomalyConfig
        storage={mockStorage}
        onChange={mockOnChange}
      />
    )

    expect(screen.getByText(/Enable anomaly detection to automatically identify/)).toBeInTheDocument()
  })

  it('disables inputs when loading', () => {
    const mockOnChange = vi.fn()
    render(
      <AnomalyConfig
        storage={mockStorage}
        onChange={mockOnChange}
        isLoading={true}
      />
    )

    const toggle = screen.getByRole('switch', { name: /Enable anomaly detection/i })
    expect(toggle).toBeDisabled()
  })

  it('displays error messages', () => {
    const mockOnChange = vi.fn()
    const errors = {
      anomaly_enabled_methods: 'At least one method must be enabled',
      anomaly_iqr_threshold: 'IQR threshold must be between 0.1 and 5.0',
    }

    const enabledStorage: StorageConfig = {
      ...mockStorage,
      enable_anomaly_detection: true,
    }

    render(
      <AnomalyConfig
        storage={enabledStorage}
        onChange={mockOnChange}
        errors={errors}
      />
    )

    expect(screen.getByText('At least one method must be enabled')).toBeInTheDocument()
  })

  it('uses default values when not provided', () => {
    const mockOnChange = vi.fn()
    const minimalStorage: StorageConfig = {
      connection: {
        type: 'postgres',
        database: 'test_db',
      },
      enable_anomaly_detection: true,
    }

    render(
      <AnomalyConfig
        storage={minimalStorage}
        onChange={mockOnChange}
      />
    )

    // Should render with default methods
    expect(screen.getByText('Control Limits')).toBeInTheDocument()
    expect(screen.getByText('IQR (Interquartile Range)')).toBeInTheDocument()
  })
})

