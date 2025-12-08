/**
 * Unit tests for HookCard component
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { HookCard } from '@/components/config/HookCard'
import type { HookWithId } from '@/types/hook'

describe('HookCard', () => {
  const mockHook: HookWithId = {
    id: '0',
    hook: {
      type: 'logging',
      enabled: true,
      log_level: 'INFO',
    },
  }

  const mockOnEdit = vi.fn()
  const mockOnDelete = vi.fn()
  const mockOnTest = vi.fn()

  it('renders hook information', () => {
    render(
      <HookCard
        hook={mockHook}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    expect(screen.getByText('Logging')).toBeInTheDocument()
    expect(screen.getByText('Enabled')).toBeInTheDocument()
  })

  it('displays hook summary for logging hook', () => {
    render(
      <HookCard
        hook={mockHook}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    expect(screen.getByText(/Level: INFO/)).toBeInTheDocument()
  })

  it('displays hook summary for slack hook', () => {
    const slackHook: HookWithId = {
      id: '1',
      hook: {
        type: 'slack',
        enabled: true,
        webhook_url: 'https://hooks.slack.com/test',
        channel: '#alerts',
        min_severity: 'medium',
      },
    }

    render(
      <HookCard
        hook={slackHook}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    expect(screen.getByText(/Channel: #alerts/)).toBeInTheDocument()
    expect(screen.getByText(/Min severity: medium/)).toBeInTheDocument()
  })

  it('calls onEdit when edit button is clicked', () => {
    render(
      <HookCard
        hook={mockHook}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    const editButton = screen.getByText('Edit')
    fireEvent.click(editButton)

    expect(mockOnEdit).toHaveBeenCalledWith('0')
  })

  it('calls onDelete when delete button is clicked twice', () => {
    render(
      <HookCard
        hook={mockHook}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    const deleteButton = screen.getByText('Delete')
    fireEvent.click(deleteButton)

    // First click shows confirm button
    expect(screen.getByText('Confirm')).toBeInTheDocument()

    const confirmButton = screen.getByText('Confirm')
    fireEvent.click(confirmButton)

    expect(mockOnDelete).toHaveBeenCalledWith('0')
  })

  it('calls onTest when test button is clicked', () => {
    render(
      <HookCard
        hook={mockHook}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    const testButton = screen.getByText('Test')
    fireEvent.click(testButton)

    expect(mockOnTest).toHaveBeenCalledWith('0')
  })

  it('shows disabled badge when hook is disabled', () => {
    const disabledHook: HookWithId = {
      id: '2',
      hook: {
        type: 'logging',
        enabled: false,
      },
    }

    render(
      <HookCard
        hook={disabledHook}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    expect(screen.getByText('Disabled')).toBeInTheDocument()
  })

  it('displays last tested date when available', () => {
    const hookWithTest: HookWithId = {
      id: '3',
      hook: {
        type: 'logging',
        enabled: true,
      },
      last_tested: '2024-01-01T00:00:00Z',
      test_status: 'success',
    }

    render(
      <HookCard
        hook={hookWithTest}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    expect(screen.getByText(/Last tested:/)).toBeInTheDocument()
  })
})

