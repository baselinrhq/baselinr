'use client'

import { useQuery } from '@tanstack/react-query'
import { BarChart3, TrendingUp, Activity } from 'lucide-react'
import { fetchDashboardMetrics } from '@/lib/api'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

const COLORS = ['#06b6d4', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

export default function MetricsPage() {
  const { data: metrics, isLoading } = useQuery({
    queryKey: ['metrics-page'],
    queryFn: () => fetchDashboardMetrics({ days: 90 }),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="w-12 h-12 rounded-full border-2 border-accent-500/20 border-t-accent-500 animate-spin" />
      </div>
    )
  }

  if (!metrics) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="text-lg font-medium text-slate-400">No data available</div>
        </div>
      </div>
    )
  }

  // Transform warehouse breakdown for pie chart
  const warehouseData = Object.entries(metrics.warehouse_breakdown).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value,
  }))

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <div className="p-2 rounded-lg bg-accent-500/10">
            <BarChart3 className="w-7 h-7 text-accent-400" />
          </div>
          Metrics & Analytics
        </h1>
        <p className="text-slate-400 mt-2">Deep dive into profiling metrics and trends</p>
      </div>

      {/* KPI Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {metrics.kpis.map((kpi: { name: string; value: string | number }) => (
          <div key={kpi.name} className="glass-card p-6">
            <p className="text-sm font-medium text-slate-400">{kpi.name}</p>
            <p className="text-3xl font-bold text-white mt-2">
              {typeof kpi.value === 'number' ? kpi.value.toLocaleString() : kpi.value}
            </p>
          </div>
        ))}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Warehouse Distribution */}
        <div className="glass-card p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Warehouse Distribution</h2>
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
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1e293b', 
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      color: '#f1f5f9'
                    }} 
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-slate-500">
                <p>No data available</p>
              </div>
            )}
          </div>
        </div>

        {/* Run Trend Bar Chart */}
        <div className="glass-card p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Profiling Activity</h2>
          <div className="h-64">
            {metrics.run_trend.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={metrics.run_trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="timestamp" stroke="#94a3b8" fontSize={12} />
                  <YAxis stroke="#94a3b8" fontSize={12} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1e293b', 
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      color: '#f1f5f9'
                    }} 
                  />
                  <Bar dataKey="value" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-slate-500">
                <p>No trend data available</p>
              </div>
            )}
          </div>
        </div>

        {/* Drift Trend */}
        <div className="glass-card p-6 lg:col-span-2">
          <h2 className="text-lg font-semibold text-white mb-4">Drift Detection Trend</h2>
          <div className="h-64">
            {metrics.drift_trend.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={metrics.drift_trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="timestamp" stroke="#94a3b8" fontSize={12} />
                  <YAxis stroke="#94a3b8" fontSize={12} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1e293b', 
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      color: '#f1f5f9'
                    }} 
                  />
                  <Bar dataKey="value" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-slate-500">
                <p>No drift data available</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Additional Stats */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Statistics Summary</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-accent-500/10 rounded-lg">
              <Activity className="w-6 h-6 text-accent-400" />
            </div>
            <div>
              <p className="text-sm text-slate-400">Total Profiling Runs</p>
              <p className="text-2xl font-bold text-white">{metrics.total_runs}</p>
              <p className="text-xs text-slate-500 mt-1">Last 90 days</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="p-3 bg-success-500/10 rounded-lg">
              <TrendingUp className="w-6 h-6 text-success-400" />
            </div>
            <div>
              <p className="text-sm text-slate-400">Average Row Count</p>
              <p className="text-2xl font-bold text-white">{metrics.avg_row_count ? Math.round(metrics.avg_row_count).toLocaleString() : '0'}</p>
              <p className="text-xs text-slate-500 mt-1">Across all tables</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="p-3 bg-warning-500/10 rounded-lg">
              <BarChart3 className="w-6 h-6 text-warning-400" />
            </div>
            <div>
              <p className="text-sm text-slate-400">Drift Events</p>
              <p className="text-2xl font-bold text-white">{metrics.total_drift_events}</p>
              <p className="text-xs text-slate-500 mt-1">Detected anomalies</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
