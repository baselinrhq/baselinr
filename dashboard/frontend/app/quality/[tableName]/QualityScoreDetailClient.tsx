'use client'

import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams, useParams } from 'next/navigation'
import { ArrowLeft, TrendingUp } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui'
import { LoadingSpinner } from '@/components/ui'
import { Card, CardHeader, CardBody, CardTitle } from '@/components/ui'
import { Badge } from '@/components/ui/Badge'
import {
  fetchTableScore,
  fetchScoreHistory,
  fetchColumnScores,
  fetchScoreTrend,
} from '@/lib/api'
import QualityScoreCard from '@/components/quality/QualityScoreCard'
import ScoreRadarChart from '@/components/quality/ScoreRadarChart'
import ScoreHistoryChart from '@/components/quality/ScoreHistoryChart'
import ScoreBadge from '@/components/quality/ScoreBadge'
import type { QualityScore, TrendAnalysis } from '@/types/quality'
import { formatDate } from '@/lib/utils'

export default function QualityScoreDetailClient() {
  const params = useParams()
  const searchParams = useSearchParams()
  const schema = searchParams.get('schema') || undefined
  const tableName = params?.tableName ? decodeURIComponent(String(params.tableName)) : ''

  const isPlaceholder = tableName === '__placeholder__'

  // Fetch table score
  const { data: score, isLoading: scoreLoading } = useQuery<QualityScore>({
    queryKey: ['table-score', tableName, schema],
    queryFn: () => fetchTableScore(tableName, schema),
    enabled: !!tableName && !isPlaceholder,
  })

  // Fetch score history
  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ['score-history', tableName, schema],
    queryFn: () => fetchScoreHistory(tableName, schema, 90),
    enabled: !!tableName && !isPlaceholder,
  })

  // Fetch column scores
  const { data: columnScores, isLoading: columnsLoading } = useQuery({
    queryKey: ['column-scores', tableName, schema],
    queryFn: () => fetchColumnScores(tableName, schema, 30),
    enabled: !!tableName && !isPlaceholder,
  })

  // Fetch trend analysis
  const { data: trend, isLoading: trendLoading } = useQuery<TrendAnalysis>({
    queryKey: ['score-trend', tableName, schema],
    queryFn: () => fetchScoreTrend(tableName, schema),
    enabled: !!tableName && !isPlaceholder,
  })

  // Get previous score for radar chart
  const previousScore = useMemo(() => {
    if (!history?.scores || history.scores.length < 2) return null
    return history.scores[1] // Second item is previous (history is DESC)
  }, [history])

  // Handle placeholder route used for static export
  if (isPlaceholder) {
    return (
      <div className="p-6">
        <div className="text-sm text-slate-400">Loading...</div>
      </div>
    )
  }

  if (!tableName) {
    return (
      <div className="p-6 lg:p-8">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-white mb-4">Invalid Table Name</h1>
          <Link href="/quality">
            <Button>Back to Quality Scores</Button>
          </Link>
        </div>
      </div>
    )
  }

  if (scoreLoading) {
    return (
      <div className="p-6 lg:p-8">
        <div className="flex items-center justify-center h-96">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    )
  }

  if (!score) {
    return (
      <div className="p-6 lg:p-8">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-white mb-4">Quality Score Not Found</h1>
          <p className="text-slate-400 mb-4">
            No quality score found for table: {tableName}
            {schema && ` (schema: ${schema})`}
          </p>
          <Link href="/quality">
            <Button>Back to Quality Scores</Button>
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/quality">
            <Button variant="outline" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <div className="p-2 rounded-lg bg-emerald-500/10">
                <TrendingUp className="w-6 h-6 text-emerald-400" />
              </div>
              Quality Score: {schema ? `${schema}.${tableName}` : tableName}
            </h1>
            <p className="mt-2 text-sm text-slate-400">
              Detailed quality metrics and historical trends
            </p>
          </div>
        </div>
      </div>

      {/* Main Score Card */}
      <QualityScoreCard score={score} />

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Radar Chart */}
        <ScoreRadarChart
          currentScore={score.components}
          previousScore={previousScore?.components || null}
          title="Component Breakdown"
        />

        {/* Trend Analysis Card */}
        {trend && !trendLoading && (
          <Card variant="glass" className="bg-surface-900/30">
            <CardHeader>
              <CardTitle className="text-lg font-semibold text-white">Trend Analysis</CardTitle>
            </CardHeader>
            <CardBody>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">Direction</span>
                  <Badge
                    variant={
                      trend.direction === 'improving'
                        ? 'success'
                        : trend.direction === 'degrading'
                        ? 'error'
                        : 'default'
                    }
                    size="md"
                  >
                    {trend.direction}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">Rate of Change</span>
                  <span className="text-sm font-semibold text-white">
                    {trend.rate_of_change > 0 ? '+' : ''}
                    {trend.rate_of_change.toFixed(2)}% per period
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">Overall Change</span>
                  <span className="text-sm font-semibold text-white">
                    {trend.overall_change > 0 ? '+' : ''}
                    {trend.overall_change.toFixed(2)}%
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">Confidence</span>
                  <span className="text-sm font-semibold text-white">
                    {(trend.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">Periods Analyzed</span>
                  <span className="text-sm font-semibold text-white">{trend.periods_analyzed}</span>
                </div>
              </div>
            </CardBody>
          </Card>
        )}
      </div>

      {/* History Chart */}
      {history && !historyLoading && history.scores.length > 0 && (
        <ScoreHistoryChart
          scores={history.scores}
          showComponents={true}
          title="Score History & Component Trends"
        />
      )}

      {/* Column Scores */}
      {columnScores && !columnsLoading && columnScores.scores.length > 0 && (
        <Card variant="glass" className="bg-surface-900/30">
          <CardHeader>
            <CardTitle className="text-lg font-semibold text-white">Column-Level Scores</CardTitle>
          </CardHeader>
          <CardBody>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-surface-800/60">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                      Column
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
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                      Calculated
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-700/50">
                  {columnScores.scores.map((columnScore) => (
                    <tr
                      key={columnScore.column_name}
                      className="hover:bg-surface-800/30 transition-colors"
                    >
                      <td className="px-4 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-white">{columnScore.column_name}</div>
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap">
                        <ScoreBadge score={columnScore.overall_score} status={columnScore.status} />
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap">
                        <Badge
                          variant={
                            columnScore.status === 'healthy'
                              ? 'success'
                              : columnScore.status === 'warning'
                              ? 'warning'
                              : 'error'
                          }
                          size="sm"
                        >
                          {columnScore.status}
                        </Badge>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(columnScore.components).map(([key, value]) => (
                            <div key={key} className="text-xs">
                              <span className="text-slate-500">{key}:</span>{' '}
                              <span className="text-slate-300 font-medium">{value.toFixed(1)}</span>
                            </div>
                          ))}
                        </div>
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-sm text-slate-400">
                        {formatDate(columnScore.calculated_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardBody>
        </Card>
      )}

      {columnScores && !columnsLoading && columnScores.scores.length === 0 && (
        <Card variant="glass" className="bg-surface-900/30">
          <CardBody>
            <div className="text-center text-slate-400 py-8">
              No column-level scores available for this table
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  )
}
