'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Filter, Download } from 'lucide-react'
import { fetchRuns, exportRuns } from '@/lib/api'
import RunsTable from '@/components/RunsTable'
import FilterPanel from '@/components/FilterPanel'

export default function RunsPage() {
  const [filters, setFilters] = useState({
    warehouse: '',
    schema: '',
    table: '',
    status: '',
    days: 30,
  })
  const [showFilters, setShowFilters] = useState(false)

  const { data: runs, isLoading } = useQuery({
    queryKey: ['runs', filters],
    queryFn: () => fetchRuns(filters),
  })

  const handleExport = async () => {
    try {
      const data = await exportRuns(filters)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `baselinr-runs-${Date.now()}.json`
      a.click()
    } catch (error) {
      console.error('Export failed:', error)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Profiling Runs</h1>
          <p className="text-gray-600 mt-1">View and filter profiling run history</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <Filter className="w-4 h-4" />
            Filters
          </button>
          <button
            onClick={handleExport}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <FilterPanel filters={filters} onChange={setFilters} />
      )}

      {/* Runs Table */}
      <div className="bg-white rounded-lg shadow">
        {isLoading ? (
          <div className="flex items-center justify-center h-96">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : (
          <RunsTable runs={runs || []} showPagination />
        )}
      </div>
    </div>
  )
}

