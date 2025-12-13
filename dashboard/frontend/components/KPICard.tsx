import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react'
import clsx from 'clsx'

interface KPICardProps {
  title: string
  value: string | number
  icon: React.ReactNode
  trend?: 'up' | 'down' | 'stable'
  color?: 'blue' | 'green' | 'orange' | 'purple' | 'cyan' | 'emerald' | 'amber' | 'rose'
  changePercent?: number
  subtitle?: string
}

const colorClasses = {
  // Legacy colors (light mode compat)
  blue: {
    card: 'from-accent-500/20 to-accent-600/5 border-accent-500/20',
    icon: 'bg-accent-500/10 text-accent-400',
  },
  green: {
    card: 'from-success-500/20 to-success-600/5 border-success-500/20',
    icon: 'bg-success-500/10 text-success-400',
  },
  orange: {
    card: 'from-warning-500/20 to-warning-600/5 border-warning-500/20',
    icon: 'bg-warning-500/10 text-warning-400',
  },
  purple: {
    card: 'from-purple-500/20 to-purple-600/5 border-purple-500/20',
    icon: 'bg-purple-500/10 text-purple-400',
  },
  // New semantic colors
  cyan: {
    card: 'from-accent-500/20 to-accent-600/5 border-accent-500/20',
    icon: 'bg-accent-500/10 text-accent-400',
  },
  emerald: {
    card: 'from-success-500/20 to-success-600/5 border-success-500/20',
    icon: 'bg-success-500/10 text-success-400',
  },
  amber: {
    card: 'from-warning-500/20 to-warning-600/5 border-warning-500/20',
    icon: 'bg-warning-500/10 text-warning-400',
  },
  rose: {
    card: 'from-danger-500/20 to-danger-600/5 border-danger-500/20',
    icon: 'bg-danger-500/10 text-danger-400',
  },
}

export default function KPICard({
  title,
  value,
  icon,
  trend = 'stable',
  color = 'blue',
  changePercent,
  subtitle,
}: KPICardProps) {
  const TrendIcon = trend === 'up' ? ArrowUpRight : trend === 'down' ? ArrowDownRight : Minus
  const classes = colorClasses[color] || colorClasses.blue

  return (
    <div
      className={clsx(
        'relative overflow-hidden rounded-xl border bg-gradient-to-br p-5 transition-all duration-200 hover:shadow-lg hover:shadow-black/10',
        classes.card
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-slate-400">{title}</p>
          <p className="text-3xl font-bold text-white mt-2">{value}</p>
          {changePercent !== undefined && (
            <div className="flex items-center gap-1 mt-2">
              <TrendIcon
                className={clsx(
                  'w-4 h-4',
                  trend === 'up' && 'text-success-400',
                  trend === 'down' && 'text-danger-400',
                  trend === 'stable' && 'text-slate-500'
                )}
              />
              <span
                className={clsx(
                  'text-sm',
                  trend === 'up' && 'text-success-400',
                  trend === 'down' && 'text-danger-400',
                  trend === 'stable' && 'text-slate-500'
                )}
              >
                {changePercent}% vs last period
              </span>
            </div>
          )}
          {subtitle && (
            <p className="text-sm text-slate-500 mt-2">{subtitle}</p>
          )}
        </div>
        <div className={clsx('p-3 rounded-lg', classes.icon)}>
          {icon}
        </div>
      </div>
    </div>
  )
}
