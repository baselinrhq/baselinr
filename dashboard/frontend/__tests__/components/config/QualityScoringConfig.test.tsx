/**
 * Unit tests for QualityScoringConfig component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QualityScoringConfig } from '@/components/config/QualityScoringConfig'
import type { QualityScoringConfig as QualityScoringConfigType } from '@/types/config'

describe('QualityScoringConfig', () => {
  const mockConfig: QualityScoringConfigType = {
    enabled: true,
    weights: {
      completeness: 25,
      validity: 25,
      consistency: 20,
      freshness: 15,
      uniqueness: 10,
      accuracy: 5,
    },
    thresholds: {
      healthy: 80,
      warning: 60,
      critical: 0,
    },
    freshness: {
      excellent: 24,
      good: 48,
      acceptable: 168,
    },
    store_history: true,
    history_retention_days: 90,
  }

  const mockOnChange = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders quality scoring configuration form', () => {
    render(
      <QualityScoringConfig config={mockConfig} onChange={mockOnChange} />
    )

    expect(screen.getByText('Enable Quality Scoring')).toBeInTheDocument()
    expect(screen.getByText('Component Weights')).toBeInTheDocument()
    expect(screen.getByText('Score Thresholds')).toBeInTheDocument()
    expect(screen.getByText('Freshness Thresholds (hours)')).toBeInTheDocument()
  })

  it('renders all weight inputs', () => {
    render(
      <QualityScoringConfig config={mockConfig} onChange={mockOnChange} />
    )

    // Check that labels exist
    expect(screen.getByText('Completeness')).toBeInTheDocument()
    expect(screen.getByText('Validity')).toBeInTheDocument()
    expect(screen.getByText('Consistency')).toBeInTheDocument()
    expect(screen.getByText('Freshness')).toBeInTheDocument()
    expect(screen.getByText('Uniqueness')).toBeInTheDocument()
    expect(screen.getByText('Accuracy')).toBeInTheDocument()
    
    // Check that inputs exist - multiple inputs with value 25, so use getAllBy
    const inputs25 = screen.getAllByDisplayValue('25')
    expect(inputs25.length).toBeGreaterThanOrEqual(2) // At least completeness and validity
    expect(screen.getByDisplayValue('20')).toBeInTheDocument() // Consistency
    expect(screen.getByDisplayValue('15')).toBeInTheDocument() // Freshness
    expect(screen.getByDisplayValue('10')).toBeInTheDocument() // Uniqueness
    expect(screen.getByDisplayValue('5')).toBeInTheDocument() // Accuracy
  })

  it('displays total weights', () => {
    render(
      <QualityScoringConfig config={mockConfig} onChange={mockOnChange} />
    )

    expect(screen.getByText(/Total: 100\.0%/)).toBeInTheDocument()
  })

  it('validates weights sum to 100', async () => {
    const invalidConfig = {
      ...mockConfig,
      weights: {
        completeness: 50,
        validity: 50,
        consistency: 0,
        freshness: 0,
        uniqueness: 0,
        accuracy: 0,
      },
    }

    render(
      <QualityScoringConfig config={invalidConfig} onChange={mockOnChange} />
    )

    // Update completeness to make total > 100
    // Find the first input with value 50 (should be completeness)
    const inputs50 = screen.getAllByDisplayValue('50')
    const completenessInput = inputs50[0]
    fireEvent.change(completenessInput, { target: { value: '60' } })

    await waitFor(() => {
      expect(screen.getByText(/Weights must sum to 100/)).toBeInTheDocument()
    })
  })

  it('updates weight on input change', async () => {
    render(
      <QualityScoringConfig config={mockConfig} onChange={mockOnChange} />
    )

    // Find all number inputs and change the first one (completeness)
    const numberInputs = screen.getAllByRole('spinbutton')
    const completenessInput = numberInputs[0] // First number input should be completeness
    fireEvent.change(completenessInput, { target: { value: '30' } })

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalled()
    })
  })

  it('renders threshold inputs', () => {
    render(
      <QualityScoringConfig config={mockConfig} onChange={mockOnChange} />
    )

    expect(screen.getByText('Healthy (≥)')).toBeInTheDocument()
    expect(screen.getByText('Warning (≥)')).toBeInTheDocument()
    expect(screen.getByText('Critical (<)')).toBeInTheDocument()
    
    // Check that inputs exist by their values
    expect(screen.getByDisplayValue('80')).toBeInTheDocument()
    expect(screen.getByDisplayValue('60')).toBeInTheDocument()
    expect(screen.getByDisplayValue('0')).toBeInTheDocument()
  })

  it('validates thresholds are in order', async () => {
    const invalidConfig = {
      ...mockConfig,
      thresholds: {
        healthy: 50,
        warning: 80,
        critical: 0,
      },
    }

    render(
      <QualityScoringConfig config={invalidConfig} onChange={mockOnChange} />
    )

    await waitFor(() => {
      expect(screen.getByText(/Thresholds must be in order/)).toBeInTheDocument()
    })
  })

  it('renders freshness threshold inputs', () => {
    render(
      <QualityScoringConfig config={mockConfig} onChange={mockOnChange} />
    )

    expect(screen.getByText('Excellent (≤ hours)')).toBeInTheDocument()
    expect(screen.getByText('Good (≤ hours)')).toBeInTheDocument()
    expect(screen.getByText('Acceptable (≤ hours)')).toBeInTheDocument()
    
    // Check that inputs exist by their values
    expect(screen.getByDisplayValue('24')).toBeInTheDocument()
    expect(screen.getByDisplayValue('48')).toBeInTheDocument()
    expect(screen.getByDisplayValue('168')).toBeInTheDocument()
  })

  it('validates freshness thresholds are in order', async () => {
    const invalidConfig = {
      ...mockConfig,
      freshness: {
        excellent: 100,
        good: 50,
        acceptable: 200,
      },
    }

    render(
      <QualityScoringConfig config={invalidConfig} onChange={mockOnChange} />
    )

    await waitFor(() => {
      expect(screen.getByText(/Freshness thresholds must be in order/)).toBeInTheDocument()
    })
  })

  it('renders history settings', () => {
    render(
      <QualityScoringConfig config={mockConfig} onChange={mockOnChange} />
    )

    expect(screen.getByText(/Store score history/i)).toBeInTheDocument()
    expect(screen.getByText(/History Retention \(days\)/i)).toBeInTheDocument()
  })

  it('toggles store history', async () => {
    render(
      <QualityScoringConfig config={mockConfig} onChange={mockOnChange} />
    )

    const toggle = screen.getByRole('switch', { name: /Store score history/i })
    fireEvent.click(toggle)

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalled()
    })
  })

  it('hides history retention when history is disabled', () => {
    const configWithoutHistory = {
      ...mockConfig,
      store_history: false,
    }

    render(
      <QualityScoringConfig config={configWithoutHistory} onChange={mockOnChange} />
    )

    expect(screen.queryByText(/History Retention \(days\)/i)).not.toBeInTheDocument()
  })

  it('updates history retention days', async () => {
    render(
      <QualityScoringConfig config={mockConfig} onChange={mockOnChange} />
    )

    // Find input by its current value (90)
    const retentionInput = screen.getByDisplayValue('90')
    fireEvent.change(retentionInput, { target: { value: '180' } })

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalled()
    })
  })

  it('toggles enabled state', async () => {
    render(
      <QualityScoringConfig config={mockConfig} onChange={mockOnChange} />
    )

    const toggle = screen.getByRole('switch', { name: /Enable quality scoring/i })
    fireEvent.click(toggle)

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalled()
    })
  })

  it('disables inputs when loading', () => {
    render(
      <QualityScoringConfig config={mockConfig} onChange={mockOnChange} isLoading={true} />
    )

    // Find all number inputs - they should all be disabled
    const numberInputs = screen.getAllByRole('spinbutton')
    expect(numberInputs.length).toBeGreaterThan(0)
    // All inputs should be disabled when loading
    numberInputs.forEach(input => {
      expect(input).toBeDisabled()
    })
  })

  it('displays error messages', () => {
    const errors = {
      weights: 'Weights validation failed',
    }

    render(
      <QualityScoringConfig config={mockConfig} onChange={mockOnChange} errors={errors} />
    )

    // Error should be displayed (implementation may vary)
    expect(screen.getByText('Weights validation failed')).toBeInTheDocument()
  })

  it('prevents weights from exceeding 100', async () => {
    render(
      <QualityScoringConfig config={mockConfig} onChange={mockOnChange} />
    )

    // Find all number inputs and use the first one
    const numberInputs = screen.getAllByRole('spinbutton')
    const completenessInput = numberInputs[0]
    fireEvent.change(completenessInput, { target: { value: '150' } })

    await waitFor(() => {
      // Input should be clamped to 100
      expect(completenessInput).toHaveValue(100)
    })
  })

  it('prevents negative weights', async () => {
    render(
      <QualityScoringConfig config={mockConfig} onChange={mockOnChange} />
    )

    // Find all number inputs and use the first one
    const numberInputs = screen.getAllByRole('spinbutton')
    const completenessInput = numberInputs[0]
    fireEvent.change(completenessInput, { target: { value: '-10' } })

    await waitFor(() => {
      // Input should be clamped to 0
      expect(completenessInput).toHaveValue(0)
    })
  })
})









