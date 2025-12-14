'use client'

import { useQuery } from '@tanstack/react-query'
import { Card, CardHeader, CardBody, CardTitle } from '@/components/ui'
import { LoadingSpinner } from '@/components/ui'
import { Badge } from '@/components/ui/Badge'
import { fetchScoreComparison } from '@/lib/api'
import type { ScoreComparison as ScoreComparisonType } from '@/types/quality'
import { cn } from '@/lib/utils'
import ScoreBadge from './ScoreBadge'

export interface ScoreComparisonProps {
  tables: string[]
  schema?: string
  className?: string
}

export default function ScoreComparison({ tables, schema, className }: ScoreComparisonProps) {
  const { data, isLoading, error } = useQuery<ScoreComparisonType>({
    queryKey: ['score-comparison', tables, schema],
    queryFn: () => fetchScoreComparison(tables, schema),
    enabled: tables.length >= 2,
  })

  if (isLoading) {
    return (
      <Card variant="glass" className={cn('bg-surface-900/30', className)}>
        <CardBody>
          <div className="flex items-center justify-center h-64">
            <LoadingSpinner size="lg" />
          </div>
        </CardBody>
      </Card>
    )
  }

  if (error) {
    return (
      <Card variant="glass" className={cn('bg-surface-900/30', className)}>
        <CardBody>
          <div className="text-center text-slate-400">
            Error loading comparison: {error instanceof Error ? error.message : 'Unknown error'}
          </div>
        </CardBody>
      </Card>
    )
  }

  if (!data || !data.tables || data.tables.length === 0) {
    return (
      <Card variant="glass" className={cn('bg-surface-900/30', className)}>
        <CardBody>
          <div className="text-center text-slate-400">No comparison data available</div>
        </CardBody>
      </Card>
    )
  }

  const { tables: comparedTables, comparison_metrics } = data

  return (
    <Card variant="glass" className={cn('bg-surface-900/30', className)}>
      <CardHeader>
        <CardTitle className="text-lg font-semibold text-white">Score Comparison</CardTitle>
      </CardHeader>
      <CardBody>
        <div className="space-y-6">
          {/* Comparison Metrics */}
          {comparison_metrics && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="p-4 bg-surface-800/50 rounded-lg">
                <p className="text-xs text-slate-500 mb-1">Best Performer</p>
                <p className="text-sm font-semibold text-emerald-400">
                  {comparison_metrics.best_performer || '-'}
                </p>
              </div>
              <div className="p-4 bg-surface-800/50 rounded-lg">
                <p className="text-xs text-slate-500 mb-1">Worst Performer</p>
                <p className="text-sm font-semibold text-rose-400">
                  {comparison_metrics.worst_performer || '-'}
                </p>
              </div>
              <div className="p-4 bg-surface-800/50 rounded-lg">
                <p className="text-xs text-slate-500 mb-1">Average Score</p>
                <p className="text-sm font-semibold text-white">
                  {comparison_metrics.average_score?.toFixed(1) || '-'}
                </p>
              </div>
              <div className="p-4 bg-surface-800/50 rounded-lg">
                <p className="text-xs text-slate-500 mb-1">Score Range</p>
                <p className="text-sm font-semibold text-white">
                  {comparison_metrics.score_range?.min?.toFixed(1) || '-'} -{' '}
                  {comparison_metrics.score_range?.max?.toFixed(1) || '-'}
                </p>
              </div>
            </div>
          )}

          {/* Table Comparison */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-surface-800/60">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Table
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Score
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Components
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-700/50">
                {comparedTables.map((table) => (
                  <tr key={`${table.schema_name || ''}.${table.table_name}`} className="hover:bg-surface-800/30">
                    <td className="px-4 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-white">
                        {table.schema_name ? `${table.schema_name}.${table.table_name}` : table.table_name}
                      </div>
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap">
                      <ScoreBadge score={table.overall_score} status={table.status} />
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap">
                      <Badge
                        variant={
                          table.status === 'healthy'
                            ? 'success'
                            : table.status === 'warning'
                            ? 'warning'
                            : 'error'
                        }
                        size="sm"
                      >
                        {table.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(table.components).map(([key, value]) => (
                          <div key={key} className="text-xs">
                            <span className="text-slate-500">{key}:</span>{' '}
                            <span className="text-slate-300 font-medium">{value.toFixed(1)}</span>
                          </div>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </CardBody>
    </Card>
  )
}
