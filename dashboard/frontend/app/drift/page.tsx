'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Filter, Download, AlertTriangle } from 'lucide-react'
import { fetchDriftAlerts, exportDrift } from '@/lib/api'
import DriftAlertsTable from '@/components/DriftAlertsTable'
import FilterPanel from '@/components/FilterPanel'

export default function DriftPage() {
  const [filters, setFilters] = useState({
    warehouse: '',
    table: '',
    severity: '',
    days: 30,
  })
  const [showFilters, setShowFilters] = useState(false)

  const { data: alerts, isLoading } = useQuery({
    queryKey: ['drift-alerts', filters],
    queryFn: () => fetchDriftAlerts(filters),
  })

  const handleExport = async () => {
    try {
      const data = await exportDrift(filters)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `profilemesh-drift-${Date.now()}.json`
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
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <AlertTriangle className="w-8 h-8 text-orange-500" />
            Drift Detection
          </h1>
          <p className="text-gray-600 mt-1">Monitor data drift events and anomalies</p>
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
        <FilterPanel filters={filters} onChange={setFilters} type="drift" />
      )}

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4">
        {['low', 'medium', 'high'].map((severity) => {
          const count = alerts?.filter((a) => a.severity === severity).length || 0
          const colors = {
            low: 'bg-green-100 text-green-800 border-green-200',
            medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
            high: 'bg-red-100 text-red-800 border-red-200',
          }
          return (
            <div key={severity} className={`p-4 rounded-lg border-2 ${colors[severity as keyof typeof colors]}`}>
              <p className="text-sm font-medium capitalize">{severity} Severity</p>
              <p className="text-2xl font-bold mt-1">{count}</p>
            </div>
          )
        })}
      </div>

      {/* Alerts Table */}
      <div className="bg-white rounded-lg shadow">
        {isLoading ? (
          <div className="flex items-center justify-center h-96">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : (
          <DriftAlertsTable alerts={alerts || []} showDetails />
        )}
      </div>
    </div>
  )
}

