import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import LineageSearch from '@/components/lineage/LineageSearch'
import * as lineageApi from '@/lib/api/lineage'
import type { TableInfoResponse } from '@/types/lineage'

// Mock the API
vi.mock('@/lib/api/lineage', () => ({
  searchTables: vi.fn(),
  getAllTables: vi.fn(),
}))

describe('LineageSearch', () => {
  const mockOnTableSelect = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    // Clear localStorage
    localStorage.clear()
  })

  it('renders search input', () => {
    render(
      <LineageSearch
        onTableSelect={mockOnTableSelect}
      />
    )
    expect(screen.getByPlaceholderText(/Search tables/i)).toBeInTheDocument()
  })

  it('searches tables on input', async () => {
    const mockResults: TableInfoResponse[] = [
      { schema: 'public', table: 'table1' },
      { schema: 'public', table: 'table2' },
    ]

    vi.mocked(lineageApi.searchTables).mockResolvedValueOnce(mockResults)

    render(
      <LineageSearch
        onTableSelect={mockOnTableSelect}
      />
    )

    const input = screen.getByPlaceholderText(/Search tables/i)
    fireEvent.change(input, { target: { value: 'table' } })

    await waitFor(() => {
      expect(lineageApi.searchTables).toHaveBeenCalledWith('table', 20)
    })
  })

  it('displays search results', async () => {
    const mockResults: TableInfoResponse[] = [
      { schema: 'public', table: 'table1' },
    ]

    vi.mocked(lineageApi.searchTables).mockResolvedValueOnce(mockResults)

    render(
      <LineageSearch
        onTableSelect={mockOnTableSelect}
      />
    )

    const input = screen.getByPlaceholderText(/Search tables/i)
    fireEvent.change(input, { target: { value: 'table' } })
    fireEvent.focus(input)

    await waitFor(() => {
      expect(screen.getByText('table1')).toBeInTheDocument()
      expect(screen.getByText('public')).toBeInTheDocument()
    })
  })

  it('calls onTableSelect when table is clicked', async () => {
    const mockResults: TableInfoResponse[] = [
      { schema: 'public', table: 'table1' },
    ]

    vi.mocked(lineageApi.searchTables).mockResolvedValueOnce(mockResults)

    render(
      <LineageSearch
        onTableSelect={mockOnTableSelect}
      />
    )

    const input = screen.getByPlaceholderText(/Search tables/i)
    fireEvent.change(input, { target: { value: 'table' } })
    fireEvent.focus(input)

    await waitFor(() => {
      const tableButton = screen.getByText('table1')
      fireEvent.click(tableButton)
    })

    expect(mockOnTableSelect).toHaveBeenCalledWith({
      schema: 'public',
      table: 'table1',
    })
  })

  it('displays selected table', () => {
    const selectedTable: TableInfoResponse = {
      schema: 'public',
      table: 'selected_table',
    }

    render(
      <LineageSearch
        onTableSelect={mockOnTableSelect}
        selectedTable={selectedTable}
      />
    )

    expect(screen.getByText('selected_table')).toBeInTheDocument()
    expect(screen.getByText('public')).toBeInTheDocument()
  })

  it('shows no results message', async () => {
    vi.mocked(lineageApi.searchTables).mockResolvedValueOnce([])

    render(
      <LineageSearch
        onTableSelect={mockOnTableSelect}
      />
    )

    const input = screen.getByPlaceholderText(/Search tables/i)
    fireEvent.change(input, { target: { value: 'nonexistent' } })
    fireEvent.focus(input)

    await waitFor(() => {
      expect(screen.getByText(/No tables found/i)).toBeInTheDocument()
    })
  })
})

