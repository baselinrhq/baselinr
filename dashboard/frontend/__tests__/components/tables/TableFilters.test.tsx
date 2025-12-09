import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import TableFilters from '@/components/tables/TableFilters'
import { TableListOptions } from '@/lib/api'

describe('TableFilters', () => {
  const mockFilters: TableListOptions = {
    sort_by: 'table_name',
    sort_order: 'asc',
    page: 1,
    page_size: 50
  }

  it('renders filter panel', () => {
    const onChange = vi.fn()
    render(<TableFilters filters={mockFilters} onChange={onChange} />)
    
    expect(screen.getByText('Filters')).toBeInTheDocument()
  })

  it('expands when clicked', () => {
    const onChange = vi.fn()
    render(<TableFilters filters={mockFilters} onChange={onChange} />)
    
    const button = screen.getByText('Filters').closest('button')
    fireEvent.click(button!)
    
    expect(screen.getByPlaceholderText(/Search by table name/i)).toBeInTheDocument()
  })

  it('calls onChange when search input changes', () => {
    const onChange = vi.fn()
    render(<TableFilters filters={mockFilters} onChange={onChange} />)
    
    const button = screen.getByText('Filters').closest('button')
    fireEvent.click(button!)
    
    const searchInput = screen.getByPlaceholderText(/Search by table name/i)
    fireEvent.change(searchInput, { target: { value: 'test' } })
    
    expect(onChange).toHaveBeenCalled()
  })

  it('shows active badge when filters are applied', () => {
    const filtersWithSearch: TableListOptions = {
      ...mockFilters,
      search: 'test'
    }
    const onChange = vi.fn()
    render(<TableFilters filters={filtersWithSearch} onChange={onChange} />)
    
    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  it('clears filters when clear button is clicked', () => {
    const filtersWithSearch: TableListOptions = {
      ...mockFilters,
      search: 'test',
      warehouse: 'postgres'
    }
    const onChange = vi.fn()
    render(<TableFilters filters={filtersWithSearch} onChange={onChange} />)
    
    const button = screen.getByText('Filters').closest('button')
    fireEvent.click(button!)
    
    const clearButton = screen.getByText(/Clear Filters/i)
    fireEvent.click(clearButton)
    
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        search: undefined,
        warehouse: undefined
      })
    )
  })
})

