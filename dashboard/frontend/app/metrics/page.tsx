'use client'

import { useQuery } from '@tanstack/react-query'
import { BarChart3, TrendingUp, Activity } from 'lucide-react'
import { fetchDashboardMetrics } from '@/lib/api'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

const COLORS = ['#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

export default function MetricsPage() {
  const { data: metrics, isLoading } = useQuery({
    queryKey: ['metrics-page'],
    queryFn: () => fetchDashboardMetrics({ days: 90 }),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (!metrics) {
    return <div>No data available</div>
  }

  // Transform warehouse breakdown for pie chart
  const warehouseData = Object.entries(metrics.warehouse_breakdown).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value,
  }))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
          <BarChart3 className="w-8 h-8 text-primary-600" />
          Metrics & Analytics
        </h1>
        <p className="text-gray-600 mt-1">Deep dive into profiling metrics and trends</p>
      </div>

      {/* KPI Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {metrics.kpis.map((kpi: any) => (
          <div key={kpi.name} className="bg-white rounded-lg shadow p-6">
            <p className="text-sm font-medium text-gray-600">{kpi.name}</p>
            <p className="text-3xl font-bold text-gray-900 mt-2">
              {typeof kpi.value === 'number' ? kpi.value.toLocaleString() : kpi.value}
            </p>
          </div>
        ))}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Warehouse Distribution */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Warehouse Distribution</h2>
          <div className="h-64">
            {warehouseData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={warehouseData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {warehouseData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                <p>No data available</p>
              </div>
            )}
          </div>
        </div>

        {/* Run Trend Bar Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Profiling Activity</h2>
          <div className="h-64">
            {metrics.run_trend.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={metrics.run_trend}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value" fill="#0ea5e9" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                <p>No trend data available</p>
              </div>
            )}
          </div>
        </div>

        {/* Drift Trend */}
        <div className="bg-white rounded-lg shadow p-6 lg:col-span-2">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Drift Detection Trend</h2>
          <div className="h-64">
            {metrics.drift_trend.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={metrics.drift_trend}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value" fill="#f59e0b" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                <p>No drift data available</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Additional Stats */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Statistics Summary</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-blue-50 rounded-lg">
              <Activity className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Total Profiling Runs</p>
              <p className="text-2xl font-bold text-gray-900">{metrics.total_runs}</p>
              <p className="text-xs text-gray-500 mt-1">Last 90 days</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="p-3 bg-green-50 rounded-lg">
              <TrendingUp className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Average Row Count</p>
              <p className="text-2xl font-bold text-gray-900">{Math.round(metrics.avg_row_count).toLocaleString()}</p>
              <p className="text-xs text-gray-500 mt-1">Across all tables</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="p-3 bg-orange-50 rounded-lg">
              <BarChart3 className="w-6 h-6 text-orange-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Drift Events</p>
              <p className="text-2xl font-bold text-gray-900">{metrics.total_drift_events}</p>
              <p className="text-xs text-gray-500 mt-1">Detected anomalies</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

