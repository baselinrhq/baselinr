import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import TrendCharts from '@/components/dashboard/TrendCharts'

describe('TrendCharts', () => {
  it('renders trends overview title', () => {
    render(
      <TrendCharts
        runTrend={[]}
        driftTrend={[]}
        validationTrend={[]}
      />
    )
    expect(screen.getByText(/Trends Overview/i)).toBeInTheDocument()
  })

  it('shows no data message when all trends are empty', () => {
    render(
      <TrendCharts
        runTrend={[]}
        driftTrend={[]}
        validationTrend={[]}
      />
    )
    expect(screen.getByText(/No trend data available/i)).toBeInTheDocument()
  })

  it('renders chart when run trend data is available', () => {
    const runTrend = [
      { timestamp: '2024-01-01T00:00:00Z', value: 5 },
      { timestamp: '2024-01-02T00:00:00Z', value: 10 },
    ]
    render(
      <TrendCharts
        runTrend={runTrend}
        driftTrend={[]}
        validationTrend={[]}
      />
    )
    // Chart should render (Recharts components don't render text directly)
    expect(screen.queryByText(/No trend data available/i)).not.toBeInTheDocument()
  })

  it('combines multiple trends correctly', () => {
    const runTrend = [
      { timestamp: '2024-01-01T00:00:00Z', value: 5 },
    ]
    const driftTrend = [
      { timestamp: '2024-01-01T00:00:00Z', value: 2 },
    ]
    const validationTrend = [
      { timestamp: '2024-01-01T00:00:00Z', value: 95.5 },
    ]
    render(
      <TrendCharts
        runTrend={runTrend}
        driftTrend={driftTrend}
        validationTrend={validationTrend}
      />
    )
    expect(screen.queryByText(/No trend data available/i)).not.toBeInTheDocument()
  })

  it('handles invalid timestamp format gracefully', () => {
    const runTrend = [
      { timestamp: 'invalid-date', value: 5 },
    ]
    render(
      <TrendCharts
        runTrend={runTrend}
        driftTrend={[]}
        validationTrend={[]}
      />
    )
    // Should not crash, may show no data or handle gracefully
    expect(screen.getByText(/Trends Overview/i)).toBeInTheDocument()
  })
})

