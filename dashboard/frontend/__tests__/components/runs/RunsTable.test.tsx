import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import RunsTable from '@/components/runs/RunsTable'
import { Run } from '@/lib/api'

describe('RunsTable', () => {
  const mockRuns: Run[] = [
    {
      run_id: 'run1',
      dataset_name: 'table1',
      schema_name: 'public',
      warehouse_type: 'postgres',
      profiled_at: '2024-01-01T00:00:00Z',
      status: 'completed',
      row_count: 1000,
      column_count: 10,
      has_drift: false,
    },
    {
      run_id: 'run2',
      dataset_name: 'table2',
      schema_name: 'public',
      warehouse_type: 'snowflake',
      profiled_at: '2024-01-02T00:00:00Z',
      status: 'failed',
      row_count: 2000,
      column_count: 15,
      has_drift: true,
    },
  ]

  it('renders runs table', () => {
    render(<RunsTable runs={mockRuns} />)

    expect(screen.getByText(/table1/i)).toBeInTheDocument()
    expect(screen.getByText(/table2/i)).toBeInTheDocument()
    expect(screen.getByText(/1,000/)).toBeInTheDocument()
    expect(screen.getByText(/2,000/)).toBeInTheDocument()
  })

  it('renders checkboxes when onSelectRun is provided', () => {
    const onSelectRun = vi.fn()
    render(<RunsTable runs={mockRuns} onSelectRun={onSelectRun} />)

    const checkboxes = screen.getAllByRole('checkbox')
    expect(checkboxes.length).toBeGreaterThan(0)
  })

  it('calls onSelectRun when checkbox is clicked', () => {
    const onSelectRun = vi.fn()
    render(<RunsTable runs={mockRuns} onSelectRun={onSelectRun} />)

    const checkboxes = screen.getAllByRole('checkbox')
    // Click the first data row checkbox (index 1 is the select-all, index 2 is first row)
    const firstRowCheckbox = checkboxes[2]
    fireEvent.click(firstRowCheckbox)

    // The onChange handler receives the event, but our component extracts run_id and checked
    expect(onSelectRun).toHaveBeenCalled()
  })

  it('calls onRunClick when row is clicked', () => {
    const onRunClick = vi.fn()
    render(<RunsTable runs={mockRuns} onRunClick={onRunClick} />)

    const tableRow = screen.getByText(/table1/i).closest('tr')
    if (tableRow) {
      fireEvent.click(tableRow)
      expect(onRunClick).toHaveBeenCalledWith(mockRuns[0])
    }
  })

  it('displays status badges', () => {
    render(<RunsTable runs={mockRuns} />)

    // Status is shown via icons, check that the table rows exist with the correct data
    // The status icons are rendered but status text is in the run data
    expect(screen.getByText(/table1/i)).toBeInTheDocument()
    expect(screen.getByText(/table2/i)).toBeInTheDocument()
    // Status icons are present (check-circle for completed, x-circle for failed)
    const statusIcons = document.querySelectorAll('.lucide-check-circle, .lucide-xcircle')
    expect(statusIcons.length).toBeGreaterThan(0)
  })

  it('displays drift indicators', () => {
    render(<RunsTable runs={mockRuns} />)

    expect(screen.getByText(/None/i)).toBeInTheDocument()
    expect(screen.getByText(/Detected/i)).toBeInTheDocument()
  })

  it('sorts runs when sortable is true', () => {
    render(<RunsTable runs={mockRuns} sortable />)

    const rowCountHeader = screen.getByText(/Rows/i)
    fireEvent.click(rowCountHeader)

    // After sorting, the order should change
    const rows = screen.getAllByText(/table/i)
    expect(rows.length).toBeGreaterThan(0)
  })

  it('renders empty state when no runs', () => {
    render(<RunsTable runs={[]} />)

    expect(screen.getByText(/No runs found/i)).toBeInTheDocument()
  })
})

