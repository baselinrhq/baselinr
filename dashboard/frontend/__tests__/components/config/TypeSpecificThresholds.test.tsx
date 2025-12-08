import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { TypeSpecificThresholds } from '@/components/config/TypeSpecificThresholds'

describe('TypeSpecificThresholds', () => {
  const defaultProps = {
    enableTypeSpecificThresholds: true,
    typeSpecificThresholds: {
      numeric: {
        mean: { low: 10.0, medium: 25.0, high: 50.0 },
        default: { low: 5.0, medium: 15.0, high: 30.0 },
      },
      categorical: {
        distinct_count: { low: 2.0, medium: 5.0, high: 10.0 },
        default: { low: 5.0, medium: 15.0, high: 30.0 },
      },
    },
    onChange: vi.fn(),
  }

  it('renders toggle for enabling type-specific thresholds', () => {
    render(<TypeSpecificThresholds {...defaultProps} />)
    
    expect(screen.getByText(/type-specific thresholds/i)).toBeInTheDocument()
  })

  it('shows tabs for different data types when enabled', () => {
    render(<TypeSpecificThresholds {...defaultProps} />)
    
    expect(screen.getByRole('tab', { name: /numeric/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /categorical/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /timestamp/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /boolean/i })).toBeInTheDocument()
  })

  it('shows threshold configs for numeric type', () => {
    render(<TypeSpecificThresholds {...defaultProps} />)
    
    expect(screen.getByText(/mean/i)).toBeInTheDocument()
    expect(screen.getByText(/standard deviation/i)).toBeInTheDocument()
    expect(screen.getByText(/default/i)).toBeInTheDocument()
  })

  it('calls onChange when toggle is changed', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<TypeSpecificThresholds {...defaultProps} onChange={onChange} />)
    
    const toggle = screen.getByRole('switch')
    await user.click(toggle)
    
    expect(onChange).toHaveBeenCalledWith(false, undefined)
  })

  it('calls onChange when threshold is updated', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<TypeSpecificThresholds {...defaultProps} onChange={onChange} />)
    
    // Find and update a threshold input
    const lowInput = screen.getAllByRole('spinbutton')[0]
    await user.clear(lowInput)
    await user.type(lowInput, '12')
    expect(onChange).toHaveBeenCalled()
  })

  it('shows message when disabled', () => {
    render(<TypeSpecificThresholds {...defaultProps} enableTypeSpecificThresholds={false} />)
    
    expect(screen.getByText(/enable type-specific thresholds/i)).toBeInTheDocument()
  })
})

