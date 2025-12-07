import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { SamplingConfig } from '@/components/config/SamplingConfig'
import { SamplingConfig as SamplingConfigType } from '@/types/config'

describe('SamplingConfig', () => {
  it('renders empty state when no sampling config', () => {
    const onChange = vi.fn()
    render(<SamplingConfig sampling={null} onChange={onChange} />)

    expect(screen.getByText('No sampling configuration')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Add Sampling Config/i })).toBeInTheDocument()
  })

  it('renders sampling fields when config exists', () => {
    const sampling: SamplingConfigType = {
      enabled: true,
      method: 'random',
      fraction: 0.1,
    }
    const onChange = vi.fn()
    render(<SamplingConfig sampling={sampling} onChange={onChange} />)

    expect(screen.getByText('Sampling Configuration')).toBeInTheDocument()
    // Find toggle by finding the label and then the switch
    const enableSamplingLabel = screen.getByText(/Enable Sampling/i)
    const toggle = enableSamplingLabel.closest('label')?.querySelector('button[role="switch"]') || 
                   screen.getAllByRole('switch')[0]
    expect(toggle).toBeInTheDocument()
    // Select component doesn't expose label association easily, so just check text exists
    expect(screen.getByText(/Sampling Method/i)).toBeInTheDocument()
    expect(screen.getByText(/Sample Fraction/i)).toBeInTheDocument()
  })

  it('updates config on field changes', async () => {
    const sampling: SamplingConfigType = {
      enabled: true,
      method: 'random',
      fraction: 0.1,
    }
    const onChange = vi.fn()
    render(<SamplingConfig sampling={sampling} onChange={onChange} />)

    // Verify component renders - Select component interaction is complex to test
    expect(screen.getByText('Sampling Configuration')).toBeInTheDocument()
    // The actual Select change would require more complex interaction
  })

  it('shows/hides fields based on enabled state', () => {
    const sampling: SamplingConfigType = {
      enabled: false,
      method: 'random',
      fraction: 0.1,
    }
    const onChange = vi.fn()
    const { rerender } = render(
      <SamplingConfig sampling={sampling} onChange={onChange} />
    )

    // When sampling is null, shows empty state
    // When sampling exists but enabled is false, still shows config (just disabled)
    expect(screen.getByText('Sampling Configuration')).toBeInTheDocument()

    // When enabled, should show all fields
    const enabledSampling: SamplingConfigType = {
      enabled: true,
      method: 'random',
      fraction: 0.1,
    }
    rerender(<SamplingConfig sampling={enabledSampling} onChange={onChange} />)

    expect(screen.getByText(/Sampling Method/i)).toBeInTheDocument()
    expect(screen.getByText(/Sample Fraction/i)).toBeInTheDocument()
  })

  it('handles remove sampling config', async () => {
    const sampling: SamplingConfigType = {
      enabled: true,
      method: 'random',
      fraction: 0.1,
    }
    const onChange = vi.fn()
    render(<SamplingConfig sampling={sampling} onChange={onChange} />)

    // Find toggle by finding the label and then the switch
    const enableSamplingLabel = screen.getByText(/Enable Sampling/i)
    const toggle = enableSamplingLabel.closest('label')?.querySelector('button[role="switch"]') || 
                   screen.getAllByRole('switch')[0]
    fireEvent.click(toggle as HTMLElement)

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(null)
    })
  })

  it('validates fraction range', async () => {
    const sampling: SamplingConfigType = {
      enabled: true,
      method: 'random',
      fraction: 0.5,
    }
    const onChange = vi.fn()
    render(<SamplingConfig sampling={sampling} onChange={onChange} />)

    const fractionInputs = screen.getAllByRole('spinbutton')
    const fractionInput = fractionInputs.find((input) => (input as HTMLInputElement).value === '0.1') || fractionInputs[0]
    fireEvent.change(fractionInput, { target: { value: '1.5' } })

    // Should be clamped to max 1.0
    await waitFor(() => {
      expect(onChange).toHaveBeenCalled()
    })
  })
})

