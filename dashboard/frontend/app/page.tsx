'use client'

import { useQuery } from '@tanstack/react-query'
import { Activity, Database, AlertTriangle, BarChart3, TrendingUp } from 'lucide-react'
import { fetchDashboardMetrics } from '@/lib/api'
import KPICard from '@/components/KPICard'
import RunsTable from '@/components/RunsTable'
import DriftAlertsTable from '@/components/DriftAlertsTable'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function DashboardPage() {
  const { data: metrics, isLoading } = useQuery({
    queryKey: ['dashboard-metrics'],
    queryFn: () => fetchDashboardMetrics(),
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">ProfileMesh Dashboard</h1>
        <p className="text-gray-600 mt-1">Monitor data profiling, drift detection, and warehouse health</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard
          title="Total Runs"
          value={metrics.total_runs}
          icon={<Activity className="w-6 h-6" />}
          trend="up"
          color="blue"
        />
        <KPICard
          title="Tables Profiled"
          value={metrics.total_tables}
          icon={<Database className="w-6 h-6" />}
          trend="stable"
          color="green"
        />
        <KPICard
          title="Drift Events"
          value={metrics.total_drift_events}
          icon={<AlertTriangle className="w-6 h-6" />}
          trend="down"
          color="orange"
        />
        <KPICard
          title="Avg Rows"
          value={metrics.avg_row_count.toLocaleString()}
          icon={<BarChart3 className="w-6 h-6" />}
          trend="up"
          color="purple"
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Run Trend */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Profiling Runs Trend</h2>
          <div className="h-64">
            {metrics.run_trend.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={metrics.run_trend}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" />
                  <YAxis />
                  <Tooltip />
                  <Area type="monotone" dataKey="value" stroke="#0ea5e9" fill="#0ea5e9" fillOpacity={0.3} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                <p>No trend data available</p>
              </div>
            )}
          </div>
        </div>

        {/* Warehouse Breakdown */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Warehouse Breakdown</h2>
          <div className="space-y-3">
            {Object.entries(metrics.warehouse_breakdown).map(([warehouse, count]) => (
              <div key={warehouse} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-primary-500"></div>
                  <span className="text-sm font-medium text-gray-700 capitalize">{warehouse}</span>
                </div>
                <span className="text-sm font-bold text-gray-900">{count} runs</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Runs */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Recent Runs</h2>
        </div>
        <RunsTable runs={metrics.recent_runs} />
      </div>

      {/* Recent Drift Alerts */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Recent Drift Alerts</h2>
        </div>
        <DriftAlertsTable alerts={metrics.recent_drift} />
      </div>
    </div>
  )
}

