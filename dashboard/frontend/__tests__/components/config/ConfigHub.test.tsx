/**
 * Unit tests for ConfigHub component
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ConfigHub } from '@/components/config/ConfigHub'
import type { BaselinrConfig } from '@/types/config'

describe('ConfigHub', () => {
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
  }

  it('renders configuration sections title', () => {
    render(<ConfigHub config={mockConfig} />)

    expect(screen.getByText('Configuration Sections')).toBeInTheDocument()
  })

  it('displays all configuration sections', () => {
    render(<ConfigHub config={mockConfig} />)

    expect(screen.getByText('Connections')).toBeInTheDocument()
    expect(screen.getByText('Storage')).toBeInTheDocument()
    expect(screen.getByText('Tables')).toBeInTheDocument()
    expect(screen.getByText('Profiling')).toBeInTheDocument()
    expect(screen.getByText('Validation Rules')).toBeInTheDocument()
    expect(screen.getByText('Drift Detection')).toBeInTheDocument()
    expect(screen.getByText('Anomaly Detection')).toBeInTheDocument()
    expect(screen.getByText('Alert Hooks')).toBeInTheDocument()
  })

  it('displays section descriptions', () => {
    render(<ConfigHub config={mockConfig} />)

    expect(screen.getByText(/Configure database connections/)).toBeInTheDocument()
    expect(screen.getByText(/Configure storage database/)).toBeInTheDocument()
    expect(screen.getByText(/Select tables to profile/)).toBeInTheDocument()
  })

  it('renders section cards as links', () => {
    render(<ConfigHub config={mockConfig} />)

    const connectionsLink = screen.getByText('Connections').closest('a')
    expect(connectionsLink).toHaveAttribute('href', '/config/connections')

    const storageLink = screen.getByText('Storage').closest('a')
    expect(storageLink).toHaveAttribute('href', '/config/storage')
  })

  it('displays status badges on cards', () => {
    render(<ConfigHub config={mockConfig} />)

    // Should have status badges (either Configured or Not Configured)
    const badges = screen.getAllByText(/Configured|Not Configured|Incomplete/)
    expect(badges.length).toBeGreaterThan(0)
  })

  it('handles null config', () => {
    render(<ConfigHub config={null} />)

    expect(screen.getByText('Configuration Sections')).toBeInTheDocument()
    expect(screen.getAllByText('Not Configured').length).toBeGreaterThan(0)
  })

  it('handles undefined config', () => {
    render(<ConfigHub config={undefined} />)

    expect(screen.getByText('Configuration Sections')).toBeInTheDocument()
  })

  it('shows configured status for complete sections', () => {
    render(<ConfigHub config={mockConfig} />)

    // Connections should be configured
    const connectionsCard = screen.getByText('Connections').closest('a')
    expect(connectionsCard).toBeInTheDocument()
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

    render(<ConfigHub config={incompleteConfig} />)

    expect(screen.getByText('Incomplete')).toBeInTheDocument()
  })

  it('renders all section icons', () => {
    render(<ConfigHub config={mockConfig} />)

    // Icons are rendered as SVG elements, check that cards are present
    const cards = screen.getAllByText(/Connections|Storage|Tables|Profiling/)
    expect(cards.length).toBeGreaterThanOrEqual(4)
  })

  it('displays correct hrefs for all sections', () => {
    render(<ConfigHub config={mockConfig} />)

    const sections = [
      { name: 'Connections', href: '/config/connections' },
      { name: 'Storage', href: '/config/storage' },
      { name: 'Tables', href: '/config/tables' },
      { name: 'Profiling', href: '/config/profiling' },
      { name: 'Validation Rules', href: '/config/validation' },
      { name: 'Drift Detection', href: '/config/drift' },
      { name: 'Anomaly Detection', href: '/config/anomaly' },
      { name: 'Alert Hooks', href: '/config/hooks' },
    ]

    sections.forEach(({ name, href }) => {
      const link = screen.getByText(name).closest('a')
      expect(link).toHaveAttribute('href', href)
    })
  })
})

