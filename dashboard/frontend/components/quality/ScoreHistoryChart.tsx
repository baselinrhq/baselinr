'use client'

import { useState } from 'react'
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { Card, CardHeader, CardBody, CardTitle } from '@/components/ui'
import { Button } from '@/components/ui'
import type { QualityScore } from '@/types/quality'
import { cn } from '@/lib/utils'
import { formatDate } from '@/lib/utils'

export interface ScoreHistoryChartProps {
  scores: QualityScore[]
  showComponents?: boolean
  className?: string
  title?: string
}

type TimeRange = '7d' | '30d' | '90d' | 'all'

export default function ScoreHistoryChart({
  scores,
  showComponents = false,
  className,
  title = 'Score History',
}: ScoreHistoryChartProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>('30d')

  // Filter scores based on time range
  const filteredScores = (() => {
    if (timeRange === 'all') return scores
    const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90
    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() - days)
    return scores.filter((score) => new Date(score.calculated_at) >= cutoff)
  })()

  // Prepare chart data
  const chartData = filteredScores
    .slice()
    .reverse()
    .map((score) => ({
      date: formatDate(score.calculated_at, { month: 'short', day: 'numeric', year: 'numeric' }),
      timestamp: new Date(score.calculated_at).getTime(),
      overall: score.overall_score,
      completeness: score.components.completeness,
      validity: score.components.validity,
      consistency: score.components.consistency,
      freshness: score.components.freshness,
      uniqueness: score.components.uniqueness,
      accuracy: score.components.accuracy,
    }))

  return (
    <Card variant="glass" className={cn('bg-surface-900/30', className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold text-white">{title}</CardTitle>
          <div className="flex gap-2">
            <Button
              variant={timeRange === '7d' ? 'primary' : 'outline'}
              size="sm"
              onClick={() => setTimeRange('7d')}
            >
              7d
            </Button>
            <Button
              variant={timeRange === '30d' ? 'primary' : 'outline'}
              size="sm"
              onClick={() => setTimeRange('30d')}
            >
              30d
            </Button>
            <Button
              variant={timeRange === '90d' ? 'primary' : 'outline'}
              size="sm"
              onClick={() => setTimeRange('90d')}
            >
              90d
            </Button>
            <Button
              variant={timeRange === 'all' ? 'primary' : 'outline'}
              size="sm"
              onClick={() => setTimeRange('all')}
            >
              All
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardBody>
        {chartData.length === 0 ? (
          <div className="flex items-center justify-center h-80 text-slate-400">
            No data available for the selected time range
          </div>
        ) : (
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              {showComponents ? (
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorOverall" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="rgb(34, 211, 238)" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="rgb(34, 211, 238)" stopOpacity={0.1} />
                    </linearGradient>
                    <linearGradient id="colorCompleteness" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="rgb(16, 185, 129)" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="rgb(16, 185, 129)" stopOpacity={0.1} />
                    </linearGradient>
                    <linearGradient id="colorValidity" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="rgb(59, 130, 246)" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="rgb(59, 130, 246)" stopOpacity={0.1} />
                    </linearGradient>
                    <linearGradient id="colorConsistency" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="rgb(168, 85, 247)" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="rgb(168, 85, 247)" stopOpacity={0.1} />
                    </linearGradient>
                    <linearGradient id="colorFreshness" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="rgb(245, 158, 11)" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="rgb(245, 158, 11)" stopOpacity={0.1} />
                    </linearGradient>
                    <linearGradient id="colorUniqueness" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="rgb(236, 72, 153)" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="rgb(236, 72, 153)" stopOpacity={0.1} />
                    </linearGradient>
                    <linearGradient id="colorAccuracy" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="rgb(251, 146, 60)" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="rgb(251, 146, 60)" stopOpacity={0.1} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: 'rgb(148, 163, 184)', fontSize: 12 }}
                    angle={-45}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis
                    domain={[0, 100]}
                    tick={{ fill: 'rgb(148, 163, 184)', fontSize: 12 }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgb(30, 41, 59)',
                      border: '1px solid rgb(51, 65, 85)',
                      borderRadius: '8px',
                      color: 'rgb(226, 232, 240)',
                    }}
                  />
                  <Legend
                    wrapperStyle={{ color: 'rgb(148, 163, 184)', fontSize: '12px' }}
                    iconType="line"
                  />
                  <Area
                    type="monotone"
                    dataKey="overall"
                    stroke="rgb(34, 211, 238)"
                    fillOpacity={1}
                    fill="url(#colorOverall)"
                    name="Overall"
                  />
                  <Area
                    type="monotone"
                    dataKey="completeness"
                    stroke="rgb(16, 185, 129)"
                    fillOpacity={0.6}
                    fill="url(#colorCompleteness)"
                    name="Completeness"
                  />
                  <Area
                    type="monotone"
                    dataKey="validity"
                    stroke="rgb(59, 130, 246)"
                    fillOpacity={0.6}
                    fill="url(#colorValidity)"
                    name="Validity"
                  />
                  <Area
                    type="monotone"
                    dataKey="consistency"
                    stroke="rgb(168, 85, 247)"
                    fillOpacity={0.6}
                    fill="url(#colorConsistency)"
                    name="Consistency"
                  />
                  <Area
                    type="monotone"
                    dataKey="freshness"
                    stroke="rgb(245, 158, 11)"
                    fillOpacity={0.6}
                    fill="url(#colorFreshness)"
                    name="Freshness"
                  />
                  <Area
                    type="monotone"
                    dataKey="uniqueness"
                    stroke="rgb(236, 72, 153)"
                    fillOpacity={0.6}
                    fill="url(#colorUniqueness)"
                    name="Uniqueness"
                  />
                  <Area
                    type="monotone"
                    dataKey="accuracy"
                    stroke="rgb(251, 146, 60)"
                    fillOpacity={0.6}
                    fill="url(#colorAccuracy)"
                    name="Accuracy"
                  />
                </AreaChart>
              ) : (
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: 'rgb(148, 163, 184)', fontSize: 12 }}
                    angle={-45}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis
                    domain={[0, 100]}
                    tick={{ fill: 'rgb(148, 163, 184)', fontSize: 12 }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgb(30, 41, 59)',
                      border: '1px solid rgb(51, 65, 85)',
                      borderRadius: '8px',
                      color: 'rgb(226, 232, 240)',
                    }}
                  />
                  <Legend
                    wrapperStyle={{ color: 'rgb(148, 163, 184)', fontSize: '12px' }}
                    iconType="line"
                  />
                  <Line
                    type="monotone"
                    dataKey="overall"
                    stroke="rgb(34, 211, 238)"
                    strokeWidth={2}
                    dot={{ fill: 'rgb(34, 211, 238)', r: 4 }}
                    activeDot={{ r: 6 }}
                    name="Overall Score"
                  />
                </LineChart>
              )}
            </ResponsiveContainer>
          </div>
        )}
      </CardBody>
    </Card>
  )
}
