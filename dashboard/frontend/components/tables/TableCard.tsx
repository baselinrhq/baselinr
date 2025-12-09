'use client'

import Link from 'next/link'
import { AlertTriangle, CheckCircle2, XCircle, Settings, Eye } from 'lucide-react'
import { Badge } from '@/components/ui'
import { Button } from '@/components/ui'
import { TableListItem } from '@/lib/api'
import { formatDate } from '@/lib/utils'

interface TableCardProps {
  table: TableListItem
}

export default function TableCard({ table }: TableCardProps) {
  const formatTableName = () => {
    if (table.schema_name) {
      return `${table.schema_name}.${table.table_name}`
    }
    return table.table_name
  }

  const getValidationStatus = () => {
    if (table.validation_pass_rate === null || table.validation_pass_rate === undefined) {
      return null
    }
    if (table.validation_pass_rate >= 95) {
      return { icon: CheckCircle2, color: 'text-green-600', label: 'Passing' }
    }
    if (table.validation_pass_rate >= 80) {
      return { icon: AlertTriangle, color: 'text-yellow-600', label: 'Warning' }
    }
    return { icon: XCircle, color: 'text-red-600', label: 'Failing' }
  }

  const validationStatus = getValidationStatus()

  return (
    <div className="bg-white rounded-lg shadow hover:shadow-md transition-shadow border border-gray-200">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <Link
              href={`/tables/${encodeURIComponent(table.table_name)}${table.schema_name ? `?schema=${encodeURIComponent(table.schema_name)}` : ''}`}
              className="text-lg font-semibold text-gray-900 hover:text-primary-600 transition-colors"
            >
              {formatTableName()}
            </Link>
            {table.schema_name && (
              <p className="text-sm text-gray-500 mt-1">{table.schema_name}</p>
            )}
          </div>
          <Badge variant="default" size="sm">
            {table.warehouse_type}
          </Badge>
        </div>

        {/* Status Badges */}
        <div className="flex flex-wrap gap-2 mb-4">
          {table.has_recent_drift && (
            <Badge variant="warning" size="sm">
              <AlertTriangle className="w-3 h-3 mr-1" />
              Recent Drift
            </Badge>
          )}
          {table.has_failed_validations && (
            <Badge variant="error" size="sm">
              <XCircle className="w-3 h-3 mr-1" />
              Failed Validations
            </Badge>
          )}
          {!table.has_recent_drift && !table.has_failed_validations && (
            <Badge variant="success" size="sm">
              <CheckCircle2 className="w-3 h-3 mr-1" />
              Healthy
            </Badge>
          )}
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-xs text-gray-500 mb-1">Rows</p>
            <p className="text-sm font-medium text-gray-900">
              {table.row_count?.toLocaleString() || '-'}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Columns</p>
            <p className="text-sm font-medium text-gray-900">
              {table.column_count || '-'}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Runs</p>
            <p className="text-sm font-medium text-gray-900">
              {table.total_runs}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Drift Events</p>
            <p className="text-sm font-medium text-gray-900">
              {table.drift_count > 0 ? (
                <span className="text-orange-600">{table.drift_count}</span>
              ) : (
                '0'
              )}
            </p>
          </div>
        </div>

        {/* Validation */}
        {validationStatus && (
          <div className="mb-4 p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <validationStatus.icon className={`w-4 h-4 ${validationStatus.color}`} />
                <span className="text-sm font-medium text-gray-700">Validation</span>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold text-gray-900">
                  {table.validation_pass_rate.toFixed(1)}%
                </p>
                <p className="text-xs text-gray-500">{validationStatus.label}</p>
              </div>
            </div>
          </div>
        )}

        {/* Last Profiled */}
        <div className="mb-4">
          <p className="text-xs text-gray-500 mb-1">Last Profiled</p>
          <p className="text-sm text-gray-900">
            {table.last_profiled 
              ? formatDate(table.last_profiled)
              : 'Never'}
          </p>
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-4 border-t border-gray-200">
          <Button
            variant="primary"
            size="sm"
            asChild
            className="flex-1"
          >
            <Link href={`/tables/${encodeURIComponent(table.table_name)}${table.schema_name ? `?schema=${encodeURIComponent(table.schema_name)}` : ''}`}>
              <Eye className="w-4 h-4 mr-2" />
              View Details
            </Link>
          </Button>
          <Button
            variant="outline"
            size="sm"
            asChild
          >
            <Link href={`/config/tables?table=${encodeURIComponent(table.table_name)}`}>
              <Settings className="w-4 h-4" />
            </Link>
          </Button>
        </div>
      </div>
    </div>
  )
}

