'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download, AlertTriangle } from 'lucide-react'
import { fetchDriftAlerts, exportDrift } from '@/lib/api'
import { Button } from '@/components/ui/Button'
import { Tabs } from '@/components/ui/Tabs'
import DriftAlertsTable from '@/components/DriftAlertsTable'
import DriftFilters from '@/components/drift/DriftFilters'
import DriftDashboard from '@/components/drift/DriftDashboard'
import DriftAnalysis from '@/components/drift/DriftAnalysis'
import DriftDetails from '@/components/drift/DriftDetails'
import type { DriftFilters as DriftFiltersType, DriftAlert } from '@/types/drift'

export default function DriftPage() {
  const [filters, setFilters] = useState<DriftFiltersType>({
    days: 30,
  })
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  const [showDetailsModal, setShowDetailsModal] = useState(false)

  // Convert filters to API format
  const apiFilters = {
    warehouse: filters.warehouse,
    table: filters.table,
    severity: Array.isArray(filters.severity) ? filters.severity[0] : filters.severity,
    days: filters.days || 30,
    start_date: filters.start_date,
    end_date: filters.end_date,
  }

  const { data: alerts, isLoading } = useQuery<DriftAlert[]>({
    queryKey: ['drift-alerts', apiFilters],
    queryFn: () => fetchDriftAlerts(apiFilters),
  })

  const handleExport = async () => {
    try {
      const data = await exportDrift('json', {
        warehouse: filters.warehouse,
        days: filters.days || 30,
      })
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `baselinr-drift-${Date.now()}.json`
      a.click()
    } catch (error) {
      console.error('Export failed:', error)
    }
  }

  const handleRowClick = (eventId: string) => {
    setSelectedEventId(eventId)
    setShowDetailsModal(true)
  }

  // Extract unique warehouses and tables for filter suggestions
  const warehouses = Array.from(new Set(alerts?.map((a) => a.warehouse_type || a.warehouse).filter(Boolean) || []))
  const tables = Array.from(new Set(alerts?.map((a) => a.table_name).filter(Boolean) || []))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <AlertTriangle className="w-8 h-8 text-orange-500" />
            Drift Detection
          </h1>
          <p className="text-gray-600 mt-1">Monitor data drift events and anomalies</p>
        </div>
        <Button onClick={handleExport} variant="primary">
          <Download className="w-4 h-4 mr-2" />
          Export
        </Button>
      </div>

      {/* Filters */}
      <DriftFilters
        filters={filters}
        onChange={setFilters}
        warehouses={warehouses}
        tables={tables}
      />

      {/* Main Content with Tabs */}
      <Tabs
        tabs={[
          { id: 'dashboard', label: 'Dashboard' },
          { id: 'table', label: 'Table View' },
          { id: 'analysis', label: 'Analysis' },
        ]}
        defaultTab="dashboard"
      >
        {(activeTab) => (
          <div className="space-y-6">
            {/* Dashboard Tab */}
            {activeTab === 'dashboard' && (
              <DriftDashboard
                warehouse={filters.warehouse}
                days={filters.days || 30}
              />
            )}

            {/* Table View Tab */}
            {activeTab === 'table' && (
              <div className="bg-white rounded-lg shadow">
                {isLoading ? (
                  <div className="flex items-center justify-center h-96">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
                  </div>
                ) : (
                  <DriftAlertsTable
                    alerts={alerts || []}
                    showDetails
                    onRowClick={handleRowClick}
                  />
                )}
              </div>
            )}

            {/* Analysis Tab */}
            {activeTab === 'analysis' && (
              <DriftAnalysis alerts={alerts || []} />
            )}
          </div>
        )}
      </Tabs>

      {/* Drift Details Modal */}
      {selectedEventId && (
        <DriftDetails
          eventId={selectedEventId}
          isOpen={showDetailsModal}
          onClose={() => {
            setShowDetailsModal(false)
            setSelectedEventId(null)
          }}
        />
      )}
    </div>
  )
}

