'use client'

import { useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Database, List, Grid, ChevronLeft, ChevronRight, Table } from 'lucide-react'
import { Button } from '@/components/ui'
import { SearchInput } from '@/components/ui'
import { LoadingSpinner } from '@/components/ui'
import TableFilters from '@/components/tables/TableFilters'
import TableList from '@/components/tables/TableList'
import TableCard from '@/components/tables/TableCard'
import { fetchTables, TableListOptions } from '@/lib/api'
import { debounce } from '@/lib/utils'

type ViewMode = 'list' | 'grid'

export default function TablesPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('list')
  const [selectedTables, setSelectedTables] = useState<Set<string>>(new Set())
  const [filters, setFilters] = useState<TableListOptions>({
    sort_by: 'table_name',
    sort_order: 'asc',
    page: 1,
    page_size: 50
  })
  const [searchQuery, setSearchQuery] = useState('')

  // Debounced search
  const debouncedSetSearch = useCallback(
    debounce((value: string) => {
      setFilters((prev) => ({ ...prev, search: value || undefined, page: 1 }))
    }, 300),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  )

  const handleSearchChange = (value: string) => {
    setSearchQuery(value)
    debouncedSetSearch(value)
  }

  // Fetch tables
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['tables', filters],
    queryFn: () => fetchTables(filters),
    staleTime: 30000,
  })

  const handleSort = (column: string) => {
    setFilters(prev => ({
      ...prev,
      sort_by: column,
      sort_order: prev.sort_by === column && prev.sort_order === 'asc' ? 'desc' : 'asc',
      page: 1
    }))
  }

  const handleSelectTable = (tableName: string, selected: boolean) => {
    setSelectedTables(prev => {
      const next = new Set(prev)
      if (selected) {
        next.add(tableName)
      } else {
        next.delete(tableName)
      }
      return next
    })
  }

  const handleSelectAll = (selected: boolean) => {
    if (selected && data) {
      setSelectedTables(new Set(data.tables.map(t => t.table_name)))
    } else {
      setSelectedTables(new Set())
    }
  }

  const handlePageChange = (newPage: number) => {
    setFilters(prev => ({ ...prev, page: newPage }))
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const totalPages = data ? Math.ceil(data.total / (filters.page_size || 50)) : 0

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/10">
              <Table className="w-6 h-6 text-emerald-400" />
            </div>
            Table Browser
          </h1>
          <p className="mt-2 text-sm text-slate-400">
            Browse and manage all profiled tables
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={viewMode === 'list' ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setViewMode('list')}
          >
            <List className="w-4 h-4 mr-2" />
            List
          </Button>
          <Button
            variant={viewMode === 'grid' ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setViewMode('grid')}
          >
            <Grid className="w-4 h-4 mr-2" />
            Grid
          </Button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="space-y-4">
        <div className="flex gap-4">
          <div className="flex-1">
            <SearchInput
              value={searchQuery}
              onChange={handleSearchChange}
              placeholder="Search tables by name, schema, or warehouse..."
              debounceMs={300}
            />
          </div>
        </div>

        <TableFilters
          filters={filters}
          onChange={setFilters}
        />
      </div>

      {/* Bulk Selection Actions */}
      {selectedTables.size > 0 && (
        <div className="bg-accent-500/10 border border-accent-500/20 rounded-lg p-4 flex items-center justify-between">
          <p className="text-sm font-medium text-accent-300">
            {selectedTables.size} table{selectedTables.size !== 1 ? 's' : ''} selected
          </p>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedTables(new Set())}
            >
              Clear Selection
            </Button>
          </div>
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : error ? (
        <div className="glass-card p-6 text-center border-danger-500/20 bg-danger-500/5">
          <p className="text-danger-400 font-medium">Error loading tables</p>
          <p className="text-slate-400 text-sm mt-1">
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
          <Button
            variant="primary"
            size="sm"
            onClick={() => refetch()}
            className="mt-4"
          >
            Retry
          </Button>
        </div>
      ) : data && data.tables.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <div className="w-16 h-16 rounded-full bg-surface-800 flex items-center justify-center mx-auto mb-4">
            <Database className="w-8 h-8 text-slate-600" />
          </div>
          <p className="text-white font-medium mb-1">No tables found</p>
          <p className="text-slate-400 text-sm">
            Try adjusting your filters or search query
          </p>
        </div>
      ) : data ? (
        <>
          {/* Results Count */}
          <div className="flex items-center justify-between text-sm text-slate-400">
            <p>
              Showing {((filters.page || 1) - 1) * (filters.page_size || 50) + 1} to{' '}
              {Math.min((filters.page || 1) * (filters.page_size || 50), data.total)} of{' '}
              <span className="text-slate-300">{data.total}</span> table{data.total !== 1 ? 's' : ''}
            </p>
          </div>

          {/* Table List or Grid */}
          {viewMode === 'list' ? (
            <TableList
              tables={data.tables}
              selectedTables={selectedTables}
              onSelectTable={handleSelectTable}
              onSelectAll={handleSelectAll}
              sortBy={filters.sort_by}
              sortOrder={filters.sort_order}
              onSort={handleSort}
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {data.tables.map((table) => (
                <TableCard key={table.table_name} table={table} />
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between glass-card p-4">
              <div className="text-sm text-slate-400">
                Page <span className="text-slate-300">{filters.page || 1}</span> of {totalPages}
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange((filters.page || 1) - 1)}
                  disabled={(filters.page || 1) <= 1}
                >
                  <ChevronLeft className="w-4 h-4 mr-1" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange((filters.page || 1) + 1)}
                  disabled={(filters.page || 1) >= totalPages}
                >
                  Next
                  <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </>
      ) : null}
    </div>
  )
}
