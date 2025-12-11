'use client'

import { useEffect, useState } from 'react'
import { useConfig } from '@/hooks/useConfig'
import { ConfigHub } from '@/components/config/ConfigHub'
import { ConfigStatus } from '@/components/config/ConfigStatus'
import { ConfigQuickActions } from '@/components/config/ConfigQuickActions'
import { Loader2, AlertCircle } from 'lucide-react'

export default function ConfigHubPage() {
  const {
    currentConfig,
    loadConfig,
    isLoading: isConfigLoading,
    error: configError,
  } = useConfig()
  const [hasTriedLoad, setHasTriedLoad] = useState(false)

  // Load config on mount (only once)
  useEffect(() => {
    if (!currentConfig && !hasTriedLoad && !configError) {
      setHasTriedLoad(true)
      loadConfig().catch(() => {
        // Error is handled by useConfig hook
      })
    }
  }, [currentConfig, loadConfig, hasTriedLoad, configError])

  const handleRefresh = () => {
    loadConfig().catch(() => {
      // Error is handled by useConfig hook
    })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Configuration</h1>
        <p className="text-gray-600 mt-1">
          Manage your Baselinr configuration across all sections
        </p>
      </div>

      {/* Loading State */}
      {isConfigLoading && !currentConfig && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          <span className="ml-3 text-sm text-gray-500">Loading configuration...</span>
        </div>
      )}

      {/* Error State */}
      {configError && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="font-medium text-yellow-900">Configuration Error</div>
            <div className="text-sm text-yellow-700 mt-1">
              {configError instanceof Error ? (
                configError.message.includes('NetworkError') ||
                configError.message.includes('Failed to fetch') ? (
                  <>
                    Unable to connect to the backend API. Please ensure:
                    <ul className="list-disc list-inside mt-2 space-y-1">
                      <li>
                        The backend server is running on{' '}
                        <code className="bg-yellow-100 px-1 rounded">
                          {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}
                        </code>
                      </li>
                      <li>Check the browser console for more details</li>
                      <li>Verify CORS settings if running on a different port</li>
                    </ul>
                  </>
                ) : (
                  configError.message
                )
              ) : (
                'Unknown error occurred'
              )}
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      {(!isConfigLoading || currentConfig) && (
        <>
          {/* Configuration Status Overview */}
          <ConfigStatus
            config={currentConfig}
            isLoading={isConfigLoading}
            onRefresh={handleRefresh}
          />

          {/* Quick Actions */}
          <ConfigQuickActions />

          {/* Configuration Sections */}
          <ConfigHub config={currentConfig} isLoading={isConfigLoading} />
        </>
      )}
    </div>
  )
}

