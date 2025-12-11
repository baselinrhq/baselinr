/**
 * Unit tests for ConfigDiff component
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ConfigDiff } from '@/components/config/ConfigDiff'
import { ConfigDiffResponse } from '@/types/config'

describe('ConfigDiff', () => {
  const mockDiff: ConfigDiffResponse = {
    version_id: 'version-1',
    compare_with: 'current',
    added: {
      'new_feature': { enabled: true },
    },
    removed: {
      'old_feature': { enabled: false },
    },
    changed: {
      'storage.connection.database': {
        old: 'old_db',
        new: 'new_db',
      },
    },
  }

  it('renders diff component', () => {
    render(<ConfigDiff diff={mockDiff} />)
    expect(screen.getByText('Configuration Diff')).toBeInTheDocument()
  })

  it('displays version information', () => {
    render(<ConfigDiff diff={mockDiff} />)
    expect(screen.getByText(/Comparing version/i)).toBeInTheDocument()
    expect(screen.getByText(/with current/i)).toBeInTheDocument()
  })

  it('shows diff summary', () => {
    render(<ConfigDiff diff={mockDiff} />)
    expect(screen.getByText(/1 added/i)).toBeInTheDocument()
    expect(screen.getByText(/1 removed/i)).toBeInTheDocument()
    expect(screen.getByText(/1 changed/i)).toBeInTheDocument()
  })

  it('displays added values', () => {
    render(<ConfigDiff diff={mockDiff} />)
    expect(screen.getByText('new_feature')).toBeInTheDocument()
  })

  it('displays removed values', () => {
    render(<ConfigDiff diff={mockDiff} />)
    expect(screen.getByText('old_feature')).toBeInTheDocument()
  })

  it('displays changed values', () => {
    render(<ConfigDiff diff={mockDiff} />)
    // In tree view, we need to expand the section first
    const storageSection = screen.getByText('storage')
    fireEvent.click(storageSection.closest('button')!)
    expect(screen.getByText('storage.connection.database')).toBeInTheDocument()
  })

  it('switches view modes', () => {
    render(<ConfigDiff diff={mockDiff} />)
    
    const sideBySideButton = screen.getByText('Side-by-Side')
    fireEvent.click(sideBySideButton)
    
    // Should show side-by-side view
    expect(screen.getByText('Removed / Old Values')).toBeInTheDocument()
    expect(screen.getByText('Added / New Values')).toBeInTheDocument()
  })

  it('calls onClose when close button is clicked', () => {
    const mockOnClose = vi.fn()
    render(<ConfigDiff diff={mockDiff} onClose={mockOnClose} />)
    
    const closeButton = screen.getByText('Close')
    fireEvent.click(closeButton)
    
    expect(mockOnClose).toHaveBeenCalled()
  })

  it('shows no differences message when diff is empty', () => {
    const emptyDiff: ConfigDiffResponse = {
      version_id: 'version-1',
      compare_with: 'current',
      added: {},
      removed: {},
      changed: {},
    }

    render(<ConfigDiff diff={emptyDiff} />)
    expect(screen.getByText(/No differences found/i)).toBeInTheDocument()
  })

  it('expands and collapses sections in tree view', () => {
    render(<ConfigDiff diff={mockDiff} />)
    
    // Find a section header and click it
    const storageSection = screen.getByText('storage')
    fireEvent.click(storageSection.closest('button')!)
    
    // Should show expanded content
    expect(screen.getByText('storage.connection.database')).toBeInTheDocument()
  })
})

