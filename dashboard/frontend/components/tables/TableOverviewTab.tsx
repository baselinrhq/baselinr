'use client'

import { useQuery } from '@tanstack/react-query'
import { TrendingUp, Activity } from 'lucide-react'
import { LoadingSpinner } from '@/components/ui'
import { fetchTableOverview } from '@/lib/api'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import RunsTable from '@/components/RunsTable'

interface TableOverviewTabProps {
  tableName: string
  schema?: string
  warehouse?: string
}

export default function TableOverviewTab({
  tableName,
  schema,
  warehouse
}: TableOverviewTabProps) {
  const { data: overview, isLoading, error } = useQuery({
    queryKey: ['table-overview', tableName, schema, warehouse],
    queryFn: () => fetchTableOverview(tableName, { schema, warehouse }),
    staleTime: 30000
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error || !overview) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <p className="text-red-800 font-medium">Error loading table overview</p>
        <p className="text-red-600 text-sm mt-1">
          {error instanceof Error ? error.message : 'Unknown error'}
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm font-medium text-gray-600">Rows</p>
          <p className="text-2xl font-bold text-gray-900 mt-2">
            {overview.row_count.toLocaleString()}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm font-medium text-gray-600">Columns</p>
          <p className="text-2xl font-bold text-gray-900 mt-2">
            {overview.column_count}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm font-medium text-gray-600">Total Runs</p>
          <p className="text-2xl font-bold text-gray-900 mt-2">
            {overview.total_runs}
          </p>
        </div>
        <div className={`bg-white rounded-lg shadow p-6 ${overview.drift_count > 0 ? 'border-2 border-orange-200 bg-orange-50' : ''}`}>
          <p className={`text-sm font-medium ${overview.drift_count > 0 ? 'text-orange-800' : 'text-gray-600'}`}>
            Drift Events
          </p>
          <p className={`text-2xl font-bold mt-2 ${overview.drift_count > 0 ? 'text-orange-900' : 'text-gray-900'}`}>
            {overview.drift_count}
          </p>
        </div>
      </div>

      {/* Validation Summary */}
      {overview.validation_pass_rate !== null && overview.validation_pass_rate !== undefined && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Validation Pass Rate</p>
              <p className="text-2xl font-bold text-gray-900 mt-2">
                {overview.validation_pass_rate.toFixed(1)}%
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-600">
                {overview.total_validation_rules} rules
              </p>
              {overview.failed_validation_rules > 0 && (
                <p className="text-sm text-red-600 mt-1">
                  {overview.failed_validation_rules} failed
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Row Count Trend */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5" />
          Row Count Trend
        </h2>
        <div className="h-64">
          {overview.row_count_trend && overview.row_count_trend.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={overview.row_count_trend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={(value) => new Date(value).toLocaleDateString()}
                />
                <YAxis />
                <Tooltip
                  labelFormatter={(value) => new Date(value).toLocaleString()}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#0ea5e9"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              <p>No trend data available</p>
            </div>
          )}
        </div>
      </div>

      {/* Column Metrics */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Column Metrics</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Column Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Null %
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Distinct
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Min
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Max
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Mean
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {overview.columns && overview.columns.length > 0 ? (
                overview.columns.map((column) => (
                  <tr key={column.column_name} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {column.column_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <span className="px-2 py-1 bg-gray-100 rounded text-xs font-mono">
                        {column.column_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {column.null_percent ? `${column.null_percent.toFixed(1)}%` : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {column.distinct_count?.toLocaleString() || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {column.min_value !== null && column.min_value !== undefined
                        ? String(column.min_value).substring(0, 20)
                        : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {column.max_value !== null && column.max_value !== undefined
                        ? String(column.max_value).substring(0, 20)
                        : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {column.mean ? column.mean.toFixed(2) : '-'}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-gray-500">
                    No column metrics available
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Runs */}
      {overview.recent_runs && overview.recent_runs.length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Recent Runs
            </h2>
          </div>
          <div className="p-6">
            <RunsTable runs={overview.recent_runs.map(run => ({
              run_id: run.run_id,
              dataset_name: run.table || run.dataset_name || tableName,
              schema_name: run.schema,
              warehouse_type: run.warehouse,
              profiled_at: run.started_at,
              status: run.status,
              row_count: run.rows_profiled,
              column_count: run.metrics_count,
              has_drift: false
            }))} />
          </div>
        </div>
      )}
    </div>
  )
}

