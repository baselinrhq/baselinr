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

  // Fetch score trend
  const { data: trend, isLoading: trendLoading } = useQuery<TrendAnalysis>({
    queryKey: ['score-trend', tableName, schema],
    queryFn: () => fetchScoreTrend(tableName, schema),
    enabled: !!tableName && !isPlaceholder,
  })

  const isLoading = scoreLoading || historyLoading || columnsLoading || trendLoading

  const sortedColumns = useMemo(() => {
    if (!columnScores || !columnScores.scores || !Array.isArray(columnScores.scores)) return []
    return [...columnScores.scores].sort((a, b) => a.overall_score - b.overall_score)
  }, [columnScores])

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
        <Card>
          <CardBody>
            <p className="text-slate-400">Table name is required</p>
            <Link href="/quality">
              <Button variant="outline" className="mt-4">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Quality Scores
              </Button>
            </Link>
          </CardBody>
        </Card>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="p-6 lg:p-8 flex items-center justify-center min-h-[400px]">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!score) {
    return (
      <div className="p-6 lg:p-8">
        <Card>
          <CardBody>
            <p className="text-slate-400">Quality score not found for this table</p>
            <Link href="/quality">
              <Button variant="outline" className="mt-4">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Quality Scores
              </Button>
            </Link>
          </CardBody>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link href="/quality">
            <Button variant="ghost" size="sm" className="mb-2">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Quality Scores
            </Button>
          </Link>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <TrendingUp className="w-8 h-8 text-cyan-400" />
            {tableName}
            {schema && (
              <span className="text-lg font-normal text-slate-400">({schema})</span>
            )}
          </h1>
        </div>
        {trend && score && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-400">Trend:</span>
            <ScoreBadge score={score.overall_score} status={score.status} />
          </div>
        )}
      </div>

      {/* Main Score Card */}
      <QualityScoreCard score={score} />

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Score History Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Score History (90 days)</CardTitle>
          </CardHeader>
          <CardBody>
            {history && history.length > 0 ? (
              <ScoreHistoryChart data={history} />
            ) : (
              <p className="text-slate-400 text-sm">No history data available</p>
            )}
          </CardBody>
        </Card>

        {/* Score Radar Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Dimension Breakdown</CardTitle>
          </CardHeader>
          <CardBody>
            {score?.components && <ScoreRadarChart currentScore={score.components} />}
          </CardBody>
        </Card>
      </div>

      {/* Trend Analysis */}
      {trend && (
        <Card>
          <CardHeader>
            <CardTitle>Trend Analysis</CardTitle>
          </CardHeader>
          <CardBody>
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <span className="text-sm text-slate-400">Direction:</span>
                <Badge variant={trend.direction === 'improving' ? 'success' : trend.direction === 'degrading' ? 'error' : 'info'}>
                  {trend.direction}
                </Badge>
                <span className="text-sm text-slate-400">Change:</span>
                <Badge variant={trend.overall_change > 0 ? 'success' : 'error'}>
                  {trend.overall_change > 0 ? '+' : ''}{trend.overall_change.toFixed(1)}%
                </Badge>
              </div>
              {trend.periods_analyzed && (
                <p className="text-sm text-slate-300">
                  Analyzed {trend.periods_analyzed} period{trend.periods_analyzed !== 1 ? 's' : ''} with {trend.confidence.toFixed(1)}% confidence
                </p>
              )}
            </div>
          </CardBody>
        </Card>
      )}

      {/* Column Scores */}
      {sortedColumns && sortedColumns.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Column Scores (Lowest First)</CardTitle>
          </CardHeader>
          <CardBody>
            <div className="space-y-3">
              {sortedColumns.slice(0, 10).map((col) => (
                <div key={col.column_name} className="flex items-center justify-between p-3 bg-surface-800/40 rounded-lg">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-white">{col.column_name}</span>
                      <ScoreBadge score={col.overall_score} status={col.status} />
                    </div>
                    {col.issues && col.issues.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {col.issues.slice(0, 3).map((issue, idx) => (
                          <Badge key={idx} variant="warning" size="sm">
                            {issue}
                          </Badge>
                        ))}
                        {col.issues.length > 3 && (
                          <Badge variant="secondary" size="sm">
                            +{col.issues.length - 3} more
                          </Badge>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {sortedColumns.length > 10 && (
                <p className="text-sm text-slate-400 text-center mt-2">
                  Showing top 10 columns. {sortedColumns.length - 10} more columns available.
                </p>
              )}
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  )
}
