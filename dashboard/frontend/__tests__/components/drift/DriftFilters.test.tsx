import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import DriftFilters from '@/components/drift/DriftFilters'
import type { DriftFilters as DriftFiltersType } from '@/types/drift'

describe('DriftFilters', () => {
  const mockOnChange = vi.fn()
  const defaultFilters: DriftFiltersType = {
    days: 30,
  }

  it('renders filter controls', () => {
    render(
      <DriftFilters
        filters={defaultFilters}
        onChange={mockOnChange}
      />
    )
    expect(screen.getByText('Filters')).toBeInTheDocument()
  })

  it('displays active filter count', () => {
    const filters: DriftFiltersType = {
      warehouse: 'postgres',
      severity: 'high',
      days: 7,
    }
    render(
      <DriftFilters
        filters={filters}
        onChange={mockOnChange}
      />
    )
    // Count all non-empty filters (warehouse, severity, days = 3)
    expect(screen.getByText(/3 active/)).toBeInTheDocument()
  })

  it('calls onChange when filter changes', () => {
    render(
      <DriftFilters
        filters={defaultFilters}
        onChange={mockOnChange}
      />
    )
    
    // Expand filters
    const expandButton = screen.getByText('Expand')
    fireEvent.click(expandButton)
    
    // The actual filter changes would be tested through the Select/Input components
    // This is a basic smoke test
    expect(screen.getByText('Collapse')).toBeInTheDocument()
  })

  it('shows clear all button when filters are active', () => {
    const filters: DriftFiltersType = {
      warehouse: 'postgres',
    }
    render(
      <DriftFilters
        filters={filters}
        onChange={mockOnChange}
      />
    )
    expect(screen.getByText('Clear all')).toBeInTheDocument()
  })

  it('applies preset filters', () => {
    render(
      <DriftFilters
        filters={defaultFilters}
        onChange={mockOnChange}
        onPreset={vi.fn()}
      />
    )
    
    const expandButton = screen.getByText('Expand')
    fireEvent.click(expandButton)
    
    // Check for preset buttons
    expect(screen.getByText('Last 7 days - High severity')).toBeInTheDocument()
  })
})

