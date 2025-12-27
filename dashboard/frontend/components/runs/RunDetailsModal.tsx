'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, AlertCircle, CheckCircle, XCircle } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Tabs } from '@/components/ui/Tabs'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { fetchRunDetails, retryRun, Run } from '@/lib/api'

interface RunDetailsModalProps {
  run: Run | null
  isOpen: boolean
  onClose: () => void
}

export default function RunDetailsModal({ run, isOpen, onClose }: RunDetailsModalProps) {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('overview')

  const { data: runDetails, isLoading, error } = useQuery({
    queryKey: ['run-details', run?.run_id],
    queryFn: () => fetchRunDetails(run!.run_id),
    enabled: isOpen && !!run,
  })

  const retryMutation = useMutation({
    mutationFn: retryRun,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runs'] })
      queryClient.invalidateQueries({ queryKey: ['run-details', run?.run_id] })
    },
  })

  const handleRetry = () => {
    if (run && run.status === 'failed') {
      retryMutation.mutate(run.run_id)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  const getStatusIcon = (status?: string) => {
    if (!status) return <AlertCircle className="w-5 h-5 text-gray-600" />
    switch (status.toLowerCase()) {
      case 'success':
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-600" />
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-600" />
      case 'drift_detected':
        return <AlertCircle className="w-5 h-5 text-orange-600" />
      default:
        return <AlertCircle className="w-5 h-5 text-gray-600" />
    }
  }


  if (!run) return null

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Run Details: ${run.dataset_name}`}
      size="xl"
    >
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner />
        </div>
      ) : error ? (
        <div className="py-12 text-center text-red-600">
          Failed to load run details
        </div>
      ) : runDetails ? (
        <div className="space-y-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-gray-500">Run ID</div>
                  <div className="font-mono text-sm">{runDetails.run_id}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Status</div>
                  <div className="flex items-center gap-2">
                    {getStatusIcon(run.status)}
                    <Badge variant={
                      !run.status ? 'default' :
                      run.status.toLowerCase() === 'success' || run.status.toLowerCase() === 'completed' ? 'success' :
                      run.status.toLowerCase() === 'failed' ? 'error' :
                      run.status.toLowerCase() === 'drift_detected' ? 'warning' :
                      'default'
                    }>{run.status || 'unknown'}</Badge>
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Table</div>
                  <div className="font-medium">{runDetails.dataset_name}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Schema</div>
                  <div className="font-medium">{runDetails.schema_name || 'N/A'}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Warehouse</div>
                  <div className="font-medium capitalize">{runDetails.warehouse_type}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Environment</div>
                  <div className="font-medium">{runDetails.environment}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Profiled At</div>
                  <div className="font-medium">{formatDate(runDetails.profiled_at)}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Row Count</div>
                  <div className="font-medium">{runDetails.row_count?.toLocaleString() || '—'}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Column Count</div>
                  <div className="font-medium">{runDetails.column_count}</div>
                </div>
              </div>
            </div>
          )}

          {/* Column Metrics Tab */}
          {activeTab === 'metrics' && runDetails.columns && runDetails.columns.length > 0 && (
            <div className="space-y-4">
              {runDetails.columns.map((column, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4">
                  <h4 className="font-medium text-gray-900 mb-3">
                    {column.column_name}
                    {column.column_type && (
                      <span className="ml-2 text-sm font-normal text-gray-500">({column.column_type})</span>
                    )}
                  </h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    {column.null_count !== undefined && (
                      <div>
                        <div className="text-gray-500">Null Count</div>
                        <div className="font-medium">{column.null_count?.toLocaleString() || '0'}</div>
                      </div>
                    )}
                    {column.null_percent !== undefined && (
                      <div>
                        <div className="text-gray-500">Null %</div>
                        <div className="font-medium">{column.null_percent?.toFixed(2) || '0.00'}%</div>
                      </div>
                    )}
                    {column.distinct_count !== undefined && (
                      <div>
                        <div className="text-gray-500">Distinct Count</div>
                        <div className="font-medium">{column.distinct_count?.toLocaleString() || '0'}</div>
                      </div>
                    )}
                    {column.distinct_percent !== undefined && (
                      <div>
                        <div className="text-gray-500">Distinct %</div>
                        <div className="font-medium">{column.distinct_percent.toFixed(2)}%</div>
                      </div>
                    )}
                    {column.min_value !== undefined && (
                      <div>
                        <div className="text-gray-500">Min</div>
                        <div className="font-medium">{String(column.min_value)}</div>
                      </div>
                    )}
                    {column.max_value !== undefined && (
                      <div>
                        <div className="text-gray-500">Max</div>
                        <div className="font-medium">{String(column.max_value)}</div>
                      </div>
                    )}
                    {column.mean !== undefined && (
                      <div>
                        <div className="text-gray-500">Mean</div>
                        <div className="font-medium">{column.mean.toFixed(2)}</div>
                      </div>
                    )}
                    {column.stddev !== undefined && (
                      <div>
                        <div className="text-gray-500">Std Dev</div>
                        <div className="font-medium">{column.stddev.toFixed(2)}</div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Error Logs Tab */}
          {activeTab === 'errors' && (
            <div className="space-y-4">
              {run.status === 'failed' ? (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
                    <div className="flex-1">
                      <div className="font-medium text-red-900 mb-2">Run Failed</div>
                      <div className="text-sm text-red-700 whitespace-pre-wrap">
                        {runDetails.error_message || 'No error details available'}
                      </div>
                      {runDetails.error_logs && runDetails.error_logs.length > 0 && (
                        <div className="mt-4">
                          <div className="font-medium text-red-900 mb-2">Error Logs:</div>
                          <div className="bg-red-100 rounded p-3">
                            <pre className="text-xs text-red-800 whitespace-pre-wrap">
                              {runDetails.error_logs.join('\n')}
                            </pre>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  No errors. Run completed successfully.
                </div>
              )}
            </div>
          )}

          {/* Tabs */}
          <div className="border-t border-gray-200 pt-4">
            <Tabs
              activeTab={activeTab}
              onChange={(tabId) => setActiveTab(tabId)}
              tabs={[
                { id: 'overview', label: 'Overview' },
                { id: 'metrics', label: 'Column Metrics' },
                { id: 'errors', label: 'Error Logs' },
              ]}
            />
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 border-t border-gray-200 pt-4">
            {run.status === 'failed' && (
              <Button
                variant="primary"
                onClick={handleRetry}
                disabled={retryMutation.isPending}
              >
                {retryMutation.isPending ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Retrying...
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Retry Run
                  </>
                )}
              </Button>
            )}
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      ) : null}
    </Modal>
  )
}

