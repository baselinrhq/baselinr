'use client'

import { RefreshCw, Loader2, AlertCircle } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { TableInfo } from '@/lib/api/tables'

export interface TablePreviewProps {
  tables: TableInfo[]
  isLoading?: boolean
  error?: string | null
  onRefresh?: () => void
}

export function TablePreview({ tables, isLoading, error, onRefresh }: TablePreviewProps) {
  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A'
    try {
      return new Date(dateString).toLocaleDateString()
    } catch {
      return dateString
    }
  }

  const formatNumber = (num?: number) => {
    if (num === undefined || num === null) return 'N/A'
    return num.toLocaleString()
  }

  if (isLoading) {
    return (
      <Card>
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-cyan-400" />
          <span className="ml-2 text-sm text-slate-400">Loading tables...</span>
        </div>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <div className="py-6">
          <div className="flex items-center text-rose-400 mb-4">
            <AlertCircle className="h-5 w-5 mr-2" />
            <span className="font-medium">Error loading preview</span>
          </div>
          <p className="text-sm text-slate-400 mb-4">{error}</p>
          {onRefresh && (
            <Button variant="outline" size="sm" onClick={onRefresh}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          )}
        </div>
      </Card>
    )
  }

  if (tables.length === 0) {
    return (
      <Card>
        <div className="py-6 text-center">
          <p className="text-sm text-slate-400">No tables found matching this pattern.</p>
          {onRefresh && (
            <Button variant="outline" size="sm" onClick={onRefresh} className="mt-4">
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          )}
        </div>
      </Card>
    )
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="text-sm font-medium text-white">
            Matching Tables ({tables.length})
          </h4>
        </div>
        {onRefresh && (
          <Button variant="outline" size="sm" onClick={onRefresh}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        )}
      </div>
      
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-surface-700/50">
          <thead className="bg-surface-800/60">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Schema
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Table
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Type
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Rows
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Last Modified
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-700/50">
            {tables.map((table, index) => (
              <tr key={`${table.schema}.${table.table}-${index}`} className="hover:bg-surface-800/30">
                <td className="px-4 py-3 whitespace-nowrap text-sm text-white">
                  {table.schema}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-white">
                  {table.table}
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  {table.table_type ? (
                    <Badge variant="default" size="sm">
                      {table.table_type}
                    </Badge>
                  ) : (
                    <span className="text-sm text-slate-400">-</span>
                  )}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-400">
                  {formatNumber(table.row_count)}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-400">
                  {formatDate(table.last_modified)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

