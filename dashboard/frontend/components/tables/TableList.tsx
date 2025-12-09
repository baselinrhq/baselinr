'use client'

import Link from 'next/link'
import { ArrowUpDown, ArrowUp, ArrowDown, AlertTriangle, CheckCircle2, XCircle } from 'lucide-react'
import Checkbox from '@/components/ui/Checkbox'
import { Badge } from '@/components/ui'
import { TableListItem } from '@/lib/api'
import { formatDate } from '@/lib/utils'

interface TableListProps {
  tables: TableListItem[]
  selectedTables: Set<string>
  onSelectTable: (tableName: string, selected: boolean) => void
  onSelectAll: (selected: boolean) => void
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  onSort: (column: string) => void
}

export default function TableList({
  tables,
  selectedTables,
  onSelectTable,
  onSelectAll,
  sortBy = 'table_name',
  sortOrder = 'asc',
  onSort
}: TableListProps) {
  const allSelected = tables.length > 0 && tables.every(t => selectedTables.has(t.table_name))
  const someSelected = !allSelected && tables.some(t => selectedTables.has(t.table_name))

  const handleSort = (column: string) => {
    onSort(column)
  }

  const getSortIcon = (column: string) => {
    if (sortBy !== column) {
      return <ArrowUpDown className="w-4 h-4 text-gray-400" />
    }
    return sortOrder === 'asc' 
      ? <ArrowUp className="w-4 h-4 text-primary-600" />
      : <ArrowDown className="w-4 h-4 text-primary-600" />
  }

  const formatTableName = (table: TableListItem) => {
    if (table.schema_name) {
      return `${table.schema_name}.${table.table_name}`
    }
    return table.table_name
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left">
                <Checkbox
                  checked={allSelected}
                  ref={(el) => {
                    if (el) {
                      (el as HTMLInputElement).indeterminate = someSelected
                    }
                  }}
                  onChange={(e) => onSelectAll(e.target.checked)}
                  aria-label="Select all tables"
                />
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('table_name')}
                  className="flex items-center gap-2 hover:text-gray-700"
                >
                  Table Name
                  {getSortIcon('table_name')}
                </button>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Warehouse
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('last_profiled')}
                  className="flex items-center gap-2 hover:text-gray-700"
                >
                  Last Profiled
                  {getSortIcon('last_profiled')}
                </button>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('row_count')}
                  className="flex items-center gap-2 hover:text-gray-700"
                >
                  Rows
                  {getSortIcon('row_count')}
                </button>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Columns
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Runs
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('drift_count')}
                  className="flex items-center gap-2 hover:text-gray-700"
                >
                  Drift Events
                  {getSortIcon('drift_count')}
                </button>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Validation
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {tables.length === 0 ? (
              <tr>
                <td colSpan={10} className="px-6 py-12 text-center text-gray-500">
                  No tables found. Try adjusting your filters.
                </td>
              </tr>
            ) : (
              tables.map((table) => {
                const isSelected = selectedTables.has(table.table_name)
                const tableKey = table.schema_name 
                  ? `${table.schema_name}.${table.table_name}`
                  : table.table_name

                return (
                  <tr
                    key={tableKey}
                    className={`hover:bg-gray-50 ${isSelected ? 'bg-primary-50' : ''}`}
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Checkbox
                        checked={isSelected}
                        onChange={(e) => onSelectTable(table.table_name, e.target.checked)}
                        onClick={(e) => e.stopPropagation()}
                        aria-label={`Select ${table.table_name}`}
                      />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link
                        href={`/tables/${encodeURIComponent(table.table_name)}${table.schema_name ? `?schema=${encodeURIComponent(table.schema_name)}` : ''}`}
                        className="text-sm font-medium text-primary-600 hover:text-primary-800"
                      >
                        {formatTableName(table)}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Badge variant="default">
                        {table.warehouse_type}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {table.last_profiled 
                        ? formatDate(table.last_profiled)
                        : 'Never'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {table.row_count?.toLocaleString() || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {table.column_count || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {table.total_runs}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {table.drift_count > 0 ? (
                        <Badge variant="warning">
                          {table.drift_count}
                        </Badge>
                      ) : (
                        <span className="text-sm text-gray-500">0</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {table.validation_pass_rate !== null && table.validation_pass_rate !== undefined ? (
                        <div className="flex items-center gap-2">
                          {table.validation_pass_rate >= 95 ? (
                            <CheckCircle2 className="w-4 h-4 text-green-600" />
                          ) : table.validation_pass_rate >= 80 ? (
                            <AlertTriangle className="w-4 h-4 text-yellow-600" />
                          ) : (
                            <XCircle className="w-4 h-4 text-red-600" />
                          )}
                          <span className="text-sm text-gray-900">
                            {table.validation_pass_rate.toFixed(1)}%
                          </span>
                        </div>
                      ) : (
                        <span className="text-sm text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        {table.has_recent_drift && (
                          <Badge variant="warning" size="sm">
                            Recent Drift
                          </Badge>
                        )}
                        {table.has_failed_validations && (
                          <Badge variant="error" size="sm">
                            Failed Validations
                          </Badge>
                        )}
                        {!table.has_recent_drift && !table.has_failed_validations && (
                          <Badge variant="success" size="sm">
                            Healthy
                          </Badge>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

