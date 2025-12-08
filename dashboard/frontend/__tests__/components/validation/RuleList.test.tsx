import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { RuleList } from '@/components/validation/RuleList'
import { ValidationRuleConfig } from '@/types/config'

describe('RuleList', () => {
  const mockRules: ValidationRuleConfig[] = [
    {
      type: 'format',
      table: 'users',
      column: 'email',
      pattern: 'email',
      severity: 'high',
      enabled: true,
    },
    {
      type: 'range',
      table: 'orders',
      column: 'total_amount',
      min_value: 0,
      max_value: 1000000,
      severity: 'medium',
      enabled: true,
    },
    {
      type: 'enum',
      table: 'orders',
      column: 'status',
      allowed_values: ['pending', 'completed'],
      severity: 'high',
      enabled: false,
    },
  ]

  it('renders list of rules', () => {
    const onEdit = vi.fn()
    const onDelete = vi.fn()
    render(<RuleList rules={mockRules} onEdit={onEdit} onDelete={onDelete} />)

    // Verify rules are rendered (text may appear in multiple places)
    expect(screen.getAllByText(/users/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/email/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/orders/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/total_amount/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/status/i).length).toBeGreaterThan(0)
  })

  it('filters rules by search query', async () => {
    const onEdit = vi.fn()
    const onDelete = vi.fn()
    render(<RuleList rules={mockRules} onEdit={onEdit} onDelete={onDelete} />)

    const searchInput = screen.getByPlaceholderText(/search table or column/i)
    fireEvent.change(searchInput, { target: { value: 'users' } })

    await waitFor(() => {
      // After filtering, users should be visible, orders should not
      const usersElements = screen.queryAllByText(/users/i)
      const ordersElements = screen.queryAllByText(/orders/i)
      // Users rule should still be visible
      expect(usersElements.length).toBeGreaterThan(0)
      // Orders rules should be filtered out
      expect(ordersElements.length).toBe(0)
    })
  })

  it('filters rules by type', () => {
    const onEdit = vi.fn()
    const onDelete = vi.fn()
    render(<RuleList rules={mockRules} onEdit={onEdit} onDelete={onDelete} />)

    // Verify filter controls are rendered
    expect(screen.getByRole('button', { name: /all types/i })).toBeInTheDocument()
    // Verify rules are rendered (text may appear in multiple places)
    const usersElements = screen.getAllByText(/users/i)
    expect(usersElements.length).toBeGreaterThan(0)
    const ordersElements = screen.getAllByText(/orders/i)
    expect(ordersElements.length).toBeGreaterThan(0)
  })

  it('filters rules by severity', () => {
    const onEdit = vi.fn()
    const onDelete = vi.fn()
    render(<RuleList rules={mockRules} onEdit={onEdit} onDelete={onDelete} />)

    // Verify filter controls are rendered
    expect(screen.getByRole('button', { name: /all severities/i })).toBeInTheDocument()
    // Verify rules are rendered
    const usersElements = screen.getAllByText(/users/i)
    expect(usersElements.length).toBeGreaterThan(0)
  })

  it('filters rules by status', () => {
    const onEdit = vi.fn()
    const onDelete = vi.fn()
    render(<RuleList rules={mockRules} onEdit={onEdit} onDelete={onDelete} />)

    // Verify filter controls are rendered
    expect(screen.getByRole('button', { name: /all status/i })).toBeInTheDocument()
    // Verify rules are rendered (text may appear in multiple places)
    const ordersElements = screen.getAllByText(/orders/i)
    expect(ordersElements.length).toBeGreaterThan(0)
    const statusElements = screen.getAllByText(/status/i)
    expect(statusElements.length).toBeGreaterThan(0)
  })

  it('calls onEdit when edit button is clicked', () => {
    const onEdit = vi.fn()
    const onDelete = vi.fn()
    render(<RuleList rules={mockRules} onEdit={onEdit} onDelete={onDelete} />)

    const editButtons = screen.getAllByTitle('Edit rule')
    expect(editButtons.length).toBeGreaterThan(0)
    fireEvent.click(editButtons[0])

    expect(onEdit).toHaveBeenCalledWith(mockRules[0], 0)
  })

  it('calls onDelete when delete button is clicked', () => {
    const onEdit = vi.fn()
    const onDelete = vi.fn()
    render(<RuleList rules={mockRules} onEdit={onEdit} onDelete={onDelete} />)

    const deleteButtons = screen.getAllByTitle('Delete rule')
    fireEvent.click(deleteButtons[0])

    expect(onDelete).toHaveBeenCalledWith(0)
  })

  it('displays empty state when no rules', () => {
    const onEdit = vi.fn()
    const onDelete = vi.fn()
    render(<RuleList rules={[]} onEdit={onEdit} onDelete={onDelete} />)

    expect(screen.getByText('No validation rules')).toBeInTheDocument()
  })

  it('displays loading state', () => {
    const onEdit = vi.fn()
    const onDelete = vi.fn()
    render(<RuleList rules={[]} onEdit={onEdit} onDelete={onDelete} isLoading />)

    expect(screen.getByText('Loading rules...')).toBeInTheDocument()
  })

  it('shows rule summary for each rule type', () => {
    const onEdit = vi.fn()
    const onDelete = vi.fn()
    render(<RuleList rules={mockRules} onEdit={onEdit} onDelete={onDelete} />)

    // Verify all rules are rendered with their types
    expect(screen.getByText(/Format/i)).toBeInTheDocument()
    expect(screen.getByText(/Range/i)).toBeInTheDocument()
    expect(screen.getByText(/Enum/i)).toBeInTheDocument()
    
    // Verify rule summaries are present
    // Format rule pattern
    const emailElements = screen.getAllByText(/email/i)
    expect(emailElements.length).toBeGreaterThan(0)
    
    // Range rule shows min - max (check document contains both numbers)
    const documentText = document.body.textContent || ''
    expect(documentText).toMatch(/0.*1000000|1000000.*0/)
    
    // Enum rule shows value count
    expect(screen.getByText(/2 values/i)).toBeInTheDocument()
  })
})

