import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import clsx from 'clsx'

interface KPICardProps {
  title: string
  value: string | number
  icon: React.ReactNode
  trend?: 'up' | 'down' | 'stable'
  color?: 'blue' | 'green' | 'orange' | 'purple'
  changePercent?: number
}

const colorClasses = {
  blue: 'bg-blue-50 text-blue-600',
  green: 'bg-green-50 text-green-600',
  orange: 'bg-orange-50 text-orange-600',
  purple: 'bg-purple-50 text-purple-600',
}

const trendIcons = {
  up: <TrendingUp className="w-4 h-4 text-green-600" />,
  down: <TrendingDown className="w-4 h-4 text-red-600" />,
  stable: <Minus className="w-4 h-4 text-gray-600" />,
}

export default function KPICard({
  title,
  value,
  icon,
  trend = 'stable',
  color = 'blue',
  changePercent,
}: KPICardProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
          {changePercent !== undefined && (
            <div className="flex items-center gap-1 mt-2">
              {trendIcons[trend]}
              <span className="text-sm text-gray-600">{changePercent}% vs last period</span>
            </div>
          )}
        </div>
        <div className={clsx('p-3 rounded-lg', colorClasses[color])}>
          {icon}
        </div>
      </div>
    </div>
  )
}

