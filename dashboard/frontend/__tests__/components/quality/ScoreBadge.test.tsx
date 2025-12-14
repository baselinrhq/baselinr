import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ScoreBadge from '@/components/quality/ScoreBadge'

describe('ScoreBadge', () => {
  it('renders score with healthy status', () => {
    render(<ScoreBadge score={85.5} status="healthy" />)
    const badge = screen.getByText('85.5')
    expect(badge).toBeInTheDocument()
  })

  it('renders score with warning status', () => {
    render(<ScoreBadge score={65.0} status="warning" />)
    const badge = screen.getByText('65.0')
    expect(badge).toBeInTheDocument()
  })

  it('renders score with critical status', () => {
    render(<ScoreBadge score={45.0} status="critical" />)
    const badge = screen.getByText('45.0')
    expect(badge).toBeInTheDocument()
  })

  it('renders with small size', () => {
    render(<ScoreBadge score={85.5} status="healthy" size="sm" />)
    const badge = screen.getByText('85.5')
    expect(badge).toBeInTheDocument()
  })

  it('renders with medium size', () => {
    render(<ScoreBadge score={85.5} status="healthy" size="md" />)
    const badge = screen.getByText('85.5')
    expect(badge).toBeInTheDocument()
  })

  it('formats score to one decimal place', () => {
    render(<ScoreBadge score={85.555} status="healthy" />)
    const badge = screen.getByText('85.6')
    expect(badge).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(
      <ScoreBadge score={85.5} status="healthy" className="custom-class" />
    )
    const badge = container.querySelector('.custom-class')
    expect(badge).toBeInTheDocument()
  })
})

