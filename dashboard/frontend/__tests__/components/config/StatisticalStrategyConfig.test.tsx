import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { StatisticalStrategyConfig } from '@/components/config/StatisticalStrategyConfig'

describe('StatisticalStrategyConfig', () => {
  const defaultProps = {
    statistical: {
      tests: ['ks_test', 'psi', 'chi_square'],
      sensitivity: 'medium',
      test_params: {
        ks_test: { alpha: 0.05 },
        psi: { buckets: 10, threshold: 0.2 },
        z_score: { z_threshold: 2.0 },
        chi_square: { alpha: 0.05 },
        entropy: { entropy_threshold: 0.1 },
        top_k: { k: 10, similarity_threshold: 0.7 },
      },
    },
    onChange: vi.fn(),
  }

  it('renders sensitivity selector', () => {
    render(<StatisticalStrategyConfig {...defaultProps} />)
    
    // Use getAllByText since "Sensitivity" may appear multiple times (label, etc.)
    expect(screen.getAllByText(/sensitivity/i).length).toBeGreaterThan(0)
  })

  it('renders test checkboxes', () => {
    render(<StatisticalStrategyConfig {...defaultProps} />)
    
    // Use getAllByText since text may appear multiple times (label, description, etc.)
    expect(screen.getAllByText(/kolmogorov-smirnov test/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/population stability index/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/chi-square test/i).length).toBeGreaterThan(0)
  })

  it('shows test parameters for selected tests', () => {
    render(<StatisticalStrategyConfig {...defaultProps} />)
    
    // KS test should be selected and show parameters
    expect(screen.getByText(/ks test - alpha/i)).toBeInTheDocument()
    expect(screen.getByText(/psi - buckets/i)).toBeInTheDocument()
    expect(screen.getByText(/chi-square - alpha/i)).toBeInTheDocument()
  })

  it('calls onChange when test is toggled', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<StatisticalStrategyConfig {...defaultProps} onChange={onChange} />)
    
    // Find and click a checkbox
    const checkboxes = screen.getAllByRole('checkbox')
    const uncheckedCheckbox = checkboxes.find((cb) => !(cb as HTMLInputElement).checked)
    
    if (uncheckedCheckbox) {
      await user.click(uncheckedCheckbox)
      expect(onChange).toHaveBeenCalled()
    }
  })

  it('calls onChange when sensitivity changes', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<StatisticalStrategyConfig {...defaultProps} onChange={onChange} />)
    
    const sensitivityButton = screen.getByRole('button', { name: /medium/i })
    await user.click(sensitivityButton)
    
    const highOption = screen.getByText(/high/i)
    await user.click(highOption)
    
    expect(onChange).toHaveBeenCalled()
  })

  it('calls onChange when test parameter changes', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<StatisticalStrategyConfig {...defaultProps} onChange={onChange} />)
    
    const alphaInput = screen.getAllByDisplayValue('0.05')[0]
    await user.clear(alphaInput)
    await user.type(alphaInput, '0.01')
    
    expect(onChange).toHaveBeenCalled()
  })
})

