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
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-white">
        <div className="flex items-center gap-2 text-sm text-gray-600 mb-2">
          <Link href="/config" className="hover:text-primary-600">
            Configuration
          </Link>
          <ChevronRight className="w-4 h-4" />
          <span className="text-gray-900 font-medium">History</span>
        </div>
        <div className="flex items-center gap-3">
          <History className="w-6 h-6 text-gray-700" />
          <h1 className="text-2xl font-bold text-gray-900">Configuration History</h1>
        </div>
        <p className="text-sm text-gray-600 mt-1">
          View, compare, and restore previous configuration versions
        </p>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <ConfigHistory
          onVersionSelect={handleVersionSelect}
          onCompare={handleCompare}
          onRestore={handleRestore}
        />
      </div>

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
          <div className="bg-white rounded-lg p-6 shadow-lg">
            <div className="flex items-center gap-3">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
              <span className="text-gray-700">Loading diff...</span>
            </div>
          </div>
        </div>
      )}

      {/* Diff Error */}
      {diffError && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="bg-white rounded-lg p-6 shadow-lg max-w-md">
            <div className="text-red-800 mb-4">{diffError}</div>
            <button
              onClick={() => {
                setDiffError(null)
                setIsDiffOpen(false)
              }}
              className="px-4 py-2 bg-gray-100 rounded hover:bg-gray-200"
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
          <div className="bg-white rounded-lg p-6 shadow-lg">
            <div className="flex items-center gap-3">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
              <span className="text-gray-700">Loading version...</span>
            </div>
          </div>
        </div>
      )}

      {/* Version Error */}
      {versionError && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="bg-white rounded-lg p-6 shadow-lg max-w-md">
            <div className="text-red-800 mb-4">{versionError}</div>
            <button
              onClick={() => setVersionError(null)}
              className="px-4 py-2 bg-gray-100 rounded hover:bg-gray-200"
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

