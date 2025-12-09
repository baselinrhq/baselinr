'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, TrendingUp, BarChart3 } from 'lucide-react'
import { LoadingSpinner } from '@/components/ui'
import { fetchTableDriftHistory } from '@/lib/api'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import DriftAlertsTable from '@/components/DriftAlertsTable'

interface TableDriftTabProps {
  tableName: string
  schema?: string
  warehouse?: string
}

const COLORS = ['#f97316', '#fb923c', '#fdba74'] // Orange shades for severity

export default function TableDriftTab({
  tableName,
  schema,
  warehouse
}: TableDriftTabProps) {
  const [severityFilter, setSeverityFilter] = useState<string | undefined>()
  const { data: history, isLoading, error } = useQuery({
    queryKey: ['table-drift-history', tableName, schema, warehouse],
    queryFn: () => fetchTableDriftHistory(tableName, { schema, warehouse, limit: 100 }),
    staleTime: 30000
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error || !history) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <p className="text-red-800 font-medium">Error loading drift history</p>
        <p className="text-red-600 text-sm mt-1">
          {error instanceof Error ? error.message : 'Unknown error'}
        </p>
      </div>
    )
  }

  const filteredEvents = severityFilter
    ? history.drift_events.filter(e => e.severity === severityFilter)
    : history.drift_events

  // Prepare trend data
  const trendData = history.drift_events.reduce((acc, event) => {
    const timestamp = event.detected_at || event.timestamp
    if (!timestamp) return acc
    const date = new Date(timestamp).toISOString().split('T')[0]
    if (!acc[date]) {
      acc[date] = 0
    }
    acc[date]++
    return acc
  }, {} as Record<string, number>)

  const trendChartData = Object.entries(trendData)
    .map(([date, count]) => ({ date, count }))
    .sort((a, b) => a.date.localeCompare(b.date))

  // Severity distribution
  const severityData = Object.entries(history.summary.by_severity || {}).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value: value as number
  }))

  // Column breakdown
  const columnData = Object.entries(history.summary.by_column || {})
    .map(([name, value]) => ({
      name,
      value: value as number
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 10)

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm font-medium text-gray-600">Total Events</p>
          <p className="text-2xl font-bold text-gray-900 mt-2">
            {history.summary.total_events || history.drift_events.length}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm font-medium text-gray-600">Recent (7 days)</p>
          <p className="text-2xl font-bold text-gray-900 mt-2">
            {history.summary.recent_count || 0}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm font-medium text-gray-600">High Severity</p>
          <p className="text-2xl font-bold text-red-600 mt-2">
            {history.summary.by_severity?.high || 0}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm font-medium text-gray-600">Affected Columns</p>
          <p className="text-2xl font-bold text-gray-900 mt-2">
            {Object.keys(history.summary.by_column || {}).length}
          </p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Drift Trend */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            Drift Trend
          </h2>
          <div className="h-64">
            {trendChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tickFormatter={(value) => new Date(value).toLocaleDateString()} />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="count" stroke="#f97316" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                <p>No trend data available</p>
              </div>
            )}
          </div>
        </div>

        {/* Severity Distribution */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            Severity Distribution
          </h2>
          <div className="h-64">
            {severityData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={severityData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {severityData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                <p>No severity data available</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Column Breakdown */}
      {columnData.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Column-Level Drift Breakdown</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={columnData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" width={150} />
                <Tooltip />
                <Bar dataKey="value" fill="#f97316" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Filter */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-gray-700">Filter by Severity:</label>
          <select
            value={severityFilter || ''}
            onChange={(e) => setSeverityFilter(e.target.value || undefined)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All Severities</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>
      </div>

      {/* Drift Events Table */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            Drift Events ({filteredEvents.length})
          </h2>
        </div>
        <div className="p-6">
          {filteredEvents.length > 0 ? (
            <DriftAlertsTable
              alerts={filteredEvents.map(event => {
                const eventWithId = event as { event_id?: string; alert_id?: string; change_percent?: number | null; change_percentage?: number | null }
                return {
                  event_id: event.event_id || eventWithId.alert_id || '',
                  run_id: event.run_id,
                  table_name: event.table_name,
                  column_name: event.column_name,
                  metric_name: event.metric_name,
                  baseline_value: event.baseline_value,
                  current_value: event.current_value,
                  change_percent: event.change_percent || eventWithId.change_percentage || null,
                  severity: event.severity,
                  timestamp: event.detected_at || event.timestamp || '',
                  warehouse_type: event.warehouse_type
                }
              })}
            />
          ) : (
            <div className="text-center py-8 text-gray-500">
              <p>No drift events found{severityFilter ? ` with ${severityFilter} severity` : ''}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

