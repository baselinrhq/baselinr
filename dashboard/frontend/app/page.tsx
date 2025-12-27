'use client'

import { useQuery } from '@tanstack/react-query'
import { Activity, Database, AlertTriangle, BarChart3, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react'
import { fetchDashboardMetrics } from '@/lib/api'
import RunsTable from '@/components/RunsTable'
import DriftAlertsTable from '@/components/DriftAlertsTable'
import EnhancedKPIs from '@/components/dashboard/EnhancedKPIs'
import QuickActions from '@/components/dashboard/QuickActions'
import TrendCharts from '@/components/dashboard/TrendCharts'

interface KPICardProps {
  title: string
  value: string | number
  icon: React.ReactNode
  trend?: 'up' | 'down' | 'stable'
  trendValue?: string
  color?: 'cyan' | 'emerald' | 'amber' | 'rose'
}

function KPICard({ title, value, icon, trend = 'stable', trendValue, color = 'cyan' }: KPICardProps) {
  const colorClasses = {
    cyan: 'from-accent-500/20 to-accent-600/5 border-accent-500/20',
    emerald: 'from-success-500/20 to-success-600/5 border-success-500/20',
    amber: 'from-warning-500/20 to-warning-600/5 border-warning-500/20',
    rose: 'from-danger-500/20 to-danger-600/5 border-danger-500/20',
  }

  const iconColorClasses = {
    cyan: 'text-accent-400 bg-accent-500/10',
    emerald: 'text-success-400 bg-success-500/10',
    amber: 'text-warning-400 bg-warning-500/10',
    rose: 'text-danger-400 bg-danger-500/10',
  }

  const TrendIcon = trend === 'up' ? ArrowUpRight : trend === 'down' ? ArrowDownRight : Minus

  return (
    <div className={`relative overflow-hidden rounded-xl border bg-gradient-to-br ${colorClasses[color]} p-5`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-slate-400">{title}</p>
          <p className="mt-2 text-3xl font-bold text-white">{value}</p>
          {trendValue && (
            <div className="mt-2 flex items-center gap-1 text-sm">
              <TrendIcon className={`w-4 h-4 ${
                trend === 'up' ? 'text-success-400' : 
                trend === 'down' ? 'text-danger-400' : 
                'text-slate-500'
              }`} />
              <span className={
                trend === 'up' ? 'text-success-400' : 
                trend === 'down' ? 'text-danger-400' : 
                'text-slate-500'
              }>
                {trendValue}
              </span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-lg ${iconColorClasses[color]}`}>
          {icon}
        </div>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const { data: metrics, isLoading } = useQuery({
    queryKey: ['dashboard-metrics'],
    queryFn: () => fetchDashboardMetrics(),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="w-12 h-12 rounded-full border-2 border-accent-500/20 border-t-accent-500 animate-spin" />
          </div>
          <p className="text-sm text-slate-500">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  if (!metrics) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="text-lg font-medium text-slate-400">No data available</div>
          <p className="text-sm text-slate-500 mt-1">Check your connection settings</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 lg:p-8 space-y-8">
      {/* Header */}
      <div className="space-y-1">
        <h1 className="text-3xl font-bold text-white">Dashboard</h1>
        <p className="text-slate-400">
          Monitor data quality, drift detection, and warehouse health
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Total Runs"
          value={metrics.total_runs}
          icon={<Activity className="w-6 h-6" />}
          trend="up"
          trendValue="+12% from last week"
          color="cyan"
        />
        <KPICard
          title="Tables Profiled"
          value={metrics.total_tables}
          icon={<Database className="w-6 h-6" />}
          trend="stable"
          color="emerald"
        />
        <KPICard
          title="Drift Events"
          value={metrics.total_drift_events}
          icon={<AlertTriangle className="w-6 h-6" />}
          trend="down"
          trendValue="-8% from last week"
          color="amber"
        />
        <KPICard
          title="Avg Rows"
          value={metrics.avg_row_count?.toLocaleString() || '0'}
          icon={<BarChart3 className="w-6 h-6" />}
          trend="up"
          color="cyan"
        />
      </div>

      {/* Enhanced KPI Cards */}
      {(metrics.validation_pass_rate !== undefined || 
        metrics.active_alerts !== undefined || 
        metrics.data_freshness_hours !== undefined) && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <EnhancedKPIs metrics={metrics} />
        </div>
      )}

      {/* Quick Actions */}
      <QuickActions />

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trend Charts */}
        <div className="lg:col-span-2">
          <TrendCharts
            runTrend={metrics.run_trend}
            driftTrend={metrics.drift_trend}
            validationTrend={metrics.validation_trend}
          />
        </div>

        {/* Warehouse Breakdown */}
        <div className="glass-card p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Warehouse Breakdown</h2>
          <div className="space-y-3">
            {Object.entries(metrics.warehouse_breakdown).map(([warehouse, count]) => (
              <div key={warehouse} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-2.5 h-2.5 rounded-full bg-accent-500" />
                  <span className="text-sm font-medium text-slate-300 capitalize">{warehouse}</span>
                </div>
                <span className="text-sm font-bold text-white">{count} runs</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Runs */}
      <div className="glass-card overflow-hidden">
        <div className="px-6 py-4 border-b border-surface-700/50">
          <h2 className="text-lg font-semibold text-white">Recent Runs</h2>
        </div>
        <RunsTable runs={metrics.recent_runs} />
      </div>

      {/* Recent Drift Alerts */}
      <div className="glass-card overflow-hidden">
        <div className="px-6 py-4 border-b border-surface-700/50">
          <h2 className="text-lg font-semibold text-white">Recent Drift Alerts</h2>
        </div>
        <DriftAlertsTable alerts={metrics.recent_drift} />
      </div>
    </div>
  )
}
