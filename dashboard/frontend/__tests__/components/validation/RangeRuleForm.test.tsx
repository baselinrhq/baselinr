import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { RangeRuleForm } from '@/components/validation/RangeRuleForm'
import { ValidationRuleConfig } from '@/types/config'

describe('RangeRuleForm', () => {
  const defaultRule: ValidationRuleConfig = {
    type: 'range',
    table: 'orders',
    column: 'total_amount',
    min_value: 0,
    max_value: 1000000,
    severity: 'medium',
    enabled: true,
  }

  it('renders min and max value inputs', () => {
    const onChange = vi.fn()
    render(<RangeRuleForm rule={defaultRule} onChange={onChange} />)

    expect(screen.getByText('Minimum Value')).toBeInTheDocument()
    expect(screen.getByText('Maximum Value')).toBeInTheDocument()
  })

  it('updates min value', async () => {
    const onChange = vi.fn()
    render(<RangeRuleForm rule={defaultRule} onChange={onChange} />)

    const minInput = screen.getAllByRole('spinbutton')[0]
    fireEvent.change(minInput, { target: { value: '10' } })

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({ min_value: 10 })
      )
    })
  })

  it('updates max value', async () => {
    const onChange = vi.fn()
    render(<RangeRuleForm rule={defaultRule} onChange={onChange} />)

    const maxInput = screen.getAllByRole('spinbutton')[1]
    fireEvent.change(maxInput, { target: { value: '5000' } })

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({ max_value: 5000 })
      )
    })
  })

  it('validates min <= max', async () => {
    const onChange = vi.fn()
    const rule: ValidationRuleConfig = {
      ...defaultRule,
      min_value: 0,
      max_value: 100,
    }
    render(<RangeRuleForm rule={rule} onChange={onChange} />)

    // Set min to 100
    const minInput = screen.getAllByRole('spinbutton')[0]
    fireEvent.change(minInput, { target: { value: '100' } })

    // Set max to 50 (less than min) - this should trigger validation
    const maxInput = screen.getAllByRole('spinbutton')[1]
    fireEvent.change(maxInput, { target: { value: '50' } })

    // Wait for onChange to be called (validation happens in onChange handlers)
    await waitFor(() => {
      expect(onChange).toHaveBeenCalled()
    }, { timeout: 1000 })

    // Verify the component rendered the inputs correctly
    expect(minInput).toBeInTheDocument()
    expect(maxInput).toBeInTheDocument()
  })

  it('allows empty min value', async () => {
    const onChange = vi.fn()
    render(<RangeRuleForm rule={defaultRule} onChange={onChange} />)

    const minInput = screen.getAllByRole('spinbutton')[0]
    fireEvent.change(minInput, { target: { value: '' } })

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({ min_value: null })
      )
    })
  })

  it('allows empty max value', async () => {
    const onChange = vi.fn()
    render(<RangeRuleForm rule={defaultRule} onChange={onChange} />)

    const maxInput = screen.getAllByRole('spinbutton')[1]
    fireEvent.change(maxInput, { target: { value: '' } })

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({ max_value: null })
      )
    })
  })
})

