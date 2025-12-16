'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Plus, Loader2, AlertCircle, Database } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { SearchInput } from '@/components/ui/SearchInput'
import { Card } from '@/components/ui/Card'
import { DatasetCard } from './DatasetCard'
import { listDatasets } from '@/lib/api/datasets'

export interface DatasetListProps {
  onCreateNew?: () => void
}

export function DatasetList({ onCreateNew }: DatasetListProps) {
  const [searchQuery, setSearchQuery] = useState('')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['datasets'],
    queryFn: listDatasets,
  })

  // Filter datasets based on search query
  const filteredDatasets = data?.datasets.filter((dataset) => {
    if (!searchQuery) return true
    
    const query = searchQuery.toLowerCase()
    const identifier = [
      dataset.database,
      dataset.schema,
      dataset.table,
    ].filter(Boolean).join('.').toLowerCase()
    
    return (
      identifier.includes(query) ||
      dataset.source_file?.toLowerCase().includes(query) ||
      false
    )
  }) || []

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
        <span className="ml-3 text-sm text-slate-400">Loading datasets...</span>
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <div className="p-6 text-center">
          <AlertCircle className="w-12 h-12 text-rose-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">
            Failed to Load Datasets
          </h3>
          <p className="text-sm text-slate-400 mb-4">
            {error instanceof Error ? error.message : 'Unknown error occurred'}
          </p>
          <Button onClick={() => refetch()} variant="outline">
            Retry
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header with search and create */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex-1 max-w-md">
          <SearchInput
            placeholder="Search datasets..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <Button
          onClick={onCreateNew}
          icon={<Plus className="w-4 h-4" />}
        >
          New Dataset
        </Button>
      </div>

      {/* Results count */}
      {data && (
        <div className="text-sm text-slate-400">
          Showing {filteredDatasets.length} of {data.total} datasets
        </div>
      )}

      {/* Dataset grid */}
      {filteredDatasets.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredDatasets.map((dataset) => (
            <DatasetCard key={dataset.dataset_id} dataset={dataset} />
          ))}
        </div>
      ) : (
        <Card>
          <div className="p-12 text-center">
            <Database className="w-16 h-16 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">
              {searchQuery ? 'No datasets found' : 'No datasets configured'}
            </h3>
            <p className="text-sm text-slate-400 mb-6">
              {searchQuery
                ? 'Try adjusting your search query'
                : 'Get started by creating your first dataset configuration'}
            </p>
            {!searchQuery && onCreateNew && (
              <Button onClick={onCreateNew} icon={<Plus className="w-4 h-4" />}>
                Create Dataset
              </Button>
            )}
          </div>
        </Card>
      )}
    </div>
  )
}

