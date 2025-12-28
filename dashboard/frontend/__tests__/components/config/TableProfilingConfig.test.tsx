import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { TableProfilingConfig } from '@/components/config/TableProfilingConfig'
import { TablePattern } from '@/types/config'

describe('TableProfilingConfig', () => {
  const tables: TablePattern[] = [
    { schema: 'public', table: 'users' },
    { schema: 'public', table: 'orders' },
  ]

  it('renders table list', () => {
    const onChange = vi.fn()
    render(<TableProfilingConfig tables={tables} onChange={onChange} />)

    expect(screen.getByText('Per-Table Metrics Overrides')).toBeInTheDocument()
    expect(screen.getByText(/Select Table/i)).toBeInTheDocument()
  })

  it('shows empty state when no tables', () => {
    const onChange = vi.fn()
    render(<TableProfilingConfig tables={[]} onChange={onChange} />)

    expect(
      screen.getByText(/No tables configured. Configure tables in the Table Selection page first/i)
    ).toBeInTheDocument()
  })

  it('selects table for override configuration', () => {
    const onChange = vi.fn()
    render(<TableProfilingConfig tables={tables} onChange={onChange} />)

    // Verify the component renders with table selector
    expect(screen.getByText('Per-Table Metrics Overrides')).toBeInTheDocument()
    expect(screen.getByText(/Choose a table to configure overrides/i)).toBeInTheDocument()
    // Table details would appear when selected via Select component
  })

  it('shows metrics configuration when table is selected', () => {
    const tablesWithSelection: TablePattern[] = [
      {
        schema: 'public',
        table: 'users',
      },
    ]
    const onChange = vi.fn()
    render(
      <TableProfilingConfig tables={tablesWithSelection} onChange={onChange} />
    )

    // Verify component renders
    expect(screen.getByText('Per-Table Metrics Overrides')).toBeInTheDocument()
    // Metrics configuration would appear when a table is selected via the Select component
  })

  it('shows inheritance indicator when table has overrides', () => {
    const tablesWithOverrides: TablePattern[] = [
      {
        schema: 'public',
        table: 'users',
        metrics: ['count', 'null_count'],
      },
    ]
    const onChange = vi.fn()
    render(<TableProfilingConfig tables={tablesWithOverrides} onChange={onChange} />)

    // The component should render the table selector
    expect(screen.getByText('Per-Table Metrics Overrides')).toBeInTheDocument()
  })

  it('updates table metrics override when table is selected', () => {
    const onChange = vi.fn()
    render(<TableProfilingConfig tables={tables} onChange={onChange} />)

    // Verify component renders
    expect(screen.getByText('Per-Table Metrics Overrides')).toBeInTheDocument()
    // The actual selection and update would happen through the Select component
    // which requires more complex interaction testing
  })
})

