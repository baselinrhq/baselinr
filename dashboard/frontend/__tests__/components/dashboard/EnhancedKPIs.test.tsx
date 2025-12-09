import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import EnhancedKPIs from '@/components/dashboard/EnhancedKPIs'
import { DashboardMetrics } from '@/lib/api'

describe('EnhancedKPIs', () => {
  const baseMetrics: DashboardMetrics = {
    total_runs: 10,
    total_tables: 5,
    total_drift_events: 2,
    avg_row_count: 1000,
    kpis: [],
    run_trend: [],
    drift_trend: [],
    warehouse_breakdown: {},
    recent_runs: [],
    recent_drift: [],
    total_validation_rules: 0,
    failed_validation_rules: 0,
    active_alerts: 0,
    stale_tables_count: 0,
    validation_trend: [],
  }

  it('renders validation pass rate when available', () => {
    const metrics: DashboardMetrics = {
      ...baseMetrics,
      validation_pass_rate: 95.5,
      total_validation_rules: 100,
    }
    render(<EnhancedKPIs metrics={metrics} />)
    expect(screen.getByText(/Validation Pass Rate/i)).toBeInTheDocument()
    expect(screen.getByText(/95.5%/)).toBeInTheDocument()
  })

  it('renders active alerts', () => {
    const metrics: DashboardMetrics = {
      ...baseMetrics,
      active_alerts: 5,
    }
    render(<EnhancedKPIs metrics={metrics} />)
    expect(screen.getByText(/Active Alerts/i)).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
  })

  it('renders data freshness when available', () => {
    const metrics: DashboardMetrics = {
      ...baseMetrics,
      data_freshness_hours: 12.5,
    }
    render(<EnhancedKPIs metrics={metrics} />)
    expect(screen.getByText(/Data Freshness/i)).toBeInTheDocument()
    expect(screen.getByText(/\d+ hours/)).toBeInTheDocument()
  })

  it('does not render validation pass rate when no validation rules', () => {
    const metrics: DashboardMetrics = {
      ...baseMetrics,
      validation_pass_rate: 95.5,
      total_validation_rules: 0,
    }
    render(<EnhancedKPIs metrics={metrics} />)
    expect(screen.queryByText(/Validation Pass Rate/i)).not.toBeInTheDocument()
  })

  it('formats data freshness correctly for days', () => {
    const metrics: DashboardMetrics = {
      ...baseMetrics,
      data_freshness_hours: 48,
    }
    render(<EnhancedKPIs metrics={metrics} />)
    expect(screen.getByText(/2 days/)).toBeInTheDocument()
  })
})

