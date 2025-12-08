import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { ThresholdConfig } from '@/components/config/ThresholdConfig'

describe('ThresholdConfig', () => {
  const defaultProps = {
    thresholds: {
      low_threshold: 5.0,
      medium_threshold: 15.0,
      high_threshold: 30.0,
    },
    onChange: vi.fn(),
  }

  it('renders threshold inputs', () => {
    render(<ThresholdConfig {...defaultProps} />)
    
    expect(screen.getByText(/low severity threshold/i)).toBeInTheDocument()
    expect(screen.getByText(/medium severity threshold/i)).toBeInTheDocument()
    expect(screen.getByText(/high severity threshold/i)).toBeInTheDocument()
  })

  it('displays threshold values', () => {
    render(<ThresholdConfig {...defaultProps} />)
    
    const lowInput = screen.getByDisplayValue('5')
    const mediumInput = screen.getByDisplayValue('15')
    const highInput = screen.getByDisplayValue('30')
    
    expect(lowInput).toBeInTheDocument()
    expect(mediumInput).toBeInTheDocument()
    expect(highInput).toBeInTheDocument()
  })

  it('calls onChange when threshold is updated', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<ThresholdConfig {...defaultProps} onChange={onChange} />)
    
    const lowInput = screen.getByDisplayValue('5')
    await user.clear(lowInput)
    await user.type(lowInput, '10')
    
    expect(onChange).toHaveBeenCalled()
  })

  it('validates threshold order', () => {
    const invalidThresholds = {
      low_threshold: 30.0,
      medium_threshold: 15.0,
      high_threshold: 5.0,
    }
    render(<ThresholdConfig {...defaultProps} thresholds={invalidThresholds} />)
    
    expect(screen.getByText(/thresholds must be in ascending order/i)).toBeInTheDocument()
  })

  it('uses custom unit', () => {
    render(<ThresholdConfig {...defaultProps} unit="σ" />)
    
    expect(screen.getByText(/low severity threshold \(σ\)/i)).toBeInTheDocument()
  })
})

