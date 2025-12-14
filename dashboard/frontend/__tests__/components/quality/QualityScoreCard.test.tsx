import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import QualityScoreCard from '@/components/quality/QualityScoreCard'
import type { QualityScore } from '@/types/quality'

const createMockScore = (overrides?: Partial<QualityScore>): QualityScore => ({
  table_name: 'customers',
  schema_name: 'public',
  overall_score: 85.5,
  status: 'healthy',
  trend: 'improving',
  trend_percentage: 2.3,
  components: {
    completeness: 90.0,
    validity: 88.0,
    consistency: 82.0,
    freshness: 95.0,
    uniqueness: 85.0,
    accuracy: 78.0,
  },
  issues: {
    total: 3,
    critical: 1,
    warnings: 2,
  },
  calculated_at: '2024-01-15T10:30:00Z',
  run_id: 'run123',
  ...overrides,
})

describe('QualityScoreCard', () => {
  it('renders quality score card with all components', () => {
    const score = createMockScore()
    render(<QualityScoreCard score={score} />)

    expect(screen.getByText('Data Quality Score')).toBeInTheDocument()
    expect(screen.getByText('85.5')).toBeInTheDocument()
    expect(screen.getByText('healthy')).toBeInTheDocument()
    expect(screen.getByText('Completeness')).toBeInTheDocument()
    expect(screen.getByText('Validity')).toBeInTheDocument()
    expect(screen.getByText('Consistency')).toBeInTheDocument()
    expect(screen.getByText('Freshness')).toBeInTheDocument()
    expect(screen.getByText('Uniqueness')).toBeInTheDocument()
    expect(screen.getByText('Accuracy')).toBeInTheDocument()
  })

  it('renders with warning status', () => {
    const score = createMockScore({ status: 'warning', overall_score: 65.0 })
    render(<QualityScoreCard score={score} />)

    expect(screen.getByText('65.0')).toBeInTheDocument()
    expect(screen.getByText('warning')).toBeInTheDocument()
  })

  it('renders with critical status', () => {
    const score = createMockScore({ status: 'critical', overall_score: 45.0 })
    render(<QualityScoreCard score={score} />)

    expect(screen.getByText('45.0')).toBeInTheDocument()
    expect(screen.getByText('critical')).toBeInTheDocument()
  })

  it('displays trend indicator when available', () => {
    const score = createMockScore({ trend: 'improving', trend_percentage: 5.2 })
    render(<QualityScoreCard score={score} />)

    expect(screen.getByText(/\+5\.2%/)).toBeInTheDocument()
  })

  it('displays degrading trend', () => {
    const score = createMockScore({ trend: 'degrading', trend_percentage: -3.1 })
    render(<QualityScoreCard score={score} />)

    expect(screen.getByText(/-3\.1%/)).toBeInTheDocument()
  })

  it('displays stable trend', () => {
    const score = createMockScore({ trend: 'stable', trend_percentage: 0.5 })
    render(<QualityScoreCard score={score} />)

    expect(screen.getByText('Stable')).toBeInTheDocument()
  })

  it('displays issues summary', () => {
    const score = createMockScore({
      issues: { total: 10, critical: 3, warnings: 7 },
    })
    render(<QualityScoreCard score={score} />)

    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('7')).toBeInTheDocument()
  })

  it('handles table without schema', () => {
    const score = createMockScore({ schema_name: null })
    render(<QualityScoreCard score={score} />)

    expect(screen.getByText('customers')).toBeInTheDocument()
  })

  it('renders in compact mode', () => {
    const score = createMockScore()
    render(<QualityScoreCard score={score} compact />)

    expect(screen.getByText('85.5')).toBeInTheDocument()
    // In compact mode, component breakdown should not be visible
    expect(screen.queryByText('Completeness')).not.toBeInTheDocument()
  })

  it('displays all component scores', () => {
    const score = createMockScore()
    render(<QualityScoreCard score={score} />)

    expect(screen.getByText('90.0')).toBeInTheDocument() // Completeness
    expect(screen.getByText('88.0')).toBeInTheDocument() // Validity
    expect(screen.getByText('82.0')).toBeInTheDocument() // Consistency
    expect(screen.getByText('95.0')).toBeInTheDocument() // Freshness
    expect(screen.getByText('85.0')).toBeInTheDocument() // Uniqueness
    expect(screen.getByText('78.0')).toBeInTheDocument() // Accuracy
  })

  it('handles score without trend', () => {
    const score = createMockScore({ trend: null, trend_percentage: null })
    render(<QualityScoreCard score={score} />)

    expect(screen.getByText('85.5')).toBeInTheDocument()
    // Trend section should not show
  })
})

