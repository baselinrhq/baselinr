/**
 * Unit tests for StorageStatus component
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { StorageStatus } from '@/components/config/StorageStatus'
import type { StorageStatusResponse } from '@/types/config'

describe('StorageStatus', () => {
  const mockStatus: StorageStatusResponse = {
    connection_status: 'connected',
    results_table_exists: true,
    runs_table_exists: false,
    last_checked: '2024-01-01T12:00:00Z',
  }

  const mockOnRefresh = vi.fn()

  it('renders storage status title', () => {
    render(<StorageStatus status={mockStatus} />)

    expect(screen.getByText('Storage Status')).toBeInTheDocument()
  })

  it('displays connection status correctly when connected', () => {
    render(<StorageStatus status={mockStatus} />)

    expect(screen.getByText('Connected')).toBeInTheDocument()
  })

  it('displays connection status correctly when disconnected', () => {
    const disconnectedStatus: StorageStatusResponse = {
      ...mockStatus,
      connection_status: 'disconnected',
    }
    render(<StorageStatus status={disconnectedStatus} />)

    expect(screen.getByText('Disconnected')).toBeInTheDocument()
  })

  it('displays connection status correctly when error', () => {
    const errorStatus: StorageStatusResponse = {
      ...mockStatus,
      connection_status: 'error',
      connection_error: 'Connection failed',
    }
    render(<StorageStatus status={errorStatus} />)

    expect(screen.getByText('Error')).toBeInTheDocument()
    expect(screen.getByText('Connection failed')).toBeInTheDocument()
  })

  it('displays table existence status', () => {
    render(<StorageStatus status={mockStatus} />)

    expect(screen.getByText('Results Table')).toBeInTheDocument()
    expect(screen.getByText('Runs Table')).toBeInTheDocument()
    expect(screen.getByText('Exists')).toBeInTheDocument()
    expect(screen.getByText('Missing')).toBeInTheDocument()
  })

  it('displays last checked timestamp', () => {
    render(<StorageStatus status={mockStatus} />)

    expect(screen.getByText(/Last checked:/)).toBeInTheDocument()
  })

  it('shows loading state', () => {
    render(<StorageStatus isLoading={true} />)

    expect(screen.getByText('Checking status...')).toBeInTheDocument()
  })

  it('shows error state', () => {
    render(<StorageStatus error="Failed to check status" />)

    expect(screen.getByText('Error checking status')).toBeInTheDocument()
    expect(screen.getByText('Failed to check status')).toBeInTheDocument()
  })

  it('calls onRefresh when refresh button is clicked', () => {
    render(<StorageStatus status={mockStatus} onRefresh={mockOnRefresh} />)

    const refreshButton = screen.getByRole('button', { name: /Refresh/i })
    fireEvent.click(refreshButton)

    expect(mockOnRefresh).toHaveBeenCalledTimes(1)
  })

  it('disables refresh button when loading', () => {
    render(<StorageStatus status={mockStatus} isLoading={true} onRefresh={mockOnRefresh} />)

    const refreshButton = screen.getByRole('button', { name: /Checking/i })
    expect(refreshButton).toBeDisabled()
  })

  it('shows empty state when no status available', () => {
    render(<StorageStatus />)

    expect(screen.getByText('No status information available')).toBeInTheDocument()
    expect(screen.getByText(/Click Refresh to check storage status/)).toBeInTheDocument()
  })
})

