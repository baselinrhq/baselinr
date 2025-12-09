import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import RunFilters from '@/components/runs/RunFilters'
import { RunFilters as RunFiltersType } from '@/components/runs/RunFilters'

describe('RunFilters', () => {
  const defaultFilters: RunFiltersType = {
    warehouse: '',
    schema: '',
    table: '',
    status: '',
    start_date: '',
    end_date: '',
    min_duration: undefined,
    max_duration: undefined,
    sort_by: 'profiled_at',
    sort_order: 'desc',
  }

  it('renders all filter fields', () => {
    const onChange = vi.fn()
    render(<RunFilters filters={defaultFilters} onChange={onChange} />)

    expect(screen.getByLabelText(/Warehouse/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Schema/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Table/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Status/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Start Date/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/End Date/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Min Duration/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Max Duration/i)).toBeInTheDocument()
    expect(screen.getByText(/Sort By/i)).toBeInTheDocument()
    expect(screen.getByText(/Sort Order/i)).toBeInTheDocument()
  })

  it('calls onChange when filters are updated', () => {
    const onChange = vi.fn()
    render(<RunFilters filters={defaultFilters} onChange={onChange} />)

    const schemaInput = screen.getByLabelText(/Schema/i)
    fireEvent.change(schemaInput, { target: { value: 'public' } })

    expect(onChange).toHaveBeenCalledWith({
      ...defaultFilters,
      schema: 'public',
    })
  })

  it('clears filters when clear button is clicked', () => {
    const onChange = vi.fn()
    const filtersWithValues: RunFiltersType = {
      warehouse: 'postgres',
      schema: 'public',
      table: 'users',
      status: 'completed',
      start_date: '2024-01-01',
      end_date: '2024-01-31',
      min_duration: 10,
      max_duration: 100,
      sort_by: 'row_count',
      sort_order: 'asc',
    }

    render(<RunFilters filters={filtersWithValues} onChange={onChange} />)

    const clearButton = screen.getByText(/Clear Filters/i)
    fireEvent.click(clearButton)

    expect(onChange).toHaveBeenCalledWith({
      warehouse: '',
      schema: '',
      table: '',
      status: '',
      start_date: '',
      end_date: '',
      min_duration: undefined,
      max_duration: undefined,
      sort_by: 'profiled_at',
      sort_order: 'desc',
    })
  })
})

