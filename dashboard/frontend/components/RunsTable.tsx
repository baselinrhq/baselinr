import Link from 'next/link'
import { CheckCircle, XCircle, AlertTriangle } from 'lucide-react'

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
  success: <CheckCircle className="w-5 h-5 text-green-600" />,
  completed: <CheckCircle className="w-5 h-5 text-green-600" />,
  failed: <XCircle className="w-5 h-5 text-red-600" />,
  drift_detected: <AlertTriangle className="w-5 h-5 text-orange-600" />,
}

export default function RunsTable({ runs, showPagination = false }: RunsTableProps) {
  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Table
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Warehouse
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Rows
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Columns
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Profiled At
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Drift
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {runs.map((run) => (
              <tr key={run.run_id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  {statusIcons[run.status as keyof typeof statusIcons] || statusIcons.completed}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <Link 
                    href={`/tables/${run.dataset_name}`}
                    className="text-sm font-medium text-primary-600 hover:text-primary-800"
                  >
                    {run.dataset_name}
                  </Link>
                  {run.schema_name && (
                    <p className="text-xs text-gray-500">{run.schema_name}</p>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded capitalize">
                    {run.warehouse_type}
                  </span>
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
                    <span className="px-2 py-1 text-xs font-medium bg-orange-100 text-orange-800 rounded">
                      Detected
                    </span>
                  ) : (
                    <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-600 rounded">
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
            <button className="px-3 py-1 border border-gray-300 rounded text-sm hover:bg-gray-50">
              Previous
            </button>
            <button className="px-3 py-1 border border-gray-300 rounded text-sm hover:bg-gray-50">
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

