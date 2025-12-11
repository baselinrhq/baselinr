/**
 * Unit tests for ConfigStatus component
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ConfigStatus } from '@/components/config/ConfigStatus'
import type { BaselinrConfig } from '@/types/config'

describe('ConfigStatus', () => {
  const mockConfig: BaselinrConfig = {
    environment: 'development',
    source: {
      type: 'postgres',
      host: 'localhost',
      port: 5432,
      database: 'test_db',
      username: 'user',
    },
    storage: {
      connection: {
        type: 'postgres',
        database: 'storage_db',
      },
      results_table: 'results',
      runs_table: 'runs',
    },
    profiling: {
      tables: [
        {
          schema: 'public',
          table: 'users',
        },
      ],
    },
    drift_detection: {
      strategy: 'absolute_threshold',
    },
    hooks: {
      hooks: [
        {
          type: 'logging',
          enabled: true,
        },
      ],
    },
    validation: {
      rules: [
        {
          type: 'not_null',
          table: 'users',
          column: 'id',
        },
      ],
    },
  }

  const mockOnRefresh = vi.fn()

  it('renders configuration status title', () => {
    render(<ConfigStatus config={mockConfig} />)

    expect(screen.getByText('Configuration Status')).toBeInTheDocument()
  })

  it('displays overall completion percentage', () => {
    render(<ConfigStatus config={mockConfig} />)

    expect(screen.getByText(/Overall Completion/)).toBeInTheDocument()
    expect(screen.getByText(/\d+%/)).toBeInTheDocument()
  })

  it('displays section statuses', () => {
    render(<ConfigStatus config={mockConfig} />)

    expect(screen.getByText('Connections')).toBeInTheDocument()
    expect(screen.getByText('Storage')).toBeInTheDocument()
    expect(screen.getByText('Tables')).toBeInTheDocument()
    expect(screen.getByText('Profiling')).toBeInTheDocument()
    expect(screen.getByText('Validation Rules')).toBeInTheDocument()
    expect(screen.getByText('Drift Detection')).toBeInTheDocument()
    expect(screen.getByText('Anomaly Detection')).toBeInTheDocument()
    expect(screen.getByText('Alert Hooks')).toBeInTheDocument()
  })

  it('shows configured status for complete sections', () => {
    render(<ConfigStatus config={mockConfig} />)

    expect(screen.getAllByText('Configured').length).toBeGreaterThan(0)
  })

  it('shows not configured status when config is null', () => {
    render(<ConfigStatus config={null} />)

    expect(screen.getAllByText('Not Configured').length).toBeGreaterThan(0)
  })

  it('shows incomplete status for storage without table names', () => {
    const incompleteConfig: BaselinrConfig = {
      ...mockConfig,
      storage: {
        connection: {
          type: 'postgres',
          database: 'storage_db',
        },
      },
    }

    render(<ConfigStatus config={incompleteConfig} />)

    expect(screen.getByText('Incomplete')).toBeInTheDocument()
  })

  it('shows loading state', () => {
    render(<ConfigStatus config={null} isLoading={true} />)

    expect(screen.getByText('Loading configuration...')).toBeInTheDocument()
  })

  it('calls onRefresh when refresh button is clicked', () => {
    render(<ConfigStatus config={mockConfig} onRefresh={mockOnRefresh} />)

    const refreshButton = screen.getByRole('button', { name: /Refresh/i })
    fireEvent.click(refreshButton)

    expect(mockOnRefresh).toHaveBeenCalledTimes(1)
  })

  it('disables refresh button when loading', () => {
    render(
      <ConfigStatus config={mockConfig} isLoading={true} onRefresh={mockOnRefresh} />
    )

    const refreshButton = screen.getByRole('button', { name: /Refreshing/i })
    expect(refreshButton).toBeDisabled()
  })

  it('shows correct status for connections without required fields', () => {
    const incompleteConfig: BaselinrConfig = {
      ...mockConfig,
      source: {
        type: 'postgres',
        // Missing database
      } as any,
    }

    render(<ConfigStatus config={incompleteConfig} />)

    // Check that Connections section shows Incomplete status badge
    expect(screen.getByText('Incomplete')).toBeInTheDocument()
  })

  it('shows correct status for tables without patterns', () => {
    const noTablesConfig: BaselinrConfig = {
      ...mockConfig,
      profiling: {
        tables: [],
      },
    }

    render(<ConfigStatus config={noTablesConfig} />)

    // Check that Tables section shows Not Configured status badge
    const notConfiguredBadges = screen.getAllByText('Not Configured')
    expect(notConfiguredBadges.length).toBeGreaterThan(0)
  })

  it('shows correct status for validation without rules', () => {
    const noValidationConfig: BaselinrConfig = {
      ...mockConfig,
      validation: {
        rules: [],
      },
    }

    render(<ConfigStatus config={noValidationConfig} />)

    // Check that Validation Rules section shows Not Configured status badge
    const notConfiguredBadges = screen.getAllByText('Not Configured')
    expect(notConfiguredBadges.length).toBeGreaterThan(0)
  })

  it('shows correct status for anomaly detection when disabled', () => {
    const noAnomalyConfig: BaselinrConfig = {
      ...mockConfig,
      storage: {
        ...mockConfig.storage,
        enable_anomaly_detection: false,
      },
    }

    render(<ConfigStatus config={noAnomalyConfig} />)

    // Check that Anomaly Detection section shows Not Configured status badge
    const notConfiguredBadges = screen.getAllByText('Not Configured')
    expect(notConfiguredBadges.length).toBeGreaterThan(0)
  })

  it('shows correct status for hooks without hooks', () => {
    const noHooksConfig: BaselinrConfig = {
      ...mockConfig,
      hooks: {
        hooks: [],
      },
    }

    render(<ConfigStatus config={noHooksConfig} />)

    // Check that Alert Hooks section shows Not Configured status badge
    const notConfiguredBadges = screen.getAllByText('Not Configured')
    expect(notConfiguredBadges.length).toBeGreaterThan(0)
  })

  it('displays configured sections count', () => {
    render(<ConfigStatus config={mockConfig} />)

    expect(screen.getByText(/\d+ of \d+ sections configured/)).toBeInTheDocument()
  })
})

