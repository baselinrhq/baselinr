import Link from 'next/link'
import { AlertTriangle } from 'lucide-react'
import clsx from 'clsx'

interface DriftAlert {
  event_id: string
  run_id: string
  table_name: string
  column_name?: string
  metric_name: string
  baseline_value?: number
  current_value?: number
  change_percent?: number
  severity: string
  timestamp: string
  warehouse_type: string
}

interface DriftAlertsTableProps {
  alerts: DriftAlert[]
  showDetails?: boolean
  onRowClick?: (eventId: string) => void
}

const severityColors = {
  low: 'bg-success-500/20 text-success-400 border-success-500/30',
  medium: 'bg-warning-500/20 text-warning-400 border-warning-500/30',
  high: 'bg-danger-500/20 text-danger-400 border-danger-500/30',
}

export default function DriftAlertsTable({ alerts, showDetails = false, onRowClick }: DriftAlertsTableProps) {
  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-surface-800/50 border-b border-surface-700/50">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Severity
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Table
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Column
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Metric
              </th>
              {showDetails && (
                <>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Baseline
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Current
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Change
                  </th>
                </>
              )}
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Detected At
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-700/50">
            {alerts.map((alert) => (
              <tr
                key={alert.event_id}
                className={clsx(
                  'transition-colors',
                  onRowClick && 'cursor-pointer hover:bg-surface-800/50'
                )}
                onClick={() => onRowClick?.(alert.event_id)}
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={clsx(
                    'px-2.5 py-1 text-xs font-medium rounded-full border capitalize',
                    severityColors[alert.severity as keyof typeof severityColors] || severityColors.low
                  )}>
                    {alert.severity}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <Link 
                    href={`/tables/${encodeURIComponent(alert.table_name)}`}
                    className="text-sm font-medium text-accent-400 hover:text-accent-300 transition-colors"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {alert.table_name}
                  </Link>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
                  {alert.column_name || <span className="text-slate-600">—</span>}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <span className="font-mono text-xs bg-surface-700/50 text-slate-300 px-2 py-1 rounded">
                    {alert.metric_name}
                  </span>
                </td>
                {showDetails && (
                  <>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300 font-mono">
                      {alert.baseline_value?.toFixed(2) || <span className="text-slate-600">—</span>}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300 font-mono">
                      {alert.current_value?.toFixed(2) || <span className="text-slate-600">—</span>}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {alert.change_percent !== undefined ? (
                        <span className={clsx(
                          'text-sm font-semibold font-mono',
                          alert.change_percent > 0 ? 'text-danger-400' : 'text-success-400'
                        )}>
                          {alert.change_percent > 0 ? '+' : ''}{alert.change_percent.toFixed(1)}%
                        </span>
                      ) : <span className="text-slate-600">—</span>}
                    </td>
                  </>
                )}
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-400">
                  {new Date(alert.timestamp).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {alerts.length === 0 && (
        <div className="text-center py-16">
          <div className="w-16 h-16 rounded-full bg-surface-800 flex items-center justify-center mx-auto mb-4">
            <AlertTriangle className="w-8 h-8 text-slate-600" />
          </div>
          <p className="text-slate-400 font-medium">No drift alerts found</p>
          <p className="text-sm text-slate-500 mt-1">Adjust your filters or check back later</p>
        </div>
      )}
    </div>
  )
}
