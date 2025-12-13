'use client'

import { useQuery } from '@tanstack/react-query'
import { Clock, User, FileText, GitCompare, RotateCcw, Eye, AlertCircle } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { getConfigHistory, ConfigError } from '@/lib/api/config'
// Format date relative to now
function formatTimeAgo(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`
  if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`
  if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`
  return date.toLocaleDateString()
}

export interface ConfigHistoryProps {
  onVersionSelect?: (versionId: string) => void
  onCompare?: (versionId1: string, versionId2?: string) => void
  onRestore?: (versionId: string) => void
}

export function ConfigHistory({
  onVersionSelect,
  onCompare,
  onRestore,
}: ConfigHistoryProps) {
  const {
    data: historyData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['config-history'],
    queryFn: getConfigHistory,
    retry: false,
  })

  const handleView = (versionId: string) => {
    if (onVersionSelect) {
      onVersionSelect(versionId)
    }
  }

  const handleCompare = (versionId: string) => {
    if (onCompare) {
      onCompare(versionId)
    }
  }

  const handleRestore = (versionId: string) => {
    if (onRestore) {
      onRestore(versionId)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
        <span className="ml-3 text-sm text-slate-400">Loading history...</span>
      </div>
    )
  }

  if (error) {
    const errorMessage = error instanceof ConfigError
      ? error.message
      : 'Failed to load configuration history'
    
    return (
      <div className="glass-card border-rose-500/30 bg-rose-500/10 p-4">
        <div className="flex items-center gap-2 text-rose-300">
          <AlertCircle className="w-5 h-5" />
          <span className="font-medium">Error loading history</span>
        </div>
        <p className="mt-1 text-sm text-rose-200">{errorMessage}</p>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => refetch()}
          className="mt-3"
        >
          Retry
        </Button>
      </div>
    )
  }

  const versions = historyData?.versions || []

  if (versions.length === 0) {
    return (
      <div className="text-center py-12">
        <Clock className="w-12 h-12 text-slate-500 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-white mb-2">No Configuration History</h3>
        <p className="text-sm text-slate-400">
          Configuration versions will appear here once you start making changes.
        </p>
      </div>
    )
  }

  // Get the most recent version (first in the list) as current
  const currentVersionId = versions[0]?.version_id

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">
          Configuration History ({versions.length} version{versions.length !== 1 ? 's' : ''})
        </h3>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => refetch()}
        >
          Refresh
        </Button>
      </div>

      <div className="space-y-3">
        {versions.map((version) => {
          const isCurrent = version.version_id === currentVersionId
          const createdAt = new Date(version.created_at)
          const timeAgo = formatTimeAgo(createdAt)

          return (
            <Card key={version.version_id} className="p-4 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <Clock className="w-4 h-4 text-slate-400" />
                    <span className="text-sm font-medium text-white">
                      {createdAt.toLocaleString()}
                    </span>
                    <span className="text-xs text-slate-500">({timeAgo})</span>
                    {isCurrent && (
                      <Badge variant="success">Current</Badge>
                    )}
                  </div>

                  {version.created_by && (
                    <div className="flex items-center gap-2 mb-2 text-sm text-slate-400">
                      <User className="w-4 h-4" />
                      <span>{version.created_by}</span>
                    </div>
                  )}

                  {version.comment && (
                    <div className="flex items-start gap-2 mb-2 text-sm text-slate-400">
                      <FileText className="w-4 h-4 mt-0.5 flex-shrink-0" />
                      <span className="flex-1">{version.comment}</span>
                    </div>
                  )}

                  <div className="text-xs text-slate-500 font-mono mt-2">
                    Version: {version.version_id.substring(0, 8)}...
                  </div>
                </div>

                <div className="flex items-center gap-2 ml-4">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleView(version.version_id)}
                    icon={<Eye className="w-4 h-4" />}
                  >
                    View
                  </Button>
                  {!isCurrent && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleCompare(version.version_id)}
                        icon={<GitCompare className="w-4 h-4" />}
                      >
                        Compare
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleRestore(version.version_id)}
                        icon={<RotateCcw className="w-4 h-4" />}
                      >
                        Restore
                      </Button>
                    </>
                  )}
                </div>
              </div>
            </Card>
          )
        })}
      </div>
    </div>
  )
}

export default ConfigHistory

