'use client'

import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { fetchDriftSummary } from '@/lib/api'
import type { DriftSummary } from '@/types/drift'
import {
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

interface DriftDashboardProps {
  warehouse?: string
  days?: number
}

const COLORS = {
  low: '#10b981', // green
  medium: '#f59e0b', // yellow
  high: '#ef4444', // red
}

export default function DriftDashboard({ warehouse, days = 30 }: DriftDashboardProps) {
  const { data: summary, isLoading, error } = useQuery<DriftSummary>({
    queryKey: ['drift-summary', warehouse, days],
    queryFn: () => fetchDriftSummary({ warehouse, days }),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner />
      </div>
    )
  }

  if (error || !summary) {
    return (
      <div className="text-center py-8 text-gray-500">
        <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-gray-400" />
        <p>Failed to load drift summary</p>
      </div>
    )
  }

  // Calculate trend
  const calculateTrend = (): 'up' | 'down' | 'stable' => {
    if (summary.trending.length < 2) return 'stable'
    const firstHalf = summary.trending.slice(0, Math.floor(summary.trending.length / 2))
    const secondHalf = summary.trending.slice(Math.floor(summary.trending.length / 2))
    const firstAvg = firstHalf.reduce((sum, d) => sum + d.value, 0) / firstHalf.length
    const secondAvg = secondHalf.reduce((sum, d) => sum + d.value, 0) / secondHalf.length
    if (secondAvg > firstAvg * 1.1) return 'up'
    if (secondAvg < firstAvg * 0.9) return 'down'
    return 'stable'
  }

  const trend = calculateTrend()

  // Prepare pie chart data
  const severityData = [
    { name: 'Low', value: summary.by_severity.low || 0, color: COLORS.low },
    { name: 'Medium', value: summary.by_severity.medium || 0, color: COLORS.medium },
    { name: 'High', value: summary.by_severity.high || 0, color: COLORS.high },
  ].filter((d) => d.value > 0)

  // Prepare trending chart data
  const trendingData = summary.trending.map((t) => ({
    date: new Date(t.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    events: t.value,
  }))

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardBody padding="md">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Events</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{summary.total_events}</p>
              </div>
              <div className="p-3 rounded-lg bg-blue-50 text-blue-600">
                <AlertTriangle className="w-6 h-6" />
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody padding="md">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">High Severity</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{summary.by_severity.high || 0}</p>
              </div>
              <div className="p-3 rounded-lg bg-red-50 text-red-600">
                <AlertTriangle className="w-6 h-6" />
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody padding="md">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Trend</p>
                <div className="flex items-center gap-2 mt-2">
                  {trend === 'up' && <TrendingUp className="w-5 h-5 text-red-600" />}
                  {trend === 'down' && <TrendingDown className="w-5 h-5 text-green-600" />}
                  {trend === 'stable' && <Minus className="w-5 h-5 text-gray-600" />}
                  <span className="text-lg font-semibold text-gray-900 capitalize">{trend}</span>
                </div>
              </div>
              <div className="p-3 rounded-lg bg-purple-50 text-purple-600">
                {trend === 'up' && <TrendingUp className="w-6 h-6" />}
                {trend === 'down' && <TrendingDown className="w-6 h-6" />}
                {trend === 'stable' && <Minus className="w-6 h-6" />}
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody padding="md">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Affected Tables</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{summary.top_affected_tables.length}</p>
              </div>
              <div className="p-3 rounded-lg bg-orange-50 text-orange-600">
                <AlertTriangle className="w-6 h-6" />
              </div>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Severity Distribution */}
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-gray-900">Severity Distribution</h3>
          </CardHeader>
          <CardBody>
            {severityData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={severityData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {severityData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-gray-500">
                No severity data available
              </div>
            )}
          </CardBody>
        </Card>

        {/* Trending Chart */}
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-gray-900">Drift Events Over Time</h3>
          </CardHeader>
          <CardBody>
            {trendingData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={trendingData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="events" stroke="#3b82f6" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-gray-500">
                No trending data available
              </div>
            )}
          </CardBody>
        </Card>
      </div>

      {/* Top Affected Tables */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold text-gray-900">Top Affected Tables</h3>
        </CardHeader>
        <CardBody>
          {summary.top_affected_tables.length > 0 ? (
            <div className="space-y-4">
              {summary.top_affected_tables.map((table, index) => (
                <div
                  key={table.table_name}
                  className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50"
                >
                  <div className="flex items-center gap-4">
                    <span className="text-sm font-medium text-gray-500 w-6">#{index + 1}</span>
                    <div>
                      <p className="font-medium text-gray-900">{table.table_name}</p>
                      <p className="text-sm text-gray-500">{table.drift_count} drift event(s)</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {table.severity_breakdown.high > 0 && (
                      <Badge variant="error">{table.severity_breakdown.high} High</Badge>
                    )}
                    {table.severity_breakdown.medium > 0 && (
                      <Badge variant="warning">{table.severity_breakdown.medium} Medium</Badge>
                    )}
                    {table.severity_breakdown.low > 0 && (
                      <Badge variant="success">{table.severity_breakdown.low} Low</Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">No affected tables</div>
          )}
        </CardBody>
      </Card>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold text-gray-900">Recent Activity</h3>
        </CardHeader>
        <CardBody>
          {summary.recent_activity.length > 0 ? (
            <div className="space-y-3">
              {summary.recent_activity.map((alert) => (
                <div
                  key={alert.event_id}
                  className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={
                          alert.severity === 'high'
                            ? 'error'
                            : alert.severity === 'medium'
                            ? 'warning'
                            : 'success'
                        }
                      >
                        {alert.severity}
                      </Badge>
                      <span className="font-medium text-gray-900">{alert.table_name}</span>
                      {alert.column_name && (
                        <span className="text-sm text-gray-500">• {alert.column_name}</span>
                      )}
                    </div>
                    <p className="text-sm text-gray-500 mt-1">
                      {alert.metric_name} • {new Date(alert.timestamp || alert.detected_at || '').toLocaleString()}
                    </p>
                  </div>
                  {alert.change_percent !== undefined && alert.change_percent !== null && (
                    <span
                      className={`text-sm font-medium ${
                        alert.change_percent > 0 ? 'text-red-600' : 'text-green-600'
                      }`}
                    >
                      {alert.change_percent > 0 ? '+' : ''}
                      {alert.change_percent.toFixed(1)}%
                    </span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">No recent activity</div>
          )}
        </CardBody>
      </Card>
    </div>
  )
}

