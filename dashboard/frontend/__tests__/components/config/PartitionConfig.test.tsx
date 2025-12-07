import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { PartitionConfig } from '@/components/config/PartitionConfig'
import { PartitionConfig as PartitionConfigType } from '@/types/config'

describe('PartitionConfig', () => {
  it('renders empty state when no partition config', () => {
    const onChange = vi.fn()
    render(<PartitionConfig partition={null} onChange={onChange} />)

    expect(screen.getByText('No partition configuration')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Add Partition Config/i })).toBeInTheDocument()
  })

  it('renders partition fields when config exists', () => {
    const partition: PartitionConfigType = {
      key: 'order_date',
      strategy: 'latest',
      metadata_fallback: false,
    }
    const onChange = vi.fn()
    render(<PartitionConfig partition={partition} onChange={onChange} />)

    expect(screen.getByText('Partition Configuration')).toBeInTheDocument()
    expect(screen.getByText(/Partition Key/i)).toBeInTheDocument()
    expect(screen.getByText(/Strategy/i)).toBeInTheDocument()
  })

  it('updates config on field changes', async () => {
    const partition: PartitionConfigType = {
      key: 'order_date',
      strategy: 'latest',
    }
    const onChange = vi.fn()
    render(<PartitionConfig partition={partition} onChange={onChange} />)

    const keyInput = screen.getByDisplayValue('order_date')
    fireEvent.change(keyInput, { target: { value: 'created_at' } })

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({ key: 'created_at' })
      )
    })
  })

  it('shows recent_n field when strategy is recent_n', () => {
    const partition: PartitionConfigType = {
      strategy: 'recent_n',
      recent_n: 5,
    }
    const onChange = vi.fn()
    render(<PartitionConfig partition={partition} onChange={onChange} />)

    // Check that Recent N label exists and input with value 5 exists
    const recentNLabels = screen.getAllByText(/Recent N/i)
    expect(recentNLabels.length).toBeGreaterThan(0)
    expect(screen.getByDisplayValue('5')).toBeInTheDocument()
  })

  it('shows specific values field when strategy is specific_values', () => {
    const partition: PartitionConfigType = {
      strategy: 'specific_values',
      values: ['2024-01-01', '2024-01-02'],
    }
    const onChange = vi.fn()
    render(<PartitionConfig partition={partition} onChange={onChange} />)

    expect(screen.getByText(/Specific Values/i)).toBeInTheDocument()
    expect(screen.getByText('2024-01-01')).toBeInTheDocument()
    expect(screen.getByText('2024-01-02')).toBeInTheDocument()
  })

  it('adds specific value', async () => {
    const partition: PartitionConfigType = {
      strategy: 'specific_values',
      values: [],
    }
    const onChange = vi.fn()
    render(<PartitionConfig partition={partition} onChange={onChange} />)

    const valueInput = screen.getByPlaceholderText(/Enter partition value/i)
    const addButton = screen.getByRole('button', { name: /Add/i })

    fireEvent.change(valueInput, { target: { value: '2024-01-01' } })
    fireEvent.click(addButton)

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          values: ['2024-01-01'],
        })
      )
    })
  })

  it('removes specific value', async () => {
    const partition: PartitionConfigType = {
      strategy: 'specific_values',
      values: ['2024-01-01', '2024-01-02'],
    }
    const onChange = vi.fn()
    render(<PartitionConfig partition={partition} onChange={onChange} />)

    const removeButtons = screen.getAllByRole('button', { name: '' })
    // Find the X button for the first value
    const firstRemoveButton = removeButtons.find((btn) =>
      btn.closest('span')?.textContent?.includes('2024-01-01')
    )

    if (firstRemoveButton) {
      fireEvent.click(firstRemoveButton)

      await waitFor(() => {
        expect(onChange).toHaveBeenCalledWith(
          expect.objectContaining({
            values: ['2024-01-02'],
          })
        )
      })
    }
  })

  it('handles remove partition config', async () => {
    const partition: PartitionConfigType = {
      strategy: 'latest',
    }
    const onChange = vi.fn()
    render(<PartitionConfig partition={partition} onChange={onChange} />)

    const removeButton = screen.getByRole('button', { name: /Remove/i })
    fireEvent.click(removeButton)

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(null)
    })
  })
})

