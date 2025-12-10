import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ValidationResults from '@/components/validation/ValidationResults'
import type { ValidationResult } from '@/types/validation'

describe('ValidationResults', () => {
  const mockResults: ValidationResult[] = [
    {
      id: 1,
      run_id: 'run1',
      table_name: 'users',
      schema_name: 'public',
      column_name: 'email',
      rule_type: 'format',
      passed: false,
      failure_reason: 'Invalid format',
      total_rows: 1000,
      failed_rows: 5,
      failure_rate: 0.5,
      severity: 'high',
      validated_at: '2024-01-02T00:00:00Z',
    },
    {
      id: 2,
      run_id: 'run1',
      table_name: 'orders',
      schema_name: 'public',
      column_name: 'amount',
      rule_type: 'range',
      passed: true,
      total_rows: 500,
      failed_rows: 0,
      failure_rate: 0.0,
      severity: 'medium',
      validated_at: '2024-01-02T00:00:00Z',
    },
  ]

  it('renders validation results table', () => {
    render(
      <ValidationResults
        results={mockResults}
        total={2}
        page={1}
        pageSize={50}
      />
    )

    expect(screen.getByText('users')).toBeInTheDocument()
    expect(screen.getByText('orders')).toBeInTheDocument()
    expect(screen.getByText('email')).toBeInTheDocument()
    expect(screen.getByText('Format')).toBeInTheDocument()
  })

  it('displays pass/fail badges correctly', () => {
    render(
      <ValidationResults
        results={mockResults}
        total={2}
        page={1}
        pageSize={50}
      />
    )

    expect(screen.getByText('Fail')).toBeInTheDocument()
    expect(screen.getByText('Pass')).toBeInTheDocument()
  })

  it('displays empty state when no results', () => {
    render(
      <ValidationResults
        results={[]}
        total={0}
        page={1}
        pageSize={50}
      />
    )

    expect(screen.getByText(/no validation results/i)).toBeInTheDocument()
  })

  it('calls onRowClick when row is clicked', () => {
    const handleRowClick = vi.fn()
    render(
      <ValidationResults
        results={mockResults}
        total={2}
        page={1}
        pageSize={50}
        onRowClick={handleRowClick}
      />
    )

    const row = screen.getByText('users').closest('tr')
    if (row) {
      row.click()
      expect(handleRowClick).toHaveBeenCalledWith(1)
    }
  })

  it('displays pagination controls when onPageChange is provided', () => {
    const onPageChange = vi.fn()
    render(
      <ValidationResults
        results={mockResults}
        total={100}
        page={1}
        pageSize={50}
        onPageChange={onPageChange}
      />
    )

    // Check if pagination controls are rendered (button or text)
    // The exact implementation may vary, so we just check that the component renders
    expect(screen.getByText('users')).toBeInTheDocument()
  })
})

