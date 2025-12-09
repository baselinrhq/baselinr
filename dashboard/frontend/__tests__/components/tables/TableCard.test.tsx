import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import TableCard from '@/components/tables/TableCard'
import { TableListItem } from '@/lib/api'

const mockTable: TableListItem = {
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
}

describe('TableCard', () => {
  it('renders table card with table name', () => {
    render(<TableCard table={mockTable} />)
    
    expect(screen.getByText('public.users')).toBeInTheDocument()
  })

  it('displays table metrics', () => {
    render(<TableCard table={mockTable} />)
    
    expect(screen.getByText('1,000')).toBeInTheDocument() // row_count
    expect(screen.getByText('10')).toBeInTheDocument() // column_count
    expect(screen.getByText('5')).toBeInTheDocument() // total_runs
  })

  it('shows status badges', () => {
    render(<TableCard table={mockTable} />)
    
    expect(screen.getByText(/Recent Drift/i)).toBeInTheDocument()
  })

  it('displays validation pass rate when available', () => {
    render(<TableCard table={mockTable} />)
    
    expect(screen.getByText(/95.5%/)).toBeInTheDocument()
  })

  it('handles table without schema', () => {
    const tableWithoutSchema = { ...mockTable, schema_name: null }
    render(<TableCard table={tableWithoutSchema} />)
    
    expect(screen.getByText('users')).toBeInTheDocument()
  })
})

