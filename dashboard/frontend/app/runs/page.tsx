'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Filter, Download, GitCompare } from 'lucide-react'
import { fetchRuns, fetchRunComparison, Run, RunComparison as RunComparisonType } from '@/lib/api'
import RunsTable from '@/components/runs/RunsTable'
import RunFilters, { RunFilters as RunFiltersType } from '@/components/runs/RunFilters'
import RunComparison from '@/components/runs/RunComparison'
import RunDetailsModal from '@/components/runs/RunDetailsModal'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'

export default function RunsPage() {
  const [filters, setFilters] = useState<RunFiltersType>({
    warehouse: '',
    schema: '',
    table: '',
    status: '',
    start_date: '',
    end_date: '',
    min_duration: undefined,
    max_duration: undefined,
    sort_by: 'profiled_at',
    sort_order: 'desc',
  })
  const [showFilters, setShowFilters] = useState(false)
  const [selectedRuns, setSelectedRuns] = useState<string[]>([])
  const [comparisonData, setComparisonData] = useState<RunComparisonType | null>(null)
  const [selectedRunForDetails, setSelectedRunForDetails] = useState<Run | null>(null)
  const [isLoadingComparison, setIsLoadingComparison] = useState(false)

  const { data: runs, isLoading } = useQuery({
    queryKey: ['runs', filters],
    queryFn: () => fetchRuns(filters),
  })

  const handleSelectRun = (runId: string, selected: boolean) => {
    if (selected) {
      setSelectedRuns([...selectedRuns, runId])
    } else {
      setSelectedRuns(selectedRuns.filter((id) => id !== runId))
    }
  }

  const handleSelectAll = (selected: boolean) => {
    if (selected) {
      setSelectedRuns(runs?.map((r) => r.run_id) || [])
    } else {
      setSelectedRuns([])
    }
  }

  const handleCompare = async () => {
    if (selectedRuns.length < 2) return

    setIsLoadingComparison(true)
    try {
      const comparison = await fetchRunComparison(selectedRuns)
      setComparisonData(comparison)
    } catch (error) {
      console.error('Failed to compare runs:', error)
      alert('Failed to compare runs. Please try again.')
    } finally {
      setIsLoadingComparison(false)
    }
  }

  const handleExport = async () => {
    try {
      const data = runs || []
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
          <Button
            variant="secondary"
            onClick={() => setShowFilters(!showFilters)}
          >
            <Filter className="w-4 h-4 mr-2" />
            Filters
          </Button>
          {selectedRuns.length >= 2 && (
            <Button
              variant="primary"
              onClick={handleCompare}
              disabled={isLoadingComparison}
            >
              {isLoadingComparison ? (
                <>
                  <LoadingSpinner className="w-4 h-4 mr-2" />
                  Loading...
                </>
              ) : (
                <>
                  <GitCompare className="w-4 h-4 mr-2" />
                  Compare ({selectedRuns.length})
                </>
              )}
            </Button>
          )}
          <Button
            variant="primary"
            onClick={handleExport}
          >
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Selected Runs Bar */}
      {selectedRuns.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center justify-between">
          <div className="text-sm text-blue-900">
            <span className="font-medium">{selectedRuns.length}</span> run{selectedRuns.length !== 1 ? 's' : ''} selected
            {selectedRuns.length >= 2 && ' - Click "Compare" to view side-by-side comparison'}
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setSelectedRuns([])}
          >
            Clear Selection
          </Button>
        </div>
      )}

      {/* Filters */}
      {showFilters && (
        <RunFilters filters={filters} onChange={setFilters} />
      )}

      {/* Runs Table */}
      <div className="bg-white rounded-lg shadow">
        {isLoading ? (
          <div className="flex items-center justify-center h-96">
            <LoadingSpinner />
          </div>
        ) : (
          <RunsTable
            runs={runs || []}
            showPagination
            selectedRuns={selectedRuns}
            onSelectRun={handleSelectRun}
            onSelectAll={handleSelectAll}
            onRunClick={setSelectedRunForDetails}
            sortable
          />
        )}
      </div>

      {/* Comparison Modal */}
      {comparisonData && (
        <RunComparison
          comparison={comparisonData}
          onClose={() => setComparisonData(null)}
        />
      )}

      {/* Details Modal */}
      {selectedRunForDetails && (
        <RunDetailsModal
          run={selectedRunForDetails}
          isOpen={!!selectedRunForDetails}
          onClose={() => setSelectedRunForDetails(null)}
        />
      )}
    </div>
  )
}

