import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { DriftConfig } from '@/components/config/DriftConfig'

describe('DriftConfig', () => {
  const defaultProps = {
    driftDetection: {
      strategy: 'absolute_threshold',
      absolute_threshold: {
        low_threshold: 5.0,
        medium_threshold: 15.0,
        high_threshold: 30.0,
      },
    },
    onChange: vi.fn(),
  }

  it('renders strategy selector', () => {
    render(<DriftConfig {...defaultProps} />)
    
    expect(screen.getByRole('heading', { name: /drift detection strategy/i })).toBeInTheDocument()
  })

  it('displays current strategy', () => {
    render(<DriftConfig {...defaultProps} />)
    
    expect(screen.getByText(/absolute threshold/i)).toBeInTheDocument()
  })

  it('shows threshold config for absolute_threshold strategy', () => {
    render(<DriftConfig {...defaultProps} />)
    
    expect(screen.getByText(/threshold configuration/i)).toBeInTheDocument()
  })

  it('shows threshold config for standard_deviation strategy', () => {
    render(
      <DriftConfig
        {...defaultProps}
        driftDetection={{
          strategy: 'standard_deviation',
          standard_deviation: {
            low_threshold: 1.0,
            medium_threshold: 2.0,
            high_threshold: 3.0,
          },
        }}
      />
    )
    
    expect(screen.getByText(/threshold configuration/i)).toBeInTheDocument()
  })

  it('shows statistical config for statistical strategy', () => {
    render(
      <DriftConfig
        {...defaultProps}
        driftDetection={{
          strategy: 'statistical',
          statistical: {
            tests: ['ks_test'],
            sensitivity: 'medium',
          },
        }}
      />
    )
    
    expect(screen.getByText(/statistical test configuration/i)).toBeInTheDocument()
  })

  it('shows placeholder for ml_based strategy', () => {
    render(
      <DriftConfig
        {...defaultProps}
        driftDetection={{
          strategy: 'ml_based',
        }}
      />
    )
    
    expect(screen.getAllByText(/coming soon/i).length).toBeGreaterThan(0)
  })

  it('calls onChange when strategy changes', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<DriftConfig {...defaultProps} onChange={onChange} />)
    
    const strategyButton = screen.getByRole('button', { name: /absolute threshold/i })
    await user.click(strategyButton)
    
    const standardDevOption = screen.getByText(/standard deviation/i)
    await user.click(standardDevOption)
    
    expect(onChange).toHaveBeenCalled()
  })
})

