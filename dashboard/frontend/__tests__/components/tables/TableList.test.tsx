import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import TableList from '@/components/tables/TableList'
import { TableListItem } from '@/lib/api'

const mockTables: TableListItem[] = [
  {
    table_name: 'users',
    schema_name: 'public',
    warehouse_type: 'postgres',
    last_profiled: new Date().toISOString(),
    row_count: 1000,
    column_count: 10,
    total_runs: 5,
    drift_count: 2,
    validation_pass_rate: 95.5,
    has_recent_drift: true,
    has_failed_validations: false
  },
  {
    table_name: 'orders',
    schema_name: null,
    warehouse_type: 'snowflake',
    last_profiled: new Date().toISOString(),
    row_count: 5000,
    column_count: 15,
    total_runs: 10,
    drift_count: 0,
    validation_pass_rate: null,
    has_recent_drift: false,
    has_failed_validations: true
  }
]

describe('TableList', () => {
  it('renders table list', () => {
    const onSelectTable = vi.fn()
    const onSelectAll = vi.fn()
    const onSort = vi.fn()
    
    render(
      <TableList
        tables={mockTables}
        selectedTables={new Set()}
        onSelectTable={onSelectTable}
        onSelectAll={onSelectAll}
        sortBy="table_name"
        sortOrder="asc"
        onSort={onSort}
      />
    )
    
    // Table names are displayed with schema prefix when schema exists
    expect(screen.getByText('public.users')).toBeInTheDocument()
    expect(screen.getByText('orders')).toBeInTheDocument()
  })

  it('displays table information correctly', () => {
    const onSelectTable = vi.fn()
    const onSelectAll = vi.fn()
    const onSort = vi.fn()
    
    render(
      <TableList
        tables={mockTables}
        selectedTables={new Set()}
        onSelectTable={onSelectTable}
        onSelectAll={onSelectAll}
        sortBy="table_name"
        sortOrder="asc"
        onSort={onSort}
      />
    )
    
    // Check for row count (formatted with comma)
    expect(screen.getByText('1,000')).toBeInTheDocument()
    // Check for column count (may appear multiple times, so use getAllByText)
    const columnCounts = screen.getAllByText('10')
    expect(columnCounts.length).toBeGreaterThan(0)
    // Check for total runs (may appear multiple times)
    const runCounts = screen.getAllByText('5')
    expect(runCounts.length).toBeGreaterThan(0)
  })

  it('shows empty state when no tables', () => {
    const onSelectTable = vi.fn()
    const onSelectAll = vi.fn()
    const onSort = vi.fn()
    
    render(
      <TableList
        tables={[]}
        selectedTables={new Set()}
        onSelectTable={onSelectTable}
        onSelectAll={onSelectAll}
        sortBy="table_name"
        sortOrder="asc"
        onSort={onSort}
      />
    )
    
    expect(screen.getByText(/No tables found/i)).toBeInTheDocument()
  })

  it('displays drift count badges', () => {
    const onSelectTable = vi.fn()
    const onSelectAll = vi.fn()
    const onSort = vi.fn()
    
    render(
      <TableList
        tables={mockTables}
        selectedTables={new Set()}
        onSelectTable={onSelectTable}
        onSelectAll={onSelectAll}
        sortBy="table_name"
        sortOrder="asc"
        onSort={onSort}
      />
    )
    
    // Check that drift counts are present (may appear multiple times in table)
    const driftCounts = screen.getAllByText('2')
    expect(driftCounts.length).toBeGreaterThan(0) // drift_count for users
    const zeroCounts = screen.getAllByText('0')
    expect(zeroCounts.length).toBeGreaterThan(0) // drift_count for orders
  })
})

