/**
 * Unit tests for ConnectionCard component
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ConnectionCard } from '@/components/config/ConnectionCard'
import type { SavedConnection } from '@/types/connection'

describe('ConnectionCard', () => {
  const mockConnection: SavedConnection = {
    id: '1',
    name: 'Test Connection',
    connection: {
      type: 'postgres',
      host: 'localhost',
      port: 5432,
      database: 'test_db',
      username: 'user',
    },
    created_at: '2024-01-01T00:00:00Z',
    is_active: true,
  }

  const mockOnEdit = vi.fn()
  const mockOnDelete = vi.fn()
  const mockOnTest = vi.fn()
  const mockOnUseAsSource = vi.fn()

  it('renders connection information', () => {
    render(
      <ConnectionCard
        connection={mockConnection}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    expect(screen.getByText('Test Connection')).toBeInTheDocument()
    expect(screen.getByText('PostgreSQL')).toBeInTheDocument()
  })

  it('displays connection summary', () => {
    render(
      <ConnectionCard
        connection={mockConnection}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    expect(screen.getByText(/localhost:5432\/test_db/)).toBeInTheDocument()
  })

  it('calls onEdit when edit button is clicked', () => {
    render(
      <ConnectionCard
        connection={mockConnection}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    const editButton = screen.getByText('Edit')
    fireEvent.click(editButton)

    expect(mockOnEdit).toHaveBeenCalledWith('1')
  })

  it('calls onTest when test button is clicked', () => {
    render(
      <ConnectionCard
        connection={mockConnection}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    const testButton = screen.getByText('Test')
    fireEvent.click(testButton)

    expect(mockOnTest).toHaveBeenCalledWith('1')
  })

  it('shows delete confirmation before deleting', () => {
    render(
      <ConnectionCard
        connection={mockConnection}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    const deleteButton = screen.getByText('Delete')
    fireEvent.click(deleteButton)

    // Should show confirm button
    expect(screen.getByText('Confirm')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
  })

  it('calls onDelete when delete is confirmed', () => {
    render(
      <ConnectionCard
        connection={mockConnection}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    const deleteButton = screen.getByText('Delete')
    fireEvent.click(deleteButton)

    const confirmButton = screen.getByText('Confirm')
    fireEvent.click(confirmButton)

    expect(mockOnDelete).toHaveBeenCalledWith('1')
  })

  it('calls onUseAsSource when provided and clicked', () => {
    render(
      <ConnectionCard
        connection={mockConnection}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
        onUseAsSource={mockOnUseAsSource}
      />
    )

    const useAsSourceButton = screen.getByText('Use as Source')
    fireEvent.click(useAsSourceButton)

    expect(mockOnUseAsSource).toHaveBeenCalledWith('1')
  })

  it('displays last tested timestamp when available', () => {
    const connectionWithTest: SavedConnection = {
      ...mockConnection,
      last_tested: '2024-01-02T12:00:00Z',
    }

    render(
      <ConnectionCard
        connection={connectionWithTest}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    expect(screen.getByText(/Last tested:/)).toBeInTheDocument()
  })

  it('displays active badge when connection is active', () => {
    render(
      <ConnectionCard
        connection={mockConnection}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  it('handles Snowflake connection type', () => {
    const snowflakeConnection: SavedConnection = {
      ...mockConnection,
      connection: {
        type: 'snowflake',
        account: 'account.region',
        database: 'test_db',
        username: 'user',
      },
    }

    render(
      <ConnectionCard
        connection={snowflakeConnection}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    expect(screen.getByText('Snowflake')).toBeInTheDocument()
  })
})

