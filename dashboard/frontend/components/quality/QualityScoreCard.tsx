'use client'

import { ArrowUpRight, ArrowDownRight, Minus, AlertTriangle, CheckCircle2, XCircle } from 'lucide-react'
import { Card, CardHeader, CardBody } from '@/components/ui'
import { Badge } from '@/components/ui/Badge'
import type { QualityScore, QualityTrend } from '@/types/quality'
import { formatDate } from '@/lib/utils'
import { cn } from '@/lib/utils'

export interface QualityScoreCardProps {
  score: QualityScore
  compact?: boolean
  className?: string
}

const componentLabels: Record<keyof QualityScore['components'], string> = {
  completeness: 'Completeness',
  validity: 'Validity',
  consistency: 'Consistency',
  freshness: 'Freshness',
  uniqueness: 'Uniqueness',
  accuracy: 'Accuracy',
}

function getStatusColor(status: QualityScore['status']) {
  switch (status) {
    case 'healthy':
      return {
        bg: 'from-emerald-500/20 to-emerald-600/5',
        border: 'border-emerald-500/20',
        text: 'text-emerald-400',
        badge: 'success' as const,
      }
    case 'warning':
      return {
        bg: 'from-amber-500/20 to-amber-600/5',
        border: 'border-amber-500/20',
        text: 'text-amber-400',
        badge: 'warning' as const,
      }
    case 'critical':
      return {
        bg: 'from-rose-500/20 to-rose-600/5',
        border: 'border-rose-500/20',
        text: 'text-rose-400',
        badge: 'error' as const,
      }
  }
}

function getComponentColor(score: number): 'success' | 'warning' | 'error' {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'error'
}

function TrendIndicator({ trend, percentage }: { trend?: QualityTrend | null; percentage?: number | null }) {
  if (!trend || trend === 'stable') {
    return (
      <div className="flex items-center gap-1 text-slate-500">
        <Minus className="w-4 h-4" />
        <span className="text-sm">Stable</span>
      </div>
    )
  }

  const isImproving = trend === 'improving'
  const TrendIcon = isImproving ? ArrowUpRight : ArrowDownRight
  const color = isImproving ? 'text-emerald-400' : 'text-rose-400'
  const sign = isImproving ? '+' : ''

  return (
    <div className={cn('flex items-center gap-1', color)}>
      <TrendIcon className="w-4 h-4" />
      <span className="text-sm font-medium">
        {sign}
        {percentage?.toFixed(1) || '0.0'}%
      </span>
    </div>
  )
}

export default function QualityScoreCard({ score, compact = false, className }: QualityScoreCardProps) {
  const statusColors = getStatusColor(score.status)
  const StatusIcon = score.status === 'healthy' ? CheckCircle2 : score.status === 'warning' ? AlertTriangle : XCircle

  return (
    <Card
      variant="glass"
      className={cn(
        'bg-gradient-to-br',
        statusColors.bg,
        statusColors.border,
        className
      )}
    >
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white">Data Quality Score</h3>
            {score.schema_name && (
              <p className="text-sm text-slate-400 mt-1">
                {score.schema_name}.{score.table_name}
              </p>
            )}
            {!score.schema_name && (
              <p className="text-sm text-slate-400 mt-1">{score.table_name}</p>
            )}
          </div>
          <Badge variant={statusColors.badge} size="md" icon={<StatusIcon className="w-3 h-3" />}>
            {score.status}
          </Badge>
        </div>
      </CardHeader>

      <CardBody>
        <div className="space-y-6">
          {/* Overall Score Display */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-400 mb-2">Overall Score</p>
              <div className="flex items-baseline gap-3">
                <span className={cn('text-5xl font-bold', statusColors.text)}>
                  {score.overall_score.toFixed(1)}
                </span>
                <span className="text-2xl text-slate-500">/ 100</span>
              </div>
            </div>
            {score.trend && (
              <div className="text-right">
                <TrendIndicator trend={score.trend} percentage={score.trend_percentage} />
              </div>
            )}
          </div>

          {!compact && (
            <>
              {/* Component Breakdown */}
              <div>
                <p className="text-sm font-medium text-slate-400 mb-3">Component Scores</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {Object.entries(score.components).map(([key, value]) => {
                    const label = componentLabels[key as keyof typeof componentLabels]
                    const componentVariant = getComponentColor(value)
                    return (
                      <div key={key} className="flex items-center justify-between p-3 bg-surface-900/30 rounded-lg">
                        <span className="text-sm text-slate-300">{label}</span>
                        <div className="flex items-center gap-2">
                          <div className="w-24 h-2 bg-surface-700 rounded-full overflow-hidden">
                            <div
                              className={cn(
                                'h-full transition-all',
                                componentVariant === 'success' && 'bg-emerald-500',
                                componentVariant === 'warning' && 'bg-amber-500',
                                componentVariant === 'error' && 'bg-rose-500'
                              )}
                              style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
                            />
                          </div>
                          <span className={cn('text-sm font-semibold w-12 text-right', statusColors.text)}>
                            {value.toFixed(1)}
                          </span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Issues Summary */}
              {(score.issues.total > 0 || score.issues.critical > 0 || score.issues.warnings > 0) && (
                <div>
                  <p className="text-sm font-medium text-slate-400 mb-3">Issues Summary</p>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="p-3 bg-surface-900/30 rounded-lg text-center">
                      <p className="text-xs text-slate-500 mb-1">Total</p>
                      <p className="text-lg font-semibold text-white">{score.issues.total}</p>
                    </div>
                    <div className="p-3 bg-surface-900/30 rounded-lg text-center">
                      <p className="text-xs text-slate-500 mb-1">Critical</p>
                      <p className="text-lg font-semibold text-rose-400">{score.issues.critical}</p>
                    </div>
                    <div className="p-3 bg-surface-900/30 rounded-lg text-center">
                      <p className="text-xs text-slate-500 mb-1">Warnings</p>
                      <p className="text-lg font-semibold text-amber-400">{score.issues.warnings}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Calculated At */}
              <div className="pt-4 border-t border-surface-700/50">
                <p className="text-xs text-slate-500">
                  Calculated: {formatDate(score.calculated_at)}
                </p>
              </div>
            </>
          )}
        </div>
      </CardBody>
    </Card>
  )
}

