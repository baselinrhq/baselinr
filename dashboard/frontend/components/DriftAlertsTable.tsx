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
  low: 'bg-green-100 text-green-800 border-green-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  high: 'bg-red-100 text-red-800 border-red-200',
}

export default function DriftAlertsTable({ alerts, showDetails = false, onRowClick }: DriftAlertsTableProps) {
  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Severity
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Table
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Column
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Metric
              </th>
              {showDetails && (
                <>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Baseline
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Current
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Change
                  </th>
                </>
              )}
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Detected At
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {alerts.map((alert) => (
              <tr
                key={alert.event_id}
                className={clsx(
                  'hover:bg-gray-50',
                  onRowClick && 'cursor-pointer'
                )}
                onClick={() => onRowClick?.(alert.event_id)}
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={clsx(
                    'px-2 py-1 text-xs font-medium rounded border capitalize',
                    severityColors[alert.severity as keyof typeof severityColors] || severityColors.low
                  )}>
                    {alert.severity}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <Link 
                    href={`/tables/${alert.table_name}`}
                    className="text-sm font-medium text-primary-600 hover:text-primary-800"
                  >
                    {alert.table_name}
                  </Link>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {alert.column_name || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  <span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                    {alert.metric_name}
                  </span>
                </td>
                {showDetails && (
                  <>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {alert.baseline_value?.toFixed(2) || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {alert.current_value?.toFixed(2) || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {alert.change_percent !== undefined ? (
                        <span className={clsx(
                          'text-sm font-medium',
                          alert.change_percent > 0 ? 'text-red-600' : 'text-green-600'
                        )}>
                          {alert.change_percent > 0 ? '+' : ''}{alert.change_percent.toFixed(1)}%
                        </span>
                      ) : '-'}
                    </td>
                  </>
                )}
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {new Date(alert.timestamp).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {alerts.length === 0 && (
        <div className="text-center py-12">
          <AlertTriangle className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-500">No drift alerts found</p>
        </div>
      )}
    </div>
  )
}

