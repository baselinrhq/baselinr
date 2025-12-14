'use client'

import { cn } from '@/lib/utils'
import type { QualityStatus } from '@/types/quality'

export interface ScoreBadgeProps {
  score: number
  status: QualityStatus
  size?: 'sm' | 'md'
  showTooltip?: boolean
  className?: string
}

const sizeStyles = {
  sm: 'px-2 py-0.5 text-xs font-semibold',
  md: 'px-2.5 py-1 text-sm font-semibold',
}

export default function ScoreBadge({
  score,
  status,
  size = 'md',
  showTooltip = false,
  className,
}: ScoreBadgeProps) {
  const formattedScore = score.toFixed(1)

  const badge = (
    <span
      className={cn(
        'inline-flex items-center gap-1 font-medium rounded-full',
        sizeStyles[size],
        className
      )}
      style={{
        backgroundColor:
          status === 'healthy'
            ? 'rgba(16, 185, 129, 0.2)'
            : status === 'warning'
            ? 'rgba(245, 158, 11, 0.2)'
            : 'rgba(244, 63, 94, 0.2)',
        color:
          status === 'healthy'
            ? 'rgb(52, 211, 153)'
            : status === 'warning'
            ? 'rgb(251, 191, 36)'
            : 'rgb(251, 113, 133)',
        border:
          status === 'healthy'
            ? '1px solid rgba(16, 185, 129, 0.5)'
            : status === 'warning'
            ? '1px solid rgba(245, 158, 11, 0.5)'
            : '1px solid rgba(244, 63, 94, 0.5)',
      }}
      title={showTooltip ? `Quality Score: ${formattedScore} (${status})` : undefined}
    >
      {formattedScore}
    </span>
  )

  if (showTooltip) {
    return (
      <div className="relative group">
        {badge}
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-surface-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10 border border-surface-700">
          Quality Score: {formattedScore}
          <br />
          Status: {status}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
            <div className="w-2 h-2 bg-surface-800 border-r border-b border-surface-700 transform rotate-45"></div>
          </div>
        </div>
      </div>
    )
  }

  return badge
}

