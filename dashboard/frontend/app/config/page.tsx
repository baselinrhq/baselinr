'use client'

import { useEffect, useState } from 'react'
import { useConfig } from '@/hooks/useConfig'
import { ConfigHub } from '@/components/config/ConfigHub'
import { ConfigStatus } from '@/components/config/ConfigStatus'
import { ConfigQuickActions } from '@/components/config/ConfigQuickActions'
import { Loader2, AlertCircle, Settings } from 'lucide-react'

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
    <div className="p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <div className="p-2 rounded-lg bg-slate-500/10">
            <Settings className="w-7 h-7 text-slate-400" />
          </div>
          Configuration
        </h1>
        <p className="text-slate-400 mt-2">
          Manage your Baselinr configuration across all sections
        </p>
      </div>

      {/* Loading State */}
      {isConfigLoading && !currentConfig && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-accent-400" />
          <span className="ml-3 text-sm text-slate-400">Loading configuration...</span>
        </div>
      )}

      {/* Error State */}
      {configError && (
        <div className="glass-card border-warning-500/20 bg-warning-500/5 p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-warning-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="font-medium text-warning-300">Configuration Error</div>
            <div className="text-sm text-warning-400/80 mt-1">
              {typeof configError === 'string' ? (
                configError.includes('NetworkError') ||
                configError.includes('Failed to fetch') ? (
                  <>
                    Unable to connect to the backend API. Please ensure:
                    <ul className="list-disc list-inside mt-2 space-y-1">
                      <li>
                        The backend server is running on{' '}
                        <code className="bg-warning-500/10 px-1 rounded text-warning-300">
                          {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}
                        </code>
                      </li>
                      <li>Check the browser console for more details</li>
                      <li>Verify CORS settings if running on a different port</li>
                    </ul>
                  </>
                ) : (
                  configError
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
