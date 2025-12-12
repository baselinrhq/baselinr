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
      <div className="text-center py-8 text-gray-500">
        <AlertCircle className="w-8 h-8 mx-auto mb-2 text-gray-400" />
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
                <p className="text-sm font-medium text-gray-600">Total Analyses</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{statistics.total_analyses}</p>
              </div>
              <div className="p-3 rounded-lg bg-blue-50 text-blue-600">
                <Search className="w-6 h-6" />
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody padding="md">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Analyzed</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{statistics.analyzed}</p>
              </div>
              <div className="p-3 rounded-lg bg-green-50 text-green-600">
                <CheckCircle className="w-6 h-6" />
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody padding="md">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Pending</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{statistics.pending}</p>
              </div>
              <div className="p-3 rounded-lg bg-yellow-50 text-yellow-600">
                <AlertCircle className="w-6 h-6" />
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody padding="md">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Avg Causes</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {statistics.avg_causes_per_anomaly.toFixed(1)}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-purple-50 text-purple-600">
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
            <h3 className="text-lg font-semibold text-gray-900">Status Distribution</h3>
          </CardHeader>
          <CardBody>
            {statusData.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
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
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardBody>
        </Card>

        {/* Summary Stats */}
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-gray-900">Summary</h3>
          </CardHeader>
          <CardBody>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm font-medium text-gray-700">Dismissed</span>
                <Badge variant="default" size="sm">
                  {statistics.dismissed}
                </Badge>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm font-medium text-gray-700">Average Causes per Anomaly</span>
                <span className="text-sm font-semibold text-gray-900">
                  {statistics.avg_causes_per_anomaly.toFixed(2)}
                </span>
              </div>
              {statistics.total_analyses > 0 && (
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <span className="text-sm font-medium text-gray-700">Analysis Completion Rate</span>
                  <span className="text-sm font-semibold text-gray-900">
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
            <h3 className="text-lg font-semibold text-gray-900">Quick Actions</h3>
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

