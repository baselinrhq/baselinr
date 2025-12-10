import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import LineageFilters from '@/components/lineage/LineageFilters'
import type { LineageFilters as LineageFiltersType } from '@/types/lineage'

describe('LineageFilters', () => {
  const mockOnChange = vi.fn()
  const defaultFilters: LineageFiltersType = {}

  it('renders filter controls', () => {
    render(
      <LineageFilters
        filters={defaultFilters}
        onChange={mockOnChange}
      />
    )
    expect(screen.getByText('Filters')).toBeInTheDocument()
  })

  it('displays active filter count', () => {
    const filters: LineageFiltersType = {
      providers: ['dbt_manifest'],
      node_type: 'table',
      has_drift: true,
    }
    render(
      <LineageFilters
        filters={filters}
        onChange={mockOnChange}
      />
    )
    expect(screen.getByText(/3 active/)).toBeInTheDocument()
  })

  it('expands and collapses filters', () => {
    render(
      <LineageFilters
        filters={defaultFilters}
        onChange={mockOnChange}
      />
    )
    
    const expandButton = screen.getByText('Expand')
    fireEvent.click(expandButton)
    
    expect(screen.getByText('Collapse')).toBeInTheDocument()
    expect(screen.getByText('Quick Filters')).toBeInTheDocument()
  })

  it('clears all filters', () => {
    const filters: LineageFiltersType = {
      providers: ['dbt_manifest'],
      node_type: 'table',
    }
    render(
      <LineageFilters
        filters={filters}
        onChange={mockOnChange}
      />
    )
    
    const clearButton = screen.getByText('Clear all')
    fireEvent.click(clearButton)
    
    expect(mockOnChange).toHaveBeenCalledWith({})
  })

  it('applies filter presets', () => {
    render(
      <LineageFilters
        filters={defaultFilters}
        onChange={mockOnChange}
      />
    )
    
    const expandButton = screen.getByText('Expand')
    fireEvent.click(expandButton)
    
    const highConfidenceButton = screen.getByText('High Confidence Only')
    fireEvent.click(highConfidenceButton)
    
    expect(mockOnChange).toHaveBeenCalled()
  })
})

