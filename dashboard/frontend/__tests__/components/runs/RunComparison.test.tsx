import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import RunComparison from '@/components/runs/RunComparison'
import { RunComparison as RunComparisonType } from '@/lib/api'

describe('RunComparison', () => {
  const mockComparison: RunComparisonType = {
    runs: [
      {
        run_id: 'run1',
        dataset_name: 'table1',
        schema_name: 'public',
        warehouse_type: 'postgres',
        profiled_at: '2024-01-01T00:00:00Z',
        status: 'completed',
        row_count: 1000,
        column_count: 10,
        duration_seconds: 30,
        has_drift: false,
      },
      {
        run_id: 'run2',
        dataset_name: 'table1',
        schema_name: 'public',
        warehouse_type: 'postgres',
        profiled_at: '2024-01-02T00:00:00Z',
        status: 'completed',
        row_count: 2000,
        column_count: 15,
        duration_seconds: 45,
        has_drift: true,
      },
    ],
    comparison: {
      row_count_diff: 1000,
      column_count_diff: 5,
      common_columns: ['col1', 'col2'],
      unique_columns: {},
      metric_differences: [
        {
          column: 'col1',
          metric: 'null_percent',
          run_id: 'run2',
          baseline_value: 10.5,
          current_value: 15.5,
          change_percent: 47.62,
        },
      ],
    },
  }

  it('renders comparison header', () => {
    const onClose = vi.fn()
    render(<RunComparison comparison={mockComparison} onClose={onClose} />)

    expect(screen.getByText(/Run Comparison/i)).toBeInTheDocument()
    expect(screen.getByText(/Close/i)).toBeInTheDocument()
  })

  it('displays run information', () => {
    const onClose = vi.fn()
    render(<RunComparison comparison={mockComparison} onClose={onClose} />)

    const tableElements = screen.getAllByText(/table1/i)
    expect(tableElements.length).toBeGreaterThan(0)
    const schemaElements = screen.getAllByText(/public/i)
    expect(schemaElements.length).toBeGreaterThan(0)
  })

  it('displays summary differences', () => {
    const onClose = vi.fn()
    render(<RunComparison comparison={mockComparison} onClose={onClose} />)

    expect(screen.getByText(/Row Count Difference/i)).toBeInTheDocument()
    expect(screen.getByText(/Column Count Difference/i)).toBeInTheDocument()
    expect(screen.getByText(/\+1,000/)).toBeInTheDocument()
    expect(screen.getByText(/\+5/)).toBeInTheDocument()
  })

  it('displays common columns', () => {
    const onClose = vi.fn()
    render(<RunComparison comparison={mockComparison} onClose={onClose} />)

    expect(screen.getByText(/Common Columns/i)).toBeInTheDocument()
    const col1Elements = screen.getAllByText(/col1/i)
    expect(col1Elements.length).toBeGreaterThan(0)
    expect(screen.getByText(/col2/i)).toBeInTheDocument()
  })

  it('displays metric differences', () => {
    const onClose = vi.fn()
    render(<RunComparison comparison={mockComparison} onClose={onClose} />)

    expect(screen.getByText(/Metric Differences/i)).toBeInTheDocument()
    expect(screen.getByText(/null_percent/i)).toBeInTheDocument()
    expect(screen.getByText(/47.62%/)).toBeInTheDocument()
  })

  it('calls onClose when close button is clicked', () => {
    const onClose = vi.fn()
    render(<RunComparison comparison={mockComparison} onClose={onClose} />)

    const closeButton = screen.getByText(/Close/i)
    closeButton.click()

    expect(onClose).toHaveBeenCalled()
  })
})

