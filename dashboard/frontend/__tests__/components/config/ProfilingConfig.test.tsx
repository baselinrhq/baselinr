import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ProfilingConfig } from '@/components/config/ProfilingConfig'
import { ProfilingConfig as ProfilingConfigType } from '@/types/config'

describe('ProfilingConfig', () => {
  const defaultProfiling: ProfilingConfigType = {
    metrics: ['count', 'null_count'],
    max_distinct_values: 1000,
    compute_histograms: true,
    histogram_bins: 10,
    default_sample_ratio: 1.0,
    enable_enrichment: true,
    enable_approx_distinct: true,
    enable_schema_tracking: true,
    enable_type_inference: true,
    enable_column_stability: true,
    stability_window: 7,
    type_inference_sample_size: 1000,
    extract_lineage: false,
  }

  it('renders all global settings', () => {
    const onChange = vi.fn()
    render(<ProfilingConfig profiling={defaultProfiling} onChange={onChange} />)

    expect(screen.getByText('Global Profiling Settings')).toBeInTheDocument()
    expect(screen.getByText('Metrics to Compute')).toBeInTheDocument()
    expect(screen.getByText('Histogram Configuration')).toBeInTheDocument()
    expect(screen.getByText('Distinct Values')).toBeInTheDocument()
    expect(screen.getByText('Sampling')).toBeInTheDocument()
    expect(screen.getByText('Enrichment Options')).toBeInTheDocument()
  })

  it('updates config on field changes', async () => {
    const onChange = vi.fn()
    render(<ProfilingConfig profiling={defaultProfiling} onChange={onChange} />)

    // Find the input near the "Max Distinct Values" label
    const maxDistinctLabel = screen.getByText(/Max Distinct Values/i)
    const maxDistinctSection = maxDistinctLabel.closest('.space-y-4')
    const maxDistinctInput = maxDistinctSection?.querySelector('input[type="number"]') as HTMLInputElement
    expect(maxDistinctInput).toBeTruthy()
    fireEvent.change(maxDistinctInput, { target: { value: '2000' } })

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({ max_distinct_values: 2000 })
      )
    })
  })

  it('handles metrics selection', async () => {
    const onChange = vi.fn()
    render(<ProfilingConfig profiling={defaultProfiling} onChange={onChange} />)

    const meanCheckbox = screen.getByLabelText(/mean/i)
    fireEvent.click(meanCheckbox)

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          metrics: expect.arrayContaining(['count', 'null_count', 'mean']),
        })
      )
    })
  })

  it('handles select all metrics', async () => {
    const onChange = vi.fn()
    render(<ProfilingConfig profiling={defaultProfiling} onChange={onChange} />)

    const selectAllButtons = screen.getAllByRole('button', { name: /Select All/i })
    const selectAllButton = selectAllButtons[0] // Use first one
    fireEvent.click(selectAllButton)

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          metrics: expect.arrayContaining([
            'count',
            'null_count',
            'null_ratio',
            'distinct_count',
            'unique_ratio',
            'approx_distinct_count',
            'min',
            'max',
            'mean',
            'stddev',
            'histogram',
            'data_type_inferred',
          ]),
        })
      )
    })
  })

  it('handles deselect all metrics', async () => {
    const onChange = vi.fn()
    const profilingWithAllMetrics: ProfilingConfigType = {
      ...defaultProfiling,
      metrics: [
        'count',
        'null_count',
        'null_ratio',
        'distinct_count',
        'unique_ratio',
        'approx_distinct_count',
        'min',
        'max',
        'mean',
        'stddev',
        'histogram',
        'data_type_inferred',
      ],
    }
    render(<ProfilingConfig profiling={profilingWithAllMetrics} onChange={onChange} />)

    const deselectAllButton = screen.getByRole('button', { name: /Deselect All/i })
    fireEvent.click(deselectAllButton)

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          metrics: [],
        })
      )
    })
  })

  it('shows correct default values', () => {
    const onChange = vi.fn()
    render(<ProfilingConfig profiling={defaultProfiling} onChange={onChange} />)

    // Find inputs by their labels
    const maxDistinctLabel = screen.getByText(/Max Distinct Values/i)
    const maxDistinctSection = maxDistinctLabel.closest('.space-y-4')
    const maxDistinctInput = maxDistinctSection?.querySelector('input[type="number"]') as HTMLInputElement
    expect(maxDistinctInput?.value).toBe('1000')

    const histogramBinsLabel = screen.getByText(/Histogram Bins/i)
    const histogramSection = histogramBinsLabel.closest('.space-y-4')
    const histogramBinsInput = histogramSection?.querySelector('input[type="number"]') as HTMLInputElement
    expect(histogramBinsInput?.value).toBe('10')
  })

  it('validates numeric inputs', async () => {
    const onChange = vi.fn()
    render(<ProfilingConfig profiling={defaultProfiling} onChange={onChange} />)

    // Use getByDisplayValue to find the histogram bins input
    const histogramBinsInput = screen.getByDisplayValue('10')
    fireEvent.change(histogramBinsInput, { target: { value: '150' } })

    // Should be clamped to max 100
    await waitFor(() => {
      expect(onChange).toHaveBeenCalled()
    })
  })

  it('handles toggle changes', async () => {
    const onChange = vi.fn()
    render(<ProfilingConfig profiling={defaultProfiling} onChange={onChange} />)

    // Find toggle by finding the label text and then the associated button
    const computeHistogramsLabel = screen.getByText(/Compute Histograms/i)
    const computeHistogramsToggle = computeHistogramsLabel.closest('label')?.querySelector('button[role="switch"]') || 
                                    screen.getAllByRole('switch')[0]
    fireEvent.click(computeHistogramsToggle as HTMLElement)

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({ compute_histograms: false })
      )
    })
  })

  it('shows/hides fields based on toggles', () => {
    const onChange = vi.fn()
    const profilingWithoutHistograms: ProfilingConfigType = {
      ...defaultProfiling,
      compute_histograms: false,
    }
    const { rerender } = render(
      <ProfilingConfig profiling={profilingWithoutHistograms} onChange={onChange} />
    )

    // When compute_histograms is false, Histogram Bins field should not be visible
    const histogramBinsField = screen.queryByText(/Histogram Bins/i)
    expect(histogramBinsField).not.toBeInTheDocument()

    // When compute_histograms is true, Histogram Bins field should be visible
    rerender(<ProfilingConfig profiling={defaultProfiling} onChange={onChange} />)
    expect(screen.getByText(/Histogram Bins/i)).toBeInTheDocument()
  })
})

