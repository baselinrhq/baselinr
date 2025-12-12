'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Tabs } from '@/components/ui/Tabs'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { listRCAResults } from '@/lib/api/rca'
import RCADashboard from '@/components/rca/RCADashboard'
import RCAList from '@/components/rca/RCAList'
import RCATimeline from '@/components/rca/RCATimeline'
import RCADetails from '@/components/rca/RCADetails'
import RCAFilters from '@/components/rca/RCAFilters'
import CorrelationView from '@/components/rca/CorrelationView'
import type { RCAFilters as RCAFiltersType, RCAListItem, RCAResult } from '@/types/rca'

export default function RCAPage() {
  const [filters, setFilters] = useState<RCAFiltersType>({
    days: 30,
  })
  const [selectedAnomalyId, setSelectedAnomalyId] = useState<string | null>(null)
  const [showDetailsModal, setShowDetailsModal] = useState(false)
  const [activeTab, setActiveTab] = useState('dashboard')

  // Convert filters to API format
  const apiFilters: RCAFiltersType = {
    status: filters.status,
    table: filters.table,
    schema: filters.schema,
    days: filters.days || 30,
    start_date: filters.start_date,
    end_date: filters.end_date,
  }

  const { data: rcaList, isLoading } = useQuery<RCAListItem[]>({
    queryKey: ['rca-list', apiFilters],
    queryFn: () => listRCAResults({ ...apiFilters, limit: 100 }),
  })

  const handleRowClick = (anomalyId: string) => {
    setSelectedAnomalyId(anomalyId)
    setShowDetailsModal(true)
  }

  const handleCloseDetails = () => {
    setShowDetailsModal(false)
    setSelectedAnomalyId(null)
  }

  // Extract unique tables and schemas for filter suggestions
  const tables = Array.from(
    new Set(rcaList?.map((item) => item.table_name).filter(Boolean) || [])
  )
  const schemas = Array.from(
    new Set(rcaList?.map((item) => item.schema_name).filter(Boolean) || [])
  )

  // Get full RCA results for correlation view
  const rcaResultsForCorrelation: RCAResult[] = []
  // Note: In a real implementation, you'd fetch full RCA results for correlation view
  // For now, we'll use an empty array

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <Search className="w-8 h-8 text-blue-500" />
            Root Cause Analysis
          </h1>
          <p className="text-gray-600 mt-1">Analyze anomalies and identify root causes</p>
        </div>
        <Button
          variant="primary"
          onClick={() => {
            // Trigger new analysis - would open a modal or navigate to analysis page
            console.log('Trigger new analysis')
          }}
        >
          <Search className="w-4 h-4 mr-2" />
          Analyze Anomaly
        </Button>
      </div>

      {/* Filters */}
      <RCAFilters
        filters={filters}
        onChange={setFilters}
        tables={tables}
        schemas={schemas}
      />

      {/* Main Content with Tabs */}
      <div className="space-y-6">
        <Tabs
          tabs={[
            { id: 'dashboard', label: 'Dashboard' },
            { id: 'list', label: 'List View' },
            { id: 'timeline', label: 'Timeline' },
            { id: 'correlation', label: 'Correlation' },
          ]}
          activeTab={activeTab}
          onChange={setActiveTab}
        />
        
        <div className="space-y-6">
          {/* Dashboard Tab */}
          {activeTab === 'dashboard' && (
            <RCADashboard
              onAnalyzeNew={() => {
                // Trigger new analysis
                console.log('Analyze new anomaly')
              }}
            />
          )}

          {/* List Tab */}
          {activeTab === 'list' && (
            <>
              {isLoading ? (
                <div className="flex items-center justify-center h-64">
                  <LoadingSpinner />
                </div>
              ) : (
                <RCAList items={rcaList || []} onRowClick={handleRowClick} />
              )}
            </>
          )}

          {/* Timeline Tab */}
          {activeTab === 'timeline' && <RCATimeline />}

          {/* Correlation Tab */}
          {activeTab === 'correlation' && (
            <CorrelationView rcaResults={rcaResultsForCorrelation} />
          )}
        </div>
      </div>

      {/* Details Modal */}
      {showDetailsModal && selectedAnomalyId && (
        <RCADetails
          anomalyId={selectedAnomalyId}
          isOpen={showDetailsModal}
          onClose={handleCloseDetails}
        />
      )}
    </div>
  )
}

