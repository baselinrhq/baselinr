'use client'

import { useQuery } from '@tanstack/react-query'
import { Search, TrendingUp, AlertCircle, CheckCircle } from 'lucide-react'
import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Button } from '@/components/ui/Button'
import { getRCAStatistics } from '@/lib/api/rca'
import type { RCAStatistics } from '@/types/rca'
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts'

interface RCADashboardProps {
  onAnalyzeNew?: () => void
}

const COLORS = {
  analyzed: '#10b981', // green
  pending: '#f59e0b', // yellow
  dismissed: '#6b7280', // gray
}

export default function RCADashboard({ onAnalyzeNew }: RCADashboardProps) {
  const { data: statistics, isLoading, error } = useQuery<RCAStatistics>({
    queryKey: ['rca-statistics'],
    queryFn: () => getRCAStatistics(),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner />
      </div>
    )
  }

  if (error || !statistics) {
    return (
      <div className="text-center py-8 text-slate-400">
        <AlertCircle className="w-8 h-8 mx-auto mb-2 text-slate-500" />
        <p>Failed to load RCA statistics</p>
      </div>
    )
  }

  // Prepare pie chart data
  const statusData = [
    { name: 'Analyzed', value: statistics.analyzed || 0, color: COLORS.analyzed },
    { name: 'Pending', value: statistics.pending || 0, color: COLORS.pending },
    { name: 'Dismissed', value: statistics.dismissed || 0, color: COLORS.dismissed },
  ].filter((d) => d.value > 0)

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardBody padding="md">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-slate-400">Total Analyses</p>
                <p className="text-3xl font-bold text-white mt-2">{statistics.total_analyses}</p>
              </div>
              <div className="p-3 rounded-lg bg-cyan-500/20 text-cyan-400">
                <Search className="w-6 h-6" />
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody padding="md">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-slate-400">Analyzed</p>
                <p className="text-3xl font-bold text-white mt-2">{statistics.analyzed}</p>
              </div>
              <div className="p-3 rounded-lg bg-emerald-500/20 text-emerald-400">
                <CheckCircle className="w-6 h-6" />
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody padding="md">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-slate-400">Pending</p>
                <p className="text-3xl font-bold text-white mt-2">{statistics.pending}</p>
              </div>
              <div className="p-3 rounded-lg bg-amber-500/20 text-amber-400">
                <AlertCircle className="w-6 h-6" />
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody padding="md">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-slate-400">Avg Causes</p>
                <p className="text-3xl font-bold text-white mt-2">
                  {statistics.avg_causes_per_anomaly.toFixed(1)}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-purple-500/20 text-purple-400">
                <TrendingUp className="w-6 h-6" />
              </div>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status Distribution */}
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-white">Status Distribution</h3>
          </CardHeader>
          <CardBody>
            {statusData.length === 0 ? (
              <div className="text-center py-12 text-slate-400">
                <p>No data available</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={statusData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {statusData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
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
                  <Legend wrapperStyle={{ color: '#94a3b8' }} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardBody>
        </Card>

        {/* Summary Stats */}
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-white">Summary</h3>
          </CardHeader>
          <CardBody>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-surface-700/50 rounded-lg">
                <span className="text-sm font-medium text-slate-300">Dismissed</span>
                <Badge variant="default" size="sm">
                  {statistics.dismissed}
                </Badge>
              </div>
              <div className="flex items-center justify-between p-3 bg-surface-700/50 rounded-lg">
                <span className="text-sm font-medium text-slate-300">Average Causes per Anomaly</span>
                <span className="text-sm font-semibold text-white">
                  {statistics.avg_causes_per_anomaly.toFixed(2)}
                </span>
              </div>
              {statistics.total_analyses > 0 && (
                <div className="flex items-center justify-between p-3 bg-surface-700/50 rounded-lg">
                  <span className="text-sm font-medium text-slate-300">Analysis Completion Rate</span>
                  <span className="text-sm font-semibold text-white">
                    {((statistics.analyzed / statistics.total_analyses) * 100).toFixed(1)}%
                  </span>
                </div>
              )}
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Quick Actions */}
      {onAnalyzeNew && (
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-white">Quick Actions</h3>
          </CardHeader>
          <CardBody>
            <div className="flex items-center gap-4">
              <Button variant="primary" onClick={onAnalyzeNew}>
                <Search className="w-4 h-4 mr-2" />
                Analyze New Anomaly
              </Button>
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  )
}

