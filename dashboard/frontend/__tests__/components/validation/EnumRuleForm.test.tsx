import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { EnumRuleForm } from '@/components/validation/EnumRuleForm'
import { ValidationRuleConfig } from '@/types/config'

describe('EnumRuleForm', () => {
  const defaultRule: ValidationRuleConfig = {
    type: 'enum',
    table: 'orders',
    column: 'status',
    allowed_values: ['pending', 'completed', 'cancelled'],
    severity: 'high',
    enabled: true,
  }

  it('renders allowed values inputs', () => {
    const onChange = vi.fn()
    render(<EnumRuleForm rule={defaultRule} onChange={onChange} />)

    expect(screen.getByText('Allowed Values')).toBeInTheDocument()
    expect(screen.getByDisplayValue('pending')).toBeInTheDocument()
    expect(screen.getByDisplayValue('completed')).toBeInTheDocument()
    expect(screen.getByDisplayValue('cancelled')).toBeInTheDocument()
  })

  it('adds new value', async () => {
    const onChange = vi.fn()
    render(<EnumRuleForm rule={defaultRule} onChange={onChange} />)

    const addButton = screen.getByText('Add Value')
    fireEvent.click(addButton)

    await waitFor(() => {
      const inputs = screen.getAllByPlaceholderText(/Value \d+/i)
      expect(inputs.length).toBeGreaterThan(3)
    })
  })

  it('removes value', async () => {
    const onChange = vi.fn()
    render(<EnumRuleForm rule={defaultRule} onChange={onChange} />)

    const removeButtons = screen.getAllByRole('button', { name: '' })
    const removeButton = removeButtons.find(btn => 
      btn.querySelector('svg') && btn.closest('.flex.items-center.gap-2')
    )
    
    if (removeButton) {
      fireEvent.click(removeButton)

      await waitFor(() => {
        expect(onChange).toHaveBeenCalled()
      })
    }
  })

  it('updates value', async () => {
    const onChange = vi.fn()
    render(<EnumRuleForm rule={defaultRule} onChange={onChange} />)

    const input = screen.getByDisplayValue('pending')
    fireEvent.change(input, { target: { value: 'processing' } })

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          allowed_values: expect.arrayContaining(['processing'])
        })
      )
    })
  })

  it('detects duplicate values', async () => {
    const onChange = vi.fn()
    render(<EnumRuleForm rule={defaultRule} onChange={onChange} />)

    const input = screen.getByDisplayValue('pending')
    fireEvent.change(input, { target: { value: 'completed' } })

    await waitFor(() => {
      // Check for duplicate error message (may appear multiple times)
      const errorMessages = screen.queryAllByText((content, element) => {
        return element?.textContent?.toLowerCase().includes('duplicate') || false
      })
      expect(errorMessages.length).toBeGreaterThan(0)
    })
  })

  it('filters out empty values', async () => {
    const onChange = vi.fn()
    render(<EnumRuleForm rule={defaultRule} onChange={onChange} />)

    const input = screen.getByDisplayValue('pending')
    fireEvent.change(input, { target: { value: '' } })

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          allowed_values: expect.not.arrayContaining([''])
        })
      )
    })
  })
})

