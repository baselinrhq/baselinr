/**
 * Unit tests for RCAList component
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import RCAList from '@/components/rca/RCAList'
import type { RCAListItem } from '@/types/rca'

const mockRCAItems: RCAListItem[] = [
  {
    anomaly_id: 'anom-1',
    table_name: 'users',
    schema_name: 'public',
    column_name: 'email',
    metric_name: 'null_percent',
    analyzed_at: '2024-01-01T00:00:00Z',
    rca_status: 'analyzed',
    num_causes: 2,
    top_cause: {
      cause_type: 'pipeline_failure',
      confidence_score: 0.85,
      description: 'Pipeline failed before anomaly',
    },
  },
  {
    anomaly_id: 'anom-2',
    table_name: 'orders',
    schema_name: 'public',
    analyzed_at: '2024-01-02T00:00:00Z',
    rca_status: 'pending',
    num_causes: 0,
    top_cause: null,
  },
]

describe('RCAList', () => {
  it('renders empty state when no items', () => {
    render(<RCAList items={[]} />)

    expect(screen.getByText('No RCA results found')).toBeInTheDocument()
  })

  it('renders list of RCA items', () => {
    const onRowClick = vi.fn()

    render(<RCAList items={mockRCAItems} onRowClick={onRowClick} />)

    expect(screen.getByText('public.users')).toBeInTheDocument()
    expect(screen.getByText('public.orders')).toBeInTheDocument()
    expect(screen.getByText('analyzed')).toBeInTheDocument()
    expect(screen.getByText('pending')).toBeInTheDocument()
  })

  it('calls onRowClick when row is clicked', () => {
    const onRowClick = vi.fn()

    render(<RCAList items={mockRCAItems} onRowClick={onRowClick} />)

    const firstRow = screen.getByText('public.users').closest('tr')
    if (firstRow) {
      fireEvent.click(firstRow)
      expect(onRowClick).toHaveBeenCalledWith('anom-1')
    }
  })

  it('displays cause count and confidence', () => {
    render(<RCAList items={mockRCAItems} />)

    expect(screen.getByText('2')).toBeInTheDocument() // num_causes
    expect(screen.getByText('85%')).toBeInTheDocument() // top_cause confidence
  })

  it('handles missing optional fields', () => {
    const itemWithoutOptional: RCAListItem = {
      anomaly_id: 'anom-3',
      table_name: 'products',
      analyzed_at: '2024-01-03T00:00:00Z',
      rca_status: 'analyzed',
      num_causes: 0,
      top_cause: null,
    }

    render(<RCAList items={[itemWithoutOptional]} />)

    expect(screen.getByText('products')).toBeInTheDocument()
    // Check for column name specifically by finding the row and checking the column cell
    const productRow = screen.getByText('products').closest('tr')
    expect(productRow).toBeInTheDocument()
    // The column cell should contain "-" for missing column_name
    const columnCells = productRow?.querySelectorAll('td')
    expect(columnCells?.[3]).toHaveTextContent('-') // Column is 4th cell (index 3)
  })
})

