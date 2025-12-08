import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReferentialRuleForm } from '@/components/validation/ReferentialRuleForm'
import { ValidationRuleConfig } from '@/types/config'
import * as tablesApi from '@/lib/api/tables'
import * as connectionsApi from '@/lib/api/connections'

vi.mock('@/lib/api/tables')
vi.mock('@/lib/api/connections')

describe('ReferentialRuleForm', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })
    vi.clearAllMocks()
  })

  const defaultRule: ValidationRuleConfig = {
    type: 'referential',
    table: 'order_items',
    column: 'order_id',
    references: {
      table: 'orders',
      column: 'id',
      schema: 'public',
    },
    severity: 'high',
    enabled: true,
  }

  const renderComponent = (rule: ValidationRuleConfig = defaultRule) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <ReferentialRuleForm rule={rule} onChange={vi.fn()} />
      </QueryClientProvider>
    )
  }

  it('renders reference configuration', () => {
    vi.mocked(tablesApi.discoverTables).mockResolvedValue({
      tables: [],
      total: 0,
      schemas: [],
    })
    vi.mocked(connectionsApi.listConnections).mockResolvedValue({
      connections: [],
      total: 0,
    })

    renderComponent()

    expect(screen.getByText('Reference Configuration')).toBeInTheDocument()
    expect(screen.getByText('Reference Schema')).toBeInTheDocument()
    expect(screen.getByText('Reference Table')).toBeInTheDocument()
    expect(screen.getByText('Reference Column')).toBeInTheDocument()
  })

  it('displays relationship preview', () => {
    vi.mocked(tablesApi.discoverTables).mockResolvedValue({
      tables: [],
      total: 0,
      schemas: [],
    })
    vi.mocked(connectionsApi.listConnections).mockResolvedValue({
      connections: [],
      total: 0,
    })

    renderComponent()

    expect(screen.getByText(/order_items.order_id/i)).toBeInTheDocument()
  })

  it('loads tables for reference table selector', async () => {
    vi.mocked(tablesApi.discoverTables).mockResolvedValue({
      tables: [
        { schema: 'public', table: 'orders', table_type: 'table' },
        { schema: 'public', table: 'customers', table_type: 'table' },
      ],
      total: 2,
      schemas: ['public'],
    })
    vi.mocked(connectionsApi.listConnections).mockResolvedValue({
      connections: [],
      total: 0,
    })

    renderComponent()

    await waitFor(() => {
      expect(tablesApi.discoverTables).toHaveBeenCalled()
    })
  })

  it('loads columns for reference column selector', async () => {
    vi.mocked(tablesApi.discoverTables).mockResolvedValue({
      tables: [{ schema: 'public', table: 'orders', table_type: 'table' }],
      total: 1,
      schemas: ['public'],
    })
    vi.mocked(tablesApi.getTablePreview).mockResolvedValue({
      schema: 'public',
      table: 'orders',
      columns: [
        { name: 'id', type: 'INTEGER', nullable: false },
        { name: 'customer_id', type: 'INTEGER', nullable: true },
      ],
      row_count: 100,
      table_type: 'table',
    })
    vi.mocked(connectionsApi.listConnections).mockResolvedValue({
      connections: [],
      total: 0,
    })

    renderComponent()

    await waitFor(() => {
      expect(tablesApi.getTablePreview).toHaveBeenCalled()
    })
  })
})

