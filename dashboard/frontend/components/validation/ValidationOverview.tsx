'use client'

import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle, XCircle, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { fetchValidationSummary } from '@/lib/api'
import type { ValidationSummary } from '@/types/validation'
import {
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

interface ValidationOverviewProps {
  warehouse?: string
  days?: number
}

const SEVERITY_COLORS = {
  low: '#10b981', // green
  medium: '#f59e0b', // yellow
  high: '#ef4444', // red
}

const RULE_TYPE_COLORS = [
  '#3b82f6', // blue
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#f59e0b', // yellow
  '#10b981', // green
  '#ef4444', // red
]

export default function ValidationOverview({ warehouse, days = 30 }: ValidationOverviewProps) {
  const { data: summary, isLoading, error } = useQuery<ValidationSummary>({
    queryKey: ['validation-summary', warehouse, days],
    queryFn: () => fetchValidationSummary({ warehouse, days }),
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
        <p>Failed to load validation summary</p>
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
    if (secondAvg > firstAvg * 1.05) return 'up'
    if (secondAvg < firstAvg * 0.95) return 'down'
    return 'stable'
  }

  const trend = calculateTrend()
  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus
  const trendColor = trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-600' : 'text-gray-600'

  // Prepare pie chart data for severity
  const severityData = [
    { name: 'Low', value: summary.by_severity.low || 0, color: SEVERITY_COLORS.low },
    { name: 'Medium', value: summary.by_severity.medium || 0, color: SEVERITY_COLORS.medium },
    { name: 'High', value: summary.by_severity.high || 0, color: SEVERITY_COLORS.high },
  ].filter((d) => d.value > 0)

  // Prepare bar chart data for rule types
  const ruleTypeData = Object.entries(summary.by_rule_type)
    .map(([name, value], index) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1).replace('_', ' '),
      value,
      color: RULE_TYPE_COLORS[index % RULE_TYPE_COLORS.length],
    }))
    .sort((a, b) => b.value - a.value)

  // Prepare trending chart data
  const trendingData = summary.trending.map((t) => ({
    date: new Date(t.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    passRate: Number(t.value.toFixed(2)),
  }))

  // Top failing tables
  const topFailingTables = Object.entries(summary.by_table)
    .map(([table, count]) => ({ table, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5)

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardBody padding="md">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Validations</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{summary.total_validations}</p>
              </div>
              <div className="p-3 rounded-lg bg-blue-50 text-blue-600">
                <CheckCircle className="w-6 h-6" />
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody padding="md">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Pass Rate</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{summary.pass_rate.toFixed(1)}%</p>
                <div className="flex items-center gap-1 mt-2">
                  <TrendIcon className={`w-4 h-4 ${trendColor}`} />
                  <span className={`text-xs ${trendColor}`}>
                    {trend === 'up' ? 'Improving' : trend === 'down' ? 'Declining' : 'Stable'}
                  </span>
                </div>
              </div>
              <div className="p-3 rounded-lg bg-green-50 text-green-600">
                <TrendingUp className="w-6 h-6" />
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody padding="md">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Failed Validations</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{summary.failed_count}</p>
              </div>
              <div className="p-3 rounded-lg bg-red-50 text-red-600">
                <XCircle className="w-6 h-6" />
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody padding="md">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">High Severity Failures</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{summary.by_severity.high || 0}</p>
              </div>
              <div className="p-3 rounded-lg bg-red-50 text-red-600">
                <AlertTriangle className="w-6 h-6" />
              </div>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pass Rate Trend */}
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-gray-900">Pass Rate Trend</h3>
          </CardHeader>
          <CardBody>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={trendingData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis domain={[0, 100]} />
                <Tooltip formatter={(value: number) => `${value.toFixed(1)}%`} />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="passRate"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  name="Pass Rate (%)"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardBody>
        </Card>

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
      </div>

      {/* Rule Type Breakdown and Top Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Rule Type Breakdown */}
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-gray-900">Rule Type Breakdown</h3>
          </CardHeader>
          <CardBody>
            {ruleTypeData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={ruleTypeData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value" fill="#3b82f6" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-gray-500">
                No rule type data available
              </div>
            )}
          </CardBody>
        </Card>

        {/* Top Failing Tables */}
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-gray-900">Top Failing Tables</h3>
          </CardHeader>
          <CardBody>
            {topFailingTables.length > 0 ? (
              <div className="space-y-3">
                {topFailingTables.map(({ table, count }, index) => (
                  <div
                    key={table}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-gray-500">#{index + 1}</span>
                      <span className="font-medium text-gray-900">{table}</span>
                    </div>
                    <Badge variant="error">{count} failures</Badge>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-gray-500">
                No failing tables
              </div>
            )}
          </CardBody>
        </Card>
      </div>

      {/* Recent Validation Runs */}
      {summary.recent_runs.length > 0 && (
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-gray-900">Recent Validation Runs</h3>
          </CardHeader>
          <CardBody>
            <div className="space-y-3">
              {summary.recent_runs.map((run) => {
                const passRate = run.total > 0 ? (run.passed / run.total) * 100 : 0
                return (
                  <div
                    key={run.run_id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center gap-4">
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {new Date(run.validated_at).toLocaleString()}
                        </p>
                        <p className="text-xs text-gray-500">Run ID: {run.run_id.substring(0, 8)}...</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p className="text-sm font-medium text-gray-900">
                          {run.passed}/{run.total} passed
                        </p>
                        <p className="text-xs text-gray-500">{passRate.toFixed(1)}% pass rate</p>
                      </div>
                      <Badge variant={run.failed > 0 ? 'error' : 'success'}>
                        {run.failed > 0 ? `${run.failed} failed` : 'All passed'}
                      </Badge>
                    </div>
                  </div>
                )
              })}
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  )
}

