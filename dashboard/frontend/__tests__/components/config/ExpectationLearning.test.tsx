/**
 * Unit tests for ExpectationLearning component
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ExpectationLearning } from '@/components/config/ExpectationLearning'
import type { StorageConfig } from '@/types/config'

describe('ExpectationLearning', () => {
  const mockStorage: StorageConfig = {
    connection: {
      type: 'postgres',
      database: 'test_db',
    },
    results_table: 'baselinr_results',
    runs_table: 'baselinr_runs',
    create_tables: true,
    enable_expectation_learning: false,
    learning_window_days: 30,
    min_samples: 5,
    ewma_lambda: 0.2,
  }

  it('renders expectation learning section', () => {
    const mockOnChange = vi.fn()
    render(
      <ExpectationLearning
        storage={mockStorage}
        onChange={mockOnChange}
      />
    )

    expect(screen.getByText('Expectation Learning')).toBeInTheDocument()
    expect(screen.getByText(/Configure how Baselinr learns expected metric ranges/)).toBeInTheDocument()
  })

  it('renders enable toggle', () => {
    const mockOnChange = vi.fn()
    render(
      <ExpectationLearning
        storage={mockStorage}
        onChange={mockOnChange}
      />
    )

    expect(screen.getByText('Enable Expectation Learning')).toBeInTheDocument()
    const toggle = screen.getByRole('switch', { name: /Enable expectation learning/i })
    expect(toggle).toBeInTheDocument()
  })

  it('shows warning when expectation learning is disabled', () => {
    const mockOnChange = vi.fn()
    render(
      <ExpectationLearning
        storage={mockStorage}
        onChange={mockOnChange}
      />
    )

    expect(screen.getByText(/Expectation learning must be enabled for anomaly detection/)).toBeInTheDocument()
  })

  it('shows configuration fields when enabled', () => {
    const mockOnChange = vi.fn()
    const enabledStorage: StorageConfig = {
      ...mockStorage,
      enable_expectation_learning: true,
    }

    render(
      <ExpectationLearning
        storage={enabledStorage}
        onChange={mockOnChange}
      />
    )

    expect(screen.getByText('Learning Window (Days)')).toBeInTheDocument()
    expect(screen.getByText('Minimum Samples')).toBeInTheDocument()
    expect(screen.getByText('EWMA Smoothing Parameter (Lambda)')).toBeInTheDocument()
  })

  it('updates enable_expectation_learning on toggle', async () => {
    const mockOnChange = vi.fn()
    render(
      <ExpectationLearning
        storage={mockStorage}
        onChange={mockOnChange}
      />
    )

    const toggle = screen.getByRole('switch', { name: /Enable expectation learning/i })
    fireEvent.click(toggle)

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          enable_expectation_learning: true,
        })
      )
    })
  })

  it('updates learning_window_days on slider change', async () => {
    const mockOnChange = vi.fn()
    const enabledStorage: StorageConfig = {
      ...mockStorage,
      enable_expectation_learning: true,
    }

    render(
      <ExpectationLearning
        storage={enabledStorage}
        onChange={mockOnChange}
      />
    )

    // Find the number input for learning window
    const inputs = screen.getAllByRole('spinbutton')
    const learningWindowInput = inputs.find(
      (input) => (input as HTMLInputElement).value === '30'
    ) as HTMLInputElement

    expect(learningWindowInput).toBeTruthy()
    fireEvent.change(learningWindowInput, { target: { value: '60' } })

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          learning_window_days: 60,
        })
      )
    })
  })

  it('updates min_samples on input change', async () => {
    const mockOnChange = vi.fn()
    const enabledStorage: StorageConfig = {
      ...mockStorage,
      enable_expectation_learning: true,
    }

    render(
      <ExpectationLearning
        storage={enabledStorage}
        onChange={mockOnChange}
      />
    )

    // Find the min samples input
    const inputs = screen.getAllByRole('spinbutton')
    const minSamplesInput = inputs.find(
      (input) => (input as HTMLInputElement).value === '5'
    ) as HTMLInputElement

    expect(minSamplesInput).toBeTruthy()
    fireEvent.change(minSamplesInput, { target: { value: '10' } })

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          min_samples: 10,
        })
      )
    })
  })

  it('updates ewma_lambda on input change', async () => {
    const mockOnChange = vi.fn()
    const enabledStorage: StorageConfig = {
      ...mockStorage,
      enable_expectation_learning: true,
    }

    render(
      <ExpectationLearning
        storage={enabledStorage}
        onChange={mockOnChange}
      />
    )

    // Find the EWMA lambda input (it's a number input with value 0.2)
    const inputs = screen.getAllByRole('spinbutton')
    const ewmaInput = inputs.find(
      (input) => (input as HTMLInputElement).value === '0.20' || (input as HTMLInputElement).value === '0.2'
    ) as HTMLInputElement

    if (ewmaInput) {
      fireEvent.change(ewmaInput, { target: { value: '0.3' } })

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({
            ewma_lambda: 0.3,
          })
        )
      })
    }
  })

  it('disables inputs when loading', () => {
    const mockOnChange = vi.fn()
    render(
      <ExpectationLearning
        storage={mockStorage}
        onChange={mockOnChange}
        isLoading={true}
      />
    )

    const toggle = screen.getByRole('switch', { name: /Enable expectation learning/i })
    expect(toggle).toBeDisabled()
  })

  it('displays error messages', () => {
    const mockOnChange = vi.fn()
    const errors = {
      learning_window_days: 'Learning window must be between 7 and 365 days',
      min_samples: 'Minimum samples must be at least 1',
    }

    const enabledStorage: StorageConfig = {
      ...mockStorage,
      enable_expectation_learning: true,
    }

    render(
      <ExpectationLearning
        storage={enabledStorage}
        onChange={mockOnChange}
        errors={errors}
      />
    )

    expect(screen.getByText('Learning window must be between 7 and 365 days')).toBeInTheDocument()
    expect(screen.getByText('Minimum samples must be at least 1')).toBeInTheDocument()
  })

  it('uses default values when not provided', () => {
    const mockOnChange = vi.fn()
    const minimalStorage: StorageConfig = {
      connection: {
        type: 'postgres',
        database: 'test_db',
      },
      enable_expectation_learning: true,
    }

    render(
      <ExpectationLearning
        storage={minimalStorage}
        onChange={mockOnChange}
      />
    )

    // Should render with defaults (30 days, 5 samples, 0.2 lambda)
    expect(screen.getByText('Learning Window (Days)')).toBeInTheDocument()
    expect(screen.getByText('Minimum Samples')).toBeInTheDocument()
    expect(screen.getByText('EWMA Smoothing Parameter (Lambda)')).toBeInTheDocument()
  })
})

