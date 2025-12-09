'use client'

import { useState } from 'react'
import Link from 'next/link'
import { CheckCircle, XCircle, AlertTriangle, ChevronUp, ChevronDown, Eye } from 'lucide-react'
import { Run } from '@/lib/api'
import Checkbox from '@/components/ui/Checkbox'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'

interface RunsTableProps {
  runs: Run[]
  showPagination?: boolean
  selectedRuns?: string[]
  onSelectRun?: (runId: string, selected: boolean) => void
  onSelectAll?: (selected: boolean) => void
  onRunClick?: (run: Run) => void
  sortable?: boolean
}

type SortColumn = 'profiled_at' | 'row_count' | 'column_count' | 'status'
type SortOrder = 'asc' | 'desc'

export default function RunsTable({
  runs,
  showPagination = false,
  selectedRuns = [],
  onSelectRun,
  onSelectAll,
  onRunClick,
  sortable = false,
}: RunsTableProps) {
  const [sortColumn, setSortColumn] = useState<SortColumn>('profiled_at')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  const handleSort = (column: SortColumn) => {
    if (!sortable) return
    
    if (sortColumn === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortColumn(column)
      setSortOrder('desc')
    }
  }

  const sortedRuns = [...runs].sort((a, b) => {
    let aValue: string | number | undefined
    let bValue: string | number | undefined

    switch (sortColumn) {
      case 'profiled_at':
        aValue = new Date(a.profiled_at).getTime()
        bValue = new Date(b.profiled_at).getTime()
        break
      case 'row_count':
        aValue = a.row_count ?? 0
        bValue = b.row_count ?? 0
        break
      case 'column_count':
        aValue = a.column_count ?? 0
        bValue = b.column_count ?? 0
        break
      case 'status':
        aValue = a.status
        bValue = b.status
        break
    }

    if (aValue === undefined) return 1
    if (bValue === undefined) return -1

    if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1
    if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1
    return 0
  })

  const allSelected = runs.length > 0 && selectedRuns.length === runs.length
  const someSelected = selectedRuns.length > 0 && selectedRuns.length < runs.length

  const statusIcons = {
    success: <CheckCircle className="w-5 h-5 text-green-600" />,
    completed: <CheckCircle className="w-5 h-5 text-green-600" />,
    failed: <XCircle className="w-5 h-5 text-red-600" />,
    drift_detected: <AlertTriangle className="w-5 h-5 text-orange-600" />,
  }

  const SortIcon = ({ column }: { column: SortColumn }) => {
    if (!sortable || sortColumn !== column) return null
    return sortOrder === 'asc' ? (
      <ChevronUp className="w-4 h-4 inline ml-1" />
    ) : (
      <ChevronDown className="w-4 h-4 inline ml-1" />
    )
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              {onSelectRun && (
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <Checkbox
                    checked={allSelected}
                    indeterminate={someSelected}
                    onChange={(checked) => onSelectAll?.(checked)}
                  />
                </th>
              )}
              <th
                className={`px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${
                  sortable ? 'cursor-pointer hover:bg-gray-100' : ''
                }`}
                onClick={() => handleSort('status')}
              >
                Status
                <SortIcon column="status" />
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Table
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Warehouse
              </th>
              <th
                className={`px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${
                  sortable ? 'cursor-pointer hover:bg-gray-100' : ''
                }`}
                onClick={() => handleSort('row_count')}
              >
                Rows
                <SortIcon column="row_count" />
              </th>
              <th
                className={`px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${
                  sortable ? 'cursor-pointer hover:bg-gray-100' : ''
                }`}
                onClick={() => handleSort('column_count')}
              >
                Columns
                <SortIcon column="column_count" />
              </th>
              <th
                className={`px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${
                  sortable ? 'cursor-pointer hover:bg-gray-100' : ''
                }`}
                onClick={() => handleSort('profiled_at')}
              >
                Profiled At
                <SortIcon column="profiled_at" />
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Drift
              </th>
              {onRunClick && (
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              )}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedRuns.map((run) => (
              <tr
                key={run.run_id}
                className={`hover:bg-gray-50 ${onRunClick ? 'cursor-pointer' : ''}`}
                onClick={() => onRunClick?.(run)}
              >
                {onSelectRun && (
                  <td className="px-6 py-4 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      checked={selectedRuns.includes(run.run_id)}
                      onChange={(e) => {
                        const checked = (e.target as HTMLInputElement).checked
                        onSelectRun(run.run_id, checked)
                      }}
                    />
                  </td>
                )}
                <td className="px-6 py-4 whitespace-nowrap">
                  {statusIcons[run.status as keyof typeof statusIcons] || statusIcons.completed}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <Link
                    href={`/tables/${run.dataset_name}`}
                    className="text-sm font-medium text-primary-600 hover:text-primary-800"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {run.dataset_name}
                  </Link>
                  {run.schema_name && (
                    <p className="text-xs text-gray-500">{run.schema_name}</p>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <Badge color="gray">{run.warehouse_type}</Badge>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {run.row_count?.toLocaleString() || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {run.column_count || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {new Date(run.profiled_at).toLocaleString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {run.has_drift ? (
                    <Badge color="orange">Detected</Badge>
                  ) : (
                    <Badge color="gray">None</Badge>
                  )}
                </td>
                {onRunClick && (
                  <td className="px-6 py-4 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => onRunClick(run)}
                    >
                      <Eye className="w-4 h-4 mr-1" />
                      View Details
                    </Button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {runs.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500">No runs found</p>
        </div>
      )}

      {showPagination && runs.length > 0 && (
        <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
          <p className="text-sm text-gray-700">
            Showing <span className="font-medium">{runs.length}</span> results
          </p>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" disabled>
              Previous
            </Button>
            <Button variant="secondary" size="sm" disabled>
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

