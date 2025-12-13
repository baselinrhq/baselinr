/**
 * Tests for ValidationRulesList component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import userEvent from '@testing-library/user-event'
import ValidationRulesList from '@/components/validation/ValidationRulesList'
import * as validationRulesAPI from '@/lib/api/validationRules'
import type { ValidationRule } from '@/types/validationRules'

// Mock the API
vi.mock('@/lib/api/validationRules')

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

const mockRule: ValidationRule = {
  id: 'rule-1',
  rule_type: 'format',
  table: 'users',
  schema: 'public',
  column: 'email',
  config: { pattern: 'email' },
  severity: 'high',
  enabled: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: null,
  last_tested: null,
  last_test_result: null,
}

describe('ValidationRulesList', () => {
  const mockOnCreateRule = vi.fn()
  const mockOnEditRule = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    ;(validationRulesAPI.listValidationRules as ReturnType<typeof vi.fn>).mockResolvedValue({
      rules: [mockRule],
      total: 1,
    })
  })

  it('renders loading state', () => {
    ;(validationRulesAPI.listValidationRules as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    render(
      <ValidationRulesList onCreateRule={mockOnCreateRule} onEditRule={mockOnEditRule} />,
      { wrapper: createWrapper() }
    )

    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('renders validation rules list', async () => {
    render(
      <ValidationRulesList onCreateRule={mockOnCreateRule} onEditRule={mockOnEditRule} />,
      { wrapper: createWrapper() }
    )

    await waitFor(() => {
      expect(screen.getByText('public.users.email')).toBeInTheDocument()
    })

    expect(screen.getByText('Format')).toBeInTheDocument()
    expect(screen.getByText('high')).toBeInTheDocument()
    expect(screen.getByText('Enabled')).toBeInTheDocument()
  })

  it('renders empty state when no rules', async () => {
    ;(validationRulesAPI.listValidationRules as ReturnType<typeof vi.fn>).mockResolvedValue({
      rules: [],
      total: 0,
    })

    render(
      <ValidationRulesList onCreateRule={mockOnCreateRule} onEditRule={mockOnEditRule} />,
      { wrapper: createWrapper() }
    )

    await waitFor(() => {
      expect(screen.getByText('No validation rules')).toBeInTheDocument()
    })

    expect(screen.getByText('Create your first validation rule to get started')).toBeInTheDocument()
  })

  it('calls onCreateRule when create button is clicked', async () => {
    ;(validationRulesAPI.listValidationRules as ReturnType<typeof vi.fn>).mockResolvedValue({
      rules: [],
      total: 0,
    })

    render(
      <ValidationRulesList onCreateRule={mockOnCreateRule} onEditRule={mockOnEditRule} />,
      { wrapper: createWrapper() }
    )

    await waitFor(() => {
      expect(screen.getByText('Create Rule')).toBeInTheDocument()
    })

    const createButton = screen.getByText('Create Rule')
    await userEvent.click(createButton)

    expect(mockOnCreateRule).toHaveBeenCalledTimes(1)
  })

  it('calls onEditRule when edit button is clicked', async () => {
    render(
      <ValidationRulesList onCreateRule={mockOnCreateRule} onEditRule={mockOnEditRule} />,
      { wrapper: createWrapper() }
    )

    await waitFor(() => {
      expect(screen.getByText('public.users.email')).toBeInTheDocument()
    })

    // Find edit button by aria-label
    const editButton = screen.getByRole('button', { name: 'Edit rule' })
    await userEvent.click(editButton)

    expect(mockOnEditRule).toHaveBeenCalledWith(mockRule)
  })

  it('filters rules by search query', async () => {
    const rules = [
      mockRule,
      {
        ...mockRule,
        id: 'rule-2',
        table: 'orders',
        column: 'amount',
      },
    ]

    ;(validationRulesAPI.listValidationRules as ReturnType<typeof vi.fn>).mockResolvedValue({
      rules,
      total: 2,
    })

    render(
      <ValidationRulesList onCreateRule={mockOnCreateRule} onEditRule={mockOnEditRule} />,
      { wrapper: createWrapper() }
    )

    await waitFor(() => {
      expect(screen.getByText('public.users.email')).toBeInTheDocument()
    })

    const searchInput = screen.getByPlaceholderText('Search rules...')
    await userEvent.type(searchInput, 'orders')

    await waitFor(() => {
      expect(screen.queryByText('public.users.email')).not.toBeInTheDocument()
      expect(screen.getByText('public.orders.amount')).toBeInTheDocument()
    })
  })

  it('shows error state on API failure', async () => {
    ;(validationRulesAPI.listValidationRules as ReturnType<typeof vi.fn>).mockRejectedValue(
      new validationRulesAPI.ValidationRulesError('API error', 500)
    )

    render(
      <ValidationRulesList onCreateRule={mockOnCreateRule} onEditRule={mockOnEditRule} />,
      { wrapper: createWrapper() }
    )

    await waitFor(() => {
      // Check for error message - it should show the error text
      expect(screen.getByRole('alert')).toBeInTheDocument()
      // The error message should be displayed (either "API error" or "Failed to load validation rules")
      const errorText = screen.getByText(/API error|Failed to load validation rules/i)
      expect(errorText).toBeInTheDocument()
    })
  })
})

