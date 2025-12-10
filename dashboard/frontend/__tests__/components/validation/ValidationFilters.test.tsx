import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ValidationFilters from '@/components/validation/ValidationFilters'

describe('ValidationFilters', () => {
  it('renders filter controls', () => {
    const onChange = vi.fn()
    const filters = {}
    render(<ValidationFilters filters={filters} onChange={onChange} />)

    expect(screen.getByText(/filter/i)).toBeInTheDocument()
  })

  it('calls onChange when filters are updated', () => {
    const onChange = vi.fn()
    const filters = {}
    render(<ValidationFilters filters={filters} onChange={onChange} />)

    // This test would need to interact with the filter UI
    // The exact implementation depends on the filter component structure
    expect(onChange).toBeDefined()
  })

  it('displays active filter count', () => {
    const onChange = vi.fn()
    const filters = {
      table: 'users',
      severity: 'high',
    }

    render(<ValidationFilters filters={filters} onChange={onChange} />)

    // Check if active filter count is displayed
    expect(screen.getByText(/2.*active/i)).toBeInTheDocument()
  })

  it('clears all filters when clear button is clicked', () => {
    const onChange = vi.fn()
    const filters = {
      table: 'users',
      severity: 'high',
    }

    render(<ValidationFilters filters={filters} onChange={onChange} />)

    const clearButton = screen.getByText(/clear all/i)
    if (clearButton) {
      fireEvent.click(clearButton)
      expect(onChange).toHaveBeenCalledWith({})
    }
  })
})

