'use client'

import { X, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { RunComparison as RunComparisonType } from '@/lib/api'

interface RunComparisonProps {
  comparison: RunComparisonType
  onClose: () => void
}

export default function RunComparison({ comparison, onClose }: RunComparisonProps) {
  const { runs, comparison: comparisonData } = comparison

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'N/A'
    if (seconds < 60) return `${seconds.toFixed(1)}s`
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`
    return `${(seconds / 3600).toFixed(1)}h`
  }

  const getChangeColor = (changePercent: number) => {
    if (changePercent > 0) return 'text-red-600'
    if (changePercent < 0) return 'text-green-600'
    return 'text-gray-600'
  }

  const getChangeIcon = (changePercent: number) => {
    if (changePercent > 0) return <TrendingUp className="w-4 h-4" />
    if (changePercent < 0) return <TrendingDown className="w-4 h-4" />
    return <Minus className="w-4 h-4" />
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-7xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">Run Comparison</h2>
            <Button variant="secondary" onClick={onClose}>
              <X className="w-4 h-4 mr-2" />
              Close
            </Button>
          </div>

          {/* Run Metadata Comparison */}
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Run Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {runs.map((run, index) => (
                <div key={run.run_id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-500">Run {index + 1}</span>
                    <Badge variant={
                      run.status === 'failed' ? 'error' :
                      run.status === 'completed' || run.status === 'success' ? 'success' :
                      run.status === 'drift_detected' ? 'warning' :
                      'default'
                    }>{run.status}</Badge>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="text-gray-500">Table:</span>{' '}
                      <span className="font-medium">{run.dataset_name}</span>
                    </div>
                    {run.schema_name && (
                      <div>
                        <span className="text-gray-500">Schema:</span>{' '}
                        <span className="font-medium">{run.schema_name}</span>
                      </div>
                    )}
                    <div>
                      <span className="text-gray-500">Warehouse:</span>{' '}
                      <span className="font-medium capitalize">{run.warehouse_type}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Profiled At:</span>{' '}
                      <span className="font-medium">{formatDate(run.profiled_at)}</span>
                    </div>
                    {run.duration_seconds && (
                      <div>
                        <span className="text-gray-500">Duration:</span>{' '}
                        <span className="font-medium">{formatDuration(run.duration_seconds)}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Summary Comparison */}
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Summary</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border border-gray-200 rounded-lg p-4">
                <div className="text-sm text-gray-500 mb-1">Row Count Difference</div>
                <div className={`text-2xl font-bold ${getChangeColor(comparisonData.row_count_diff)}`}>
                  {comparisonData.row_count_diff > 0 ? '+' : ''}
                  {comparisonData.row_count_diff?.toLocaleString() || '—'}
                </div>
              </div>
              <div className="border border-gray-200 rounded-lg p-4">
                <div className="text-sm text-gray-500 mb-1">Column Count Difference</div>
                <div className={`text-2xl font-bold ${getChangeColor(comparisonData.column_count_diff)}`}>
                  {comparisonData.column_count_diff > 0 ? '+' : ''}
                  {comparisonData.column_count_diff}
                </div>
              </div>
            </div>
          </div>

          {/* Common Columns */}
          {comparisonData.common_columns.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Common Columns ({comparisonData.common_columns.length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {comparisonData.common_columns.map((col) => (
                  <Badge key={col} variant="info">{col}</Badge>
                ))}
              </div>
            </div>
          )}

          {/* Unique Columns */}
          {Object.keys(comparisonData.unique_columns).length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Unique Columns</h3>
              <div className="space-y-2">
                {Object.entries(comparisonData.unique_columns).map(([runId, columns]) => {
                  const run = runs.find((r) => r.run_id === runId)
                  return (
                    <div key={runId} className="border border-gray-200 rounded-lg p-3">
                      <div className="text-sm font-medium text-gray-700 mb-2">
                        {run?.dataset_name || runId}:
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {columns.map((col) => (
                          <Badge key={col} variant="warning">{col}</Badge>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Metric Differences */}
          {comparisonData.metric_differences.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Metric Differences</h3>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="border border-gray-200 px-4 py-2 text-left text-sm font-medium text-gray-700">
                        Column
                      </th>
                      <th className="border border-gray-200 px-4 py-2 text-left text-sm font-medium text-gray-700">
                        Metric
                      </th>
                      <th className="border border-gray-200 px-4 py-2 text-left text-sm font-medium text-gray-700">
                        Baseline
                      </th>
                      <th className="border border-gray-200 px-4 py-2 text-left text-sm font-medium text-gray-700">
                        Current
                      </th>
                      <th className="border border-gray-200 px-4 py-2 text-left text-sm font-medium text-gray-700">
                        Change
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparisonData.metric_differences.map((diff, index) => (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="border border-gray-200 px-4 py-2 text-sm">{diff.column}</td>
                        <td className="border border-gray-200 px-4 py-2 text-sm">{diff.metric}</td>
                        <td className="border border-gray-200 px-4 py-2 text-sm">
                          {typeof diff.baseline_value === 'number'
                            ? diff.baseline_value.toLocaleString(undefined, { maximumFractionDigits: 2 })
                            : diff.baseline_value}
                        </td>
                        <td className="border border-gray-200 px-4 py-2 text-sm">
                          {typeof diff.current_value === 'number'
                            ? diff.current_value.toLocaleString(undefined, { maximumFractionDigits: 2 })
                            : diff.current_value}
                        </td>
                        <td className={`border border-gray-200 px-4 py-2 text-sm font-medium ${getChangeColor(diff.change_percent)}`}>
                          <div className="flex items-center gap-1">
                            {getChangeIcon(diff.change_percent)}
                            {diff.change_percent > 0 ? '+' : ''}
                            {diff.change_percent.toFixed(2)}%
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Empty State */}
          {comparisonData.metric_differences.length === 0 &&
            comparisonData.common_columns.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                No comparison data available. Runs may not have overlapping columns or metrics.
              </div>
            )}
        </div>
      </Card>
    </div>
  )
}

