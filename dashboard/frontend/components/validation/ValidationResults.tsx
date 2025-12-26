'use client'

import Link from 'next/link'
import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import type { ValidationResult } from '@/types/validation'
import clsx from 'clsx'

interface ValidationResultsProps {
  results: ValidationResult[]
  onRowClick?: (resultId: number) => void
  page?: number
  pageSize?: number
  total?: number
  onPageChange?: (page: number) => void
  isLoading?: boolean
}

const severityColors = {
  low: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  medium: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  high: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
}

const ruleTypeLabels: Record<string, string> = {
  format: 'Format',
  range: 'Range',
  enum: 'Enum',
  not_null: 'Not Null',
  unique: 'Unique',
  referential: 'Referential',
}

export default function ValidationResults({
  results,
  onRowClick,
  page = 1,
  pageSize = 50,
  total = 0,
  onPageChange,
  isLoading = false,
}: ValidationResultsProps) {
  const totalPages = Math.ceil(total / pageSize)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="glass-card rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-surface-800/60">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Table
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Column
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Rule Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Failed / Total
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Failure Rate
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Severity
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Validated At
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-700/50">
            {results.map((result) => (
              <tr
                key={result.id}
                className={clsx(
                  'hover:bg-surface-700/30 transition-colors',
                  onRowClick && 'cursor-pointer'
                )}
                onClick={() => onRowClick?.(result.id)}
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  {result.passed ? (
                    <Badge variant="success" icon={<CheckCircle className="w-3 h-3" />}>
                      Pass
                    </Badge>
                  ) : (
                    <Badge variant="error" icon={<XCircle className="w-3 h-3" />}>
                      Fail
                    </Badge>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <Link
                    href={`/tables/${encodeURIComponent(result.table_name)}`}
                    className="text-sm font-medium text-cyan-400 hover:text-cyan-300"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {result.table_name}
                  </Link>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                  {result.column_name || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
                  <span className="font-mono text-xs bg-surface-700/50 px-2 py-1 rounded">
                    {ruleTypeLabels[result.rule_type] || result.rule_type}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                  {result.total_rows !== undefined && result.failed_rows !== undefined ? (
                    <span>
                      <span className={clsx('font-medium', result.failed_rows > 0 && 'text-rose-400')}>
                        {result.failed_rows?.toLocaleString() || '0'}
                      </span>
                      {' / '}
                      <span className="text-slate-400">{result.total_rows?.toLocaleString() || '0'}</span>
                    </span>
                  ) : (
                    '-'
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {result.failure_rate !== undefined && result.failure_rate !== null ? (
                    <span className={clsx(
                      'text-sm font-medium',
                      result.failure_rate > 0 ? 'text-rose-400' : 'text-emerald-400'
                    )}>
                      {result.failure_rate.toFixed(2)}%
                    </span>
                  ) : (
                    '-'
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {result.severity ? (
                    <span className={clsx(
                      'px-2 py-1 text-xs font-medium rounded border capitalize',
                      severityColors[result.severity as keyof typeof severityColors] || severityColors.low
                    )}>
                      {result.severity}
                    </span>
                  ) : (
                    '-'
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-400">
                  {new Date(result.validated_at).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {results.length === 0 && (
        <div className="text-center py-12">
          <AlertTriangle className="w-12 h-12 text-slate-500 mx-auto mb-3" />
          <p className="text-slate-400">No validation results found</p>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && onPageChange && (
        <div className="px-6 py-4 border-t border-surface-700/50 flex items-center justify-between">
          <div className="text-sm text-slate-400">
            Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total} results
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
            >
              Previous
            </Button>
            <span className="text-sm text-slate-400">
              Page {page} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

