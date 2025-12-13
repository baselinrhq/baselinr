import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { BaselineConfig } from '@/components/config/BaselineConfig'

describe('BaselineConfig', () => {
  const defaultProps = {
    baselines: {
      strategy: 'last_run',
      windows: {
        moving_average: 7,
        prior_period: 7,
        min_runs: 3,
      },
    },
    onChange: vi.fn(),
  }

  it('renders baseline strategy selector', () => {
    render(<BaselineConfig {...defaultProps} />)
    
    expect(screen.getByText(/baseline strategy/i)).toBeInTheDocument()
  })

  it('displays current strategy', () => {
    render(<BaselineConfig {...defaultProps} />)
    
    // The Select component should show the current value
    expect(screen.getByText(/last run/i)).toBeInTheDocument()
  })

  it('calls onChange when strategy changes', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<BaselineConfig {...defaultProps} onChange={onChange} />)
    
    const strategyButton = screen.getByRole('button', { name: /last run/i })
    await user.click(strategyButton)
    
    // Select a different strategy
    const autoOption = screen.getByText(/auto/i)
    await user.click(autoOption)
    
    expect(onChange).toHaveBeenCalled()
  })

  it('shows moving average window for moving_average strategy', () => {
    render(<BaselineConfig {...defaultProps} baselines={{ ...defaultProps.baselines, strategy: 'moving_average' }} />)
    
    expect(screen.getByText(/moving average window/i)).toBeInTheDocument()
  })

  it('shows prior period for prior_period strategy', () => {
    render(<BaselineConfig {...defaultProps} baselines={{ ...defaultProps.baselines, strategy: 'prior_period' }} />)
    
    expect(screen.getAllByText(/prior period/i).length).toBeGreaterThan(0)
  })

  it('shows all window fields for auto strategy', () => {
    render(<BaselineConfig {...defaultProps} baselines={{ ...defaultProps.baselines, strategy: 'auto' }} />)
    
    expect(screen.getByText(/moving average window/i)).toBeInTheDocument()
    expect(screen.getAllByText(/prior period/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/minimum runs required/i)).toBeInTheDocument()
  })

  it('calls onChange when window value changes', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<BaselineConfig {...defaultProps} onChange={onChange} baselines={{ ...defaultProps.baselines, strategy: 'moving_average' }} />)
    
    const windowInput = screen.getByDisplayValue('7')
    await user.clear(windowInput)
    await user.type(windowInput, '10')
    
    expect(onChange).toHaveBeenCalled()
  })
})

