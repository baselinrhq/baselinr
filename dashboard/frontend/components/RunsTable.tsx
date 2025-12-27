import Link from 'next/link'
import { CheckCircle, XCircle, AlertTriangle, Activity } from 'lucide-react'

interface Run {
  run_id: string
  dataset_name: string
  schema_name?: string
  warehouse_type: string
  profiled_at: string
  status: string
  row_count?: number
  column_count?: number
  has_drift: boolean
}

interface RunsTableProps {
  runs: Run[]
  showPagination?: boolean
}

const statusIcons = {
  success: <CheckCircle className="w-5 h-5 text-success-400" />,
  completed: <CheckCircle className="w-5 h-5 text-success-400" />,
  failed: <XCircle className="w-5 h-5 text-danger-400" />,
  drift_detected: <AlertTriangle className="w-5 h-5 text-warning-400" />,
}

export default function RunsTable({ runs, showPagination = false }: RunsTableProps) {
  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-surface-800/50 border-b border-surface-700/50">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Table
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Warehouse
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Rows
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Columns
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Profiled At
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Drift
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-700/50">
            {runs.map((run) => (
              <tr key={run.run_id} className="hover:bg-surface-800/50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap">
                  {statusIcons[run.status as keyof typeof statusIcons] || statusIcons.completed}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <Link 
                    href={`/tables/${encodeURIComponent(run.dataset_name)}`}
                    className="text-sm font-medium text-accent-400 hover:text-accent-300 transition-colors"
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
          <p className="text-sm text-slate-500 mt-1">Profiling runs will appear here</p>
        </div>
      )}

      {showPagination && runs.length > 0 && (
        <div className="px-6 py-4 border-t border-surface-700/50 flex items-center justify-between">
          <p className="text-sm text-slate-400">
            Showing <span className="font-medium text-slate-300">{runs.length}</span> results
          </p>
          <div className="flex gap-2">
            <button className="px-3 py-1.5 border border-surface-600 rounded-lg text-sm text-slate-400 hover:bg-surface-800 hover:text-slate-300 transition-colors">
              Previous
            </button>
            <button className="px-3 py-1.5 border border-surface-600 rounded-lg text-sm text-slate-400 hover:bg-surface-800 hover:text-slate-300 transition-colors">
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
