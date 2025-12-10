import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import DriftAnalysis from '@/components/drift/DriftAnalysis'
import type { DriftAlert } from '@/types/drift'

describe('DriftAnalysis', () => {
  const mockAlerts: DriftAlert[] = [
    {
      event_id: 'event1',
      run_id: 'run1',
      table_name: 'customers',
      column_name: 'age',
      metric_name: 'mean',
      severity: 'high',
      timestamp: '2024-01-01T00:00:00Z',
      warehouse_type: 'postgres',
    },
    {
      event_id: 'event2',
      run_id: 'run1',
      table_name: 'customers',
      column_name: 'email',
      metric_name: 'null_percent',
      severity: 'medium',
      timestamp: '2024-01-02T00:00:00Z',
      warehouse_type: 'postgres',
    },
  ]

  it('renders empty state when no alerts', () => {
    render(<DriftAnalysis alerts={[]} />)
    expect(screen.getByText(/No drift data available/i)).toBeInTheDocument()
  })

  it('renders severity trends chart', () => {
    render(<DriftAnalysis alerts={mockAlerts} />)
    expect(screen.getByText('Severity Trends Over Time')).toBeInTheDocument()
  })

  it('renders metric type breakdown', () => {
    render(<DriftAnalysis alerts={mockAlerts} />)
    expect(screen.getByText('Metric Type Breakdown')).toBeInTheDocument()
  })

  it('renders top affected tables', () => {
    render(<DriftAnalysis alerts={mockAlerts} />)
    expect(screen.getByText('Top Affected Tables')).toBeInTheDocument()
    expect(screen.getByText('customers')).toBeInTheDocument()
  })
})

