'use client'

import { useState } from 'react'
import Link from 'next/link'
import { CheckCircle, XCircle, AlertTriangle, ChevronUp, ChevronDown, Eye, Activity } from 'lucide-react'
import { Run } from '@/lib/api'
import Checkbox from '@/components/ui/Checkbox'
import { Button } from '@/components/ui/Button'
import clsx from 'clsx'

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
    success: <CheckCircle className="w-5 h-5 text-success-400" />,
    completed: <CheckCircle className="w-5 h-5 text-success-400" />,
    failed: <XCircle className="w-5 h-5 text-danger-400" />,
    drift_detected: <AlertTriangle className="w-5 h-5 text-warning-400" />,
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
          <thead className="bg-surface-800/50 border-b border-surface-700/50">
            <tr>
              {onSelectRun && (
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  <Checkbox
                    checked={allSelected}
                    indeterminate={someSelected}
                    onChange={(e) => onSelectAll?.(e.target.checked)}
                  />
                </th>
              )}
              <th
                className={clsx(
                  'px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider',
                  sortable && 'cursor-pointer hover:bg-surface-700/50 transition-colors'
                )}
                onClick={() => handleSort('status')}
              >
                Status
                <SortIcon column="status" />
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Table
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Warehouse
              </th>
              <th
                className={clsx(
                  'px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider',
                  sortable && 'cursor-pointer hover:bg-surface-700/50 transition-colors'
                )}
                onClick={() => handleSort('row_count')}
              >
                Rows
                <SortIcon column="row_count" />
              </th>
              <th
                className={clsx(
                  'px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider',
                  sortable && 'cursor-pointer hover:bg-surface-700/50 transition-colors'
                )}
                onClick={() => handleSort('column_count')}
              >
                Columns
                <SortIcon column="column_count" />
              </th>
              <th
                className={clsx(
                  'px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider',
                  sortable && 'cursor-pointer hover:bg-surface-700/50 transition-colors'
                )}
                onClick={() => handleSort('profiled_at')}
              >
                Profiled At
                <SortIcon column="profiled_at" />
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Drift
              </th>
              {onRunClick && (
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Actions
                </th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-700/50">
            {sortedRuns.map((run) => (
              <tr
                key={run.run_id}
                className={clsx(
                  'transition-colors hover:bg-surface-800/50',
                  onRunClick && 'cursor-pointer'
                )}
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
                    href={`/tables/${encodeURIComponent(run.dataset_name)}`}
                    className="text-sm font-medium text-accent-400 hover:text-accent-300 transition-colors"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {run.dataset_name}
                  </Link>
                  {run.schema_name && (
                    <p className="text-xs text-slate-500 mt-0.5">{run.schema_name}</p>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="px-2.5 py-1 text-xs font-medium bg-surface-700/50 text-slate-300 rounded-full capitalize">
                    {run.warehouse_type}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300 font-mono">
                  {run.row_count?.toLocaleString() || <span className="text-slate-600">—</span>}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300 font-mono">
                  {run.column_count || <span className="text-slate-600">—</span>}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-400">
                  {new Date(run.profiled_at).toLocaleString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {run.has_drift ? (
                    <span className="px-2.5 py-1 text-xs font-medium bg-warning-500/20 text-warning-400 rounded-full">
                      Detected
                    </span>
                  ) : (
                    <span className="px-2.5 py-1 text-xs font-medium bg-surface-700/50 text-slate-500 rounded-full">
                      None
                    </span>
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
        <div className="text-center py-16">
          <div className="w-16 h-16 rounded-full bg-surface-800 flex items-center justify-center mx-auto mb-4">
            <Activity className="w-8 h-8 text-slate-600" />
          </div>
          <p className="text-slate-400 font-medium">No runs found</p>
          <p className="text-sm text-slate-500 mt-1">Adjust your filters or run a new profile</p>
        </div>
      )}

      {showPagination && runs.length > 0 && (
        <div className="px-6 py-4 border-t border-surface-700/50 flex items-center justify-between">
          <p className="text-sm text-slate-400">
            Showing <span className="font-medium text-slate-300">{runs.length}</span> results
          </p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled>
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled>
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
