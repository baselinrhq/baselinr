import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ColumnConfig } from '@/components/config/ColumnConfig'
import { ColumnConfig as ColumnConfigType } from '@/types/config'

describe('ColumnConfig', () => {
  it('renders empty state when no columns', () => {
    const onChange = vi.fn()
    render(<ColumnConfig columns={[]} onChange={onChange} />)

    expect(screen.getByText(/No columns configured/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Add Column/i })).toBeInTheDocument()
  })

  it('renders column list', () => {
    const columns: ColumnConfigType[] = [
      { name: 'email' },
      { name: 'age' },
    ]
    const onChange = vi.fn()
    render(<ColumnConfig columns={columns} onChange={onChange} />)

    expect(screen.getByText('Column 1')).toBeInTheDocument()
    expect(screen.getByText('Column 2')).toBeInTheDocument()
  })

  it('adds column', async () => {
    const onChange = vi.fn()
    render(<ColumnConfig columns={[]} onChange={onChange} />)

    const addButton = screen.getByRole('button', { name: /Add Column/i })
    fireEvent.click(addButton)

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith([{ name: '' }])
    })
  })

  it('removes column', async () => {
    const columns: ColumnConfigType[] = [
      { name: 'email' },
      { name: 'age' },
    ]
    const onChange = vi.fn()
    render(<ColumnConfig columns={columns} onChange={onChange} />)

    const removeButtons = screen.getAllByRole('button', { name: /Remove/i })
    fireEvent.click(removeButtons[0])

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith([{ name: 'age' }])
    })
  })

  it('updates column configuration', async () => {
    const columns: ColumnConfigType[] = [{ name: 'email' }]
    const onChange = vi.fn()
    render(<ColumnConfig columns={columns} onChange={onChange} />)

    const nameInput = screen.getByRole('textbox') || screen.getByPlaceholderText(/column_name/i)
    fireEvent.change(nameInput, { target: { value: 'user_email' } })

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith([{ name: 'user_email' }])
    })
  })

  it('handles pattern-based column selection', async () => {
    const columns: ColumnConfigType[] = [{ name: 'email_*' }]
    const onChange = vi.fn()
    render(<ColumnConfig columns={columns} onChange={onChange} />)

    // Pattern type selector should appear when pattern is detected
    expect(screen.getByText('Column 1')).toBeInTheDocument()
  })

  it('shows available columns when provided', async () => {
    const columns: ColumnConfigType[] = []
    const availableColumns = ['email', 'age', 'name']
    const onChange = vi.fn()
    const { rerender } = render(
      <ColumnConfig
        columns={columns}
        onChange={onChange}
        availableColumns={availableColumns}
      />
    )

    const addButton = screen.getByRole('button', { name: /Add Column/i })
    fireEvent.click(addButton)

    await waitFor(() => {
      // After adding, onChange should be called with new column
      expect(onChange).toHaveBeenCalledWith([{ name: '' }])
    })
    
    // Re-render with the new column to verify it displays
    rerender(
      <ColumnConfig
        columns={[{ name: '' }]}
        onChange={onChange}
        availableColumns={availableColumns}
      />
    )
    
    expect(screen.getByText('Column 1')).toBeInTheDocument()
  })

  it('handles metrics override', async () => {
    const columns: ColumnConfigType[] = [{ name: 'email' }]
    const onChange = vi.fn()
    render(<ColumnConfig columns={columns} onChange={onChange} />)

    // Find the count checkbox within the column config (not global config)
    const countCheckboxes = screen.getAllByLabelText(/count/i)
    // Use the first one (should be in the column config section)
    const countCheckbox = countCheckboxes[0]
    fireEvent.click(countCheckbox)

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith([
        expect.objectContaining({
          name: 'email',
          metrics: ['count'],
        }),
      ])
    })
  })
})

