'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import React from 'react'
import { ChevronRight, History } from 'lucide-react'
import { ConfigHistory } from '@/components/config/ConfigHistory'
import { ConfigDiff } from '@/components/config/ConfigDiff'
import { ConfigRollback } from '@/components/config/ConfigRollback'
import { ConfigVersionView } from '@/components/config/ConfigVersionView'
import { getConfigDiff, restoreConfigVersion, loadConfigVersion, ConfigError } from '@/lib/api/config'
import { ConfigVersionResponse, ConfigDiffResponse } from '@/types/config'
import { useQueryClient } from '@tanstack/react-query'

export default function ConfigHistoryPage() {
  const router = useRouter()
  const queryClient = useQueryClient()
  const [diffData, setDiffData] = useState<ConfigDiffResponse | null>(null)
  const [isDiffOpen, setIsDiffOpen] = useState(false)
  const [viewVersionId, setViewVersionId] = useState<string | null>(null)
  const [viewVersionData, setViewVersionData] = useState<ConfigVersionResponse | null>(null)
  const [isViewOpen, setIsViewOpen] = useState(false)
  const [rollbackVersionId, setRollbackVersionId] = useState<string | null>(null)
  const [rollbackVersionData, setRollbackVersionData] = useState<ConfigVersionResponse | null>(null)
  const [isRollbackOpen, setIsRollbackOpen] = useState(false)
  const [isLoadingDiff, setIsLoadingDiff] = useState(false)
  const [isLoadingVersion, setIsLoadingVersion] = useState(false)
  const [diffError, setDiffError] = useState<string | null>(null)
  const [versionError, setVersionError] = useState<string | null>(null)

  const handleCompare = async (versionId: string, compareWith?: string) => {
    setIsLoadingDiff(true)
    setDiffError(null)
    
    try {
      const diff = await getConfigDiff(versionId, compareWith)
      setDiffData(diff)
      setIsDiffOpen(true)
    } catch (error) {
      setDiffError(error instanceof ConfigError ? error.message : 'Failed to load diff')
    } finally {
      setIsLoadingDiff(false)
    }
  }

  const handleRestore = async (versionId: string) => {
    try {
      const versionData = await loadConfigVersion(versionId)
      setRollbackVersionId(versionId)
      setRollbackVersionData(versionData)
      setIsRollbackOpen(true)
    } catch (error) {
      console.error('Failed to load version for restore:', error)
    }
  }

  const handleRestoreConfirm = async (comment?: string) => {
    if (!rollbackVersionId) return

    try {
      await restoreConfigVersion(rollbackVersionId, comment)
      
      // Invalidate queries to refresh data
      await queryClient.invalidateQueries({ queryKey: ['config'] })
      await queryClient.invalidateQueries({ queryKey: ['config-history'] })
      
      // Close modal and redirect
      setIsRollbackOpen(false)
      setRollbackVersionId(null)
      setRollbackVersionData(null)
      
      // Redirect to config editor or hub
      router.push('/config/editor')
    } catch (error) {
      throw error // Let ConfigRollback handle the error
    }
  }

  const handleRestoreCancel = () => {
    setIsRollbackOpen(false)
    setRollbackVersionId(null)
    setRollbackVersionData(null)
  }

  const handleVersionSelect = async (versionId: string) => {
    setIsLoadingVersion(true)
    setVersionError(null)
    
    try {
      const versionData = await loadConfigVersion(versionId)
      setViewVersionId(versionId)
      setViewVersionData(versionData)
      setIsViewOpen(true)
    } catch (error) {
      setVersionError(error instanceof ConfigError ? error.message : 'Failed to load version')
      console.error('Failed to load version:', error)
    } finally {
      setIsLoadingVersion(false)
    }
  }

  const handleViewClose = () => {
    setIsViewOpen(false)
    setViewVersionId(null)
    setViewVersionData(null)
    setVersionError(null)
  }

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
            <Link href="/config" className="hover:text-cyan-400">
              Configuration
            </Link>
            <ChevronRight className="w-4 h-4" />
            <span className="text-white font-medium">History</span>
          </div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <History className="w-6 h-6" />
            Configuration History
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            View, compare, and restore previous configuration versions
          </p>
        </div>
      </div>

      {/* Main Content */}
      <ConfigHistory
        onVersionSelect={handleVersionSelect}
        onCompare={handleCompare}
        onRestore={handleRestore}
      />

      {/* Diff Modal */}
      {isDiffOpen && diffData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="relative w-full max-w-6xl">
            <ConfigDiff
              diff={diffData}
              onClose={() => {
                setIsDiffOpen(false)
                setDiffData(null)
                setDiffError(null)
              }}
            />
          </div>
        </div>
      )}

      {/* Loading Diff State */}
      {isLoadingDiff && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="glass-card p-6">
            <div className="flex items-center gap-3">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-cyan-400"></div>
              <span className="text-white">Loading diff...</span>
            </div>
          </div>
        </div>
      )}

      {/* Diff Error */}
      {diffError && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="glass-card border-rose-500/30 bg-rose-500/10 p-6 max-w-md">
            <div className="text-rose-200 mb-4">{diffError}</div>
            <button
              onClick={() => {
                setDiffError(null)
                setIsDiffOpen(false)
              }}
              className="px-4 py-2 bg-surface-800 rounded hover:bg-surface-700 text-white"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Version View Modal */}
      {viewVersionId && viewVersionData && (
        <ConfigVersionView
          versionData={viewVersionData}
          onClose={handleViewClose}
          isOpen={isViewOpen}
        />
      )}

      {/* Loading Version State */}
      {isLoadingVersion && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="glass-card p-6">
            <div className="flex items-center gap-3">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-cyan-400"></div>
              <span className="text-white">Loading version...</span>
            </div>
          </div>
        </div>
      )}

      {/* Version Error */}
      {versionError && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="glass-card border-rose-500/30 bg-rose-500/10 p-6 max-w-md">
            <div className="text-rose-200 mb-4">{versionError}</div>
            <button
              onClick={() => setVersionError(null)}
              className="px-4 py-2 bg-surface-800 rounded hover:bg-surface-700 text-white"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Rollback Modal */}
      {rollbackVersionId && rollbackVersionData && (
        <ConfigRollback
          versionId={rollbackVersionId}
          versionData={rollbackVersionData}
          onConfirm={handleRestoreConfirm}
          onCancel={handleRestoreCancel}
          isOpen={isRollbackOpen}
        />
      )}
    </div>
  )
}

