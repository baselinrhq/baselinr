'use client'

import Link from 'next/link'
import { Search, ChevronRight } from 'lucide-react'
import clsx from 'clsx'
import { Badge } from '@/components/ui/Badge'
import type { RCAListItem } from '@/types/rca'

interface RCAListProps {
  items: RCAListItem[]
  onRowClick?: (anomalyId: string) => void
}

const statusColors = {
  analyzed: 'success',
  pending: 'warning',
  dismissed: 'default',
} as const

export default function RCAList({ items, onRowClick }: RCAListProps) {
  if (items.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow border border-gray-200 p-12">
        <div className="text-center">
          <Search className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 text-lg font-medium">No RCA results found</p>
          <p className="text-gray-500 text-sm mt-2">
            Try adjusting your filters or trigger a new analysis
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Anomaly ID
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
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Causes
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Top Confidence
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Analyzed At
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {items.map((item) => {
              const tableName = item.schema_name
                ? `${item.schema_name}.${item.table_name}`
                : item.table_name

              return (
                <tr
                  key={item.anomaly_id}
                  className={clsx(
                    'hover:bg-gray-50 transition-colors',
                    onRowClick && 'cursor-pointer'
                  )}
                  onClick={() => onRowClick?.(item.anomaly_id)}
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Badge
                      variant={statusColors[item.rca_status] || 'default'}
                      size="sm"
                    >
                      {item.rca_status}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm font-mono text-gray-900">
                      {item.anomaly_id.slice(0, 8)}...
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Link
                      href={`/tables/${item.table_name}`}
                      className="text-sm font-medium text-primary-600 hover:text-primary-800"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {tableName}
                    </Link>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {item.column_name || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {item.metric_name ? (
                      <span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                        {item.metric_name}
                      </span>
                    ) : (
                      '-'
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <span className="font-medium">{item.num_causes}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {item.top_cause ? (
                      <div className="flex items-center gap-2">
                        <span className="font-medium">
                          {(item.top_cause.confidence_score * 100).toFixed(0)}%
                        </span>
                        <span className="text-xs text-gray-500">
                          {item.top_cause.cause_type}
                        </span>
                      </div>
                    ) : (
                      '-'
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(item.analyzed_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <button
                      className="text-primary-600 hover:text-primary-800 flex items-center gap-1"
                      onClick={(e) => {
                        e.stopPropagation()
                        onRowClick?.(item.anomaly_id)
                      }}
                    >
                      View
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

