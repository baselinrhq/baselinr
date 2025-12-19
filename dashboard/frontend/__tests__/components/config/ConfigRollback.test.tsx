/**
 * Unit tests for ConfigRollback component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ConfigRollback } from '@/components/config/ConfigRollback'
import { ConfigVersionResponse } from '@/types/config'

// Mock Modal
vi.mock('@/components/ui/Modal', () => ({
  Modal: ({ isOpen, children, title, onClose }: any) => {
    if (!isOpen) return null
    return (
      <div data-testid="modal" role="dialog">
        <div className="flex items-center justify-between mb-4">
          <h2>{title}</h2>
          <button onClick={onClose}>Close</button>
        </div>
        {children}
      </div>
    )
  },
}))

describe('ConfigRollback', () => {
  const mockVersionData: ConfigVersionResponse = {
    version_id: 'version-1',
    config: {
      environment: 'development',
      source: { type: 'postgres', database: 'test_db' },
    },
    created_at: new Date().toISOString(),
    created_by: 'user1',
    description: 'Test version',
  }

  const mockOnConfirm = vi.fn().mockResolvedValue(undefined)
  const mockOnCancel = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders rollback modal when open', () => {
    render(
      <ConfigRollback
        versionId="version-1"
        versionData={mockVersionData}
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        isOpen={true}
      />
    )

    expect(screen.getAllByText('Restore Configuration Version').length).toBeGreaterThan(0)
  })

  it('does not render when closed', () => {
    render(
      <ConfigRollback
        versionId="version-1"
        versionData={mockVersionData}
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        isOpen={false}
      />
    )

    expect(screen.queryByTestId('modal')).not.toBeInTheDocument()
  })

  it('displays version information', () => {
    render(
      <ConfigRollback
        versionId="version-1"
        versionData={mockVersionData}
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        isOpen={true}
      />
    )

    expect(screen.getByText(/Version ID:/i)).toBeInTheDocument()
    expect(screen.getByText(/Created:/i)).toBeInTheDocument()
    expect(screen.getByText('Test version')).toBeInTheDocument()
  })

  it('allows entering a comment', () => {
    render(
      <ConfigRollback
        versionId="version-1"
        versionData={mockVersionData}
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        isOpen={true}
      />
    )

    const commentInput = screen.getByPlaceholderText(/Rolling back/i)
    fireEvent.change(commentInput, { target: { value: 'Restoring due to issues' } })

    expect(commentInput).toHaveValue('Restoring due to issues')
  })

  it('calls onConfirm with comment when restore is clicked', async () => {
    render(
      <ConfigRollback
        versionId="version-1"
        versionData={mockVersionData}
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        isOpen={true}
      />
    )

    const commentInput = screen.getByPlaceholderText(/Rolling back/i)
    fireEvent.change(commentInput, { target: { value: 'Test comment' } })

    const restoreButton = screen.getByText('Restore Configuration')
    fireEvent.click(restoreButton)

    await waitFor(() => {
      expect(mockOnConfirm).toHaveBeenCalledWith('Test comment')
    })
  })

  it('calls onConfirm without comment when restore is clicked without comment', async () => {
    render(
      <ConfigRollback
        versionId="version-1"
        versionData={mockVersionData}
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        isOpen={true}
      />
    )

    const restoreButton = screen.getByText('Restore Configuration')
    fireEvent.click(restoreButton)

    await waitFor(() => {
      expect(mockOnConfirm).toHaveBeenCalledWith(undefined)
    })
  })

  it('calls onCancel when cancel is clicked', () => {
    render(
      <ConfigRollback
        versionId="version-1"
        versionData={mockVersionData}
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        isOpen={true}
      />
    )

    const cancelButton = screen.getByText('Cancel')
    fireEvent.click(cancelButton)

    expect(mockOnCancel).toHaveBeenCalled()
  })

  it('shows loading state during restore', async () => {
    const slowConfirm = vi.fn().mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))

    render(
      <ConfigRollback
        versionId="version-1"
        versionData={mockVersionData}
        onConfirm={slowConfirm}
        onCancel={mockOnCancel}
        isOpen={true}
      />
    )

    const restoreButton = screen.getByText('Restore Configuration')
    fireEvent.click(restoreButton)

    await waitFor(() => {
      expect(screen.getByText('Restoring...')).toBeInTheDocument()
    })
  })

  it('displays error message on restore failure', async () => {
    const failingConfirm = vi.fn().mockRejectedValue(new Error('Restore failed'))

    render(
      <ConfigRollback
        versionId="version-1"
        versionData={mockVersionData}
        onConfirm={failingConfirm}
        onCancel={mockOnCancel}
        isOpen={true}
      />
    )

    const restoreButton = screen.getByText('Restore Configuration')
    fireEvent.click(restoreButton)

    await waitFor(() => {
      expect(screen.getByText(/Restore failed/i)).toBeInTheDocument()
    })
  })

  it('disables inputs during restore', async () => {
    const slowConfirm = vi.fn().mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))

    render(
      <ConfigRollback
        versionId="version-1"
        versionData={mockVersionData}
        onConfirm={slowConfirm}
        onCancel={mockOnCancel}
        isOpen={true}
      />
    )

    const restoreButton = screen.getByText('Restore Configuration')
    fireEvent.click(restoreButton)

    await waitFor(() => {
      const commentInput = screen.getByPlaceholderText(/Rolling back/i)
      expect(commentInput).toBeDisabled()
    })
  })
})

