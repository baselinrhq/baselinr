import { CheckCircle2, Bell, Clock } from 'lucide-react'
import KPICard from '@/components/KPICard'
import { DashboardMetrics } from '@/lib/api'

interface EnhancedKPIsProps {
  metrics: DashboardMetrics
}

export default function EnhancedKPIs({ metrics }: EnhancedKPIsProps) {
  // Determine validation pass rate color and trend
  const getValidationColor = (rate?: number | null): 'green' | 'orange' | 'red' => {
    if (rate === null || rate === undefined) return 'green'
    if (rate >= 90) return 'green'
    if (rate >= 70) return 'orange'
    return 'red'
  }

  const getValidationTrend = (): 'up' | 'down' | 'stable' => {
    // For now, return stable. Could be enhanced with historical comparison
    return 'stable'
  }

  // Format validation pass rate
  const formatValidationRate = (rate?: number | null): string => {
    if (rate === null || rate === undefined) return 'N/A'
    return `${rate.toFixed(1)}%`
  }

  // Format data freshness
  const formatDataFreshness = (hours?: number | null): string => {
    if (hours === null || hours === undefined) return 'N/A'
    if (hours < 1) return '< 1 hour'
    if (hours < 24) return `${Math.round(hours)} hours`
    const days = Math.floor(hours / 24)
    return `${days} day${days !== 1 ? 's' : ''}`
  }

  // Determine freshness color based on staleness
  const getFreshnessColor = (hours?: number | null): 'green' | 'orange' | 'red' => {
    if (hours === null || hours === undefined) return 'green'
    if (hours <= 24) return 'green'
    if (hours <= 48) return 'orange'
    return 'red'
  }

  // Determine active alerts color
  const getAlertsColor = (count: number): 'green' | 'orange' | 'red' => {
    if (count === 0) return 'green'
    if (count <= 5) return 'orange'
    return 'red'
  }

  return (
    <>
      {/* Validation Pass Rate */}
      {metrics.validation_pass_rate !== undefined && metrics.total_validation_rules > 0 && (
        <KPICard
          title="Validation Pass Rate"
          value={formatValidationRate(metrics.validation_pass_rate)}
          icon={<CheckCircle2 className="w-6 h-6" />}
          trend={getValidationTrend()}
          color={getValidationColor(metrics.validation_pass_rate)}
        />
      )}

      {/* Active Alerts */}
      <KPICard
        title="Active Alerts"
        value={metrics.active_alerts}
        icon={<Bell className="w-6 h-6" />}
        trend={metrics.active_alerts > 0 ? 'up' : 'stable'}
        color={getAlertsColor(metrics.active_alerts)}
      />

      {/* Data Freshness */}
      {metrics.data_freshness_hours !== undefined && (
        <KPICard
          title="Data Freshness"
          value={formatDataFreshness(metrics.data_freshness_hours)}
          icon={<Clock className="w-6 h-6" />}
          trend={metrics.data_freshness_hours > 48 ? 'down' : 'stable'}
          color={getFreshnessColor(metrics.data_freshness_hours)}
        />
      )}
    </>
  )
}

