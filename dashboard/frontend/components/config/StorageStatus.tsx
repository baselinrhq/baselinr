'use client'

import { RefreshCw, CheckCircle, XCircle, AlertCircle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { StorageStatusResponse } from '@/types/config'

export interface StorageStatusProps {
  status?: StorageStatusResponse
  isLoading?: boolean
  error?: string | null
  onRefresh?: () => void
}

export function StorageStatus({
  status,
  isLoading = false,
  error,
  onRefresh,
}: StorageStatusProps) {
  const getConnectionStatusBadge = () => {
    if (!status) {
      return <Badge variant="default">Unknown</Badge>
    }

    switch (status.connection_status) {
      case 'connected':
        return (
          <Badge variant="success" icon={<CheckCircle className="w-3 h-3" />}>
            Connected
          </Badge>
        )
      case 'disconnected':
        return (
          <Badge variant="error" icon={<XCircle className="w-3 h-3" />}>
            Disconnected
          </Badge>
        )
      case 'error':
        return (
          <Badge variant="error" icon={<AlertCircle className="w-3 h-3" />}>
            Error
          </Badge>
        )
      default:
        return <Badge variant="default">Unknown</Badge>
    }
  }

  const getTableStatusBadge = (exists: boolean) => {
    return exists ? (
      <Badge variant="success" icon={<CheckCircle className="w-3 h-3" />}>
        Exists
      </Badge>
    ) : (
      <Badge variant="warning" icon={<XCircle className="w-3 h-3" />}>
        Missing
      </Badge>
    )
  }

  const formatLastChecked = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      return date.toLocaleString()
    } catch {
      return timestamp
    }
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Storage Status</h3>
        {onRefresh && (
          <Button
            variant="secondary"
            size="sm"
            onClick={onRefresh}
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Checking...
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh
              </>
            )}
          </Button>
        )}
      </div>

      {isLoading && !status && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
          <span className="ml-2 text-sm text-slate-400">Checking status...</span>
        </div>
      )}

      {error && (
        <div className="py-4">
          <div className="flex items-center gap-2 text-rose-400">
            <AlertCircle className="w-5 h-5" />
            <span className="text-sm font-medium">Error checking status</span>
          </div>
          <p className="mt-1 text-sm text-rose-300">{error}</p>
        </div>
      )}

      {status && !error && (
        <div className="space-y-4">
          {/* Connection Status */}
          <div className="flex items-center justify-between py-2 border-b border-surface-700/50">
            <div>
              <p className="text-sm font-medium text-slate-300">Connection</p>
              {status.connection_error && (
                <p className="mt-1 text-xs text-rose-400">{status.connection_error}</p>
              )}
            </div>
            {getConnectionStatusBadge()}
          </div>

          {/* Results Table Status */}
          <div className="flex items-center justify-between py-2 border-b border-surface-700/50">
            <div>
              <p className="text-sm font-medium text-slate-300">Results Table</p>
              <p className="mt-0.5 text-xs text-slate-400">
                Stores profiling results
              </p>
            </div>
            {getTableStatusBadge(status.results_table_exists)}
          </div>

          {/* Runs Table Status */}
          <div className="flex items-center justify-between py-2 border-b border-surface-700/50">
            <div>
              <p className="text-sm font-medium text-slate-300">Runs Table</p>
              <p className="mt-0.5 text-xs text-slate-400">
                Stores run metadata
              </p>
            </div>
            {getTableStatusBadge(status.runs_table_exists)}
          </div>

          {/* Last Checked */}
          {status.last_checked && (
            <div className="pt-2">
              <p className="text-xs text-slate-400">
                Last checked: {formatLastChecked(status.last_checked)}
              </p>
            </div>
          )}
        </div>
      )}

      {!status && !isLoading && !error && (
        <div className="py-4 text-center">
          <p className="text-sm text-slate-400">No status information available</p>
          <p className="mt-1 text-xs text-slate-500">
            Click Refresh to check storage status
          </p>
        </div>
      )}
    </Card>
  )
}

export default StorageStatus

