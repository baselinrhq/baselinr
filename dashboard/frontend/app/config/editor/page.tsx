'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { ChevronRight, AlertCircle } from 'lucide-react'
import { ConfigEditor } from '@/components/config/ConfigEditor'
import { useConfig } from '@/hooks/useConfig'

export default function ConfigEditorPage() {
  const {
    currentConfig,
    loadConfig,
    saveConfig,
    validateConfig,
    error: configError,
  } = useConfig()
  const [hasTriedLoad, setHasTriedLoad] = useState(false)

  // Load config on mount
  useEffect(() => {
    if (!currentConfig && !hasTriedLoad && !configError) {
      setHasTriedLoad(true)
      loadConfig().catch(() => {
        // Error is handled by useConfig hook
      })
    }
  }, [currentConfig, loadConfig, hasTriedLoad, configError])

  const handleSave = async () => {
    await saveConfig()
  }

  const handleValidate = async () => {
    return await validateConfig()
  }

  return (
    <div className="h-screen flex flex-col bg-surface-950">
      {/* Header */}
      <div className="p-6 lg:p-8">
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
          <Link href="/config" className="hover:text-cyan-400">
            Configuration
          </Link>
          <ChevronRight className="w-4 h-4" />
          <span className="text-white font-medium">Editor</span>
        </div>
        <h1 className="text-2xl font-bold text-white">Configuration Editor</h1>
        <p className="text-sm text-slate-400 mt-1">
          Edit your Baselinr configuration with visual and YAML views
        </p>
      </div>

      {/* Error State */}
      {configError && !currentConfig && (
        <div className="px-6 lg:px-8">
          <div className="glass-card border-amber-500/30 bg-amber-500/10 p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <div className="font-medium text-amber-300">Configuration Error</div>
              <div className="text-sm text-amber-200 mt-1">
                {(() => {
                  if (!configError) return 'Unknown error occurred'
                  const errorObj = configError as { message?: string } | string | null
                  const errorMessage = typeof errorObj === 'string' 
                    ? errorObj 
                    : errorObj && typeof errorObj === 'object' && 'message' in errorObj
                      ? String(errorObj.message || 'Unknown error')
                      : String(configError)
                  
                  if (errorMessage.includes('NetworkError') || errorMessage.includes('Failed to fetch')) {
                    return (
                      <>
                        Unable to connect to the backend API. Please ensure:
                        <ul className="list-disc list-inside mt-2 space-y-1">
                          <li>
                            The backend server is running on{' '}
                            <code className="bg-amber-500/20 px-1 rounded text-amber-200">
                              {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}
                            </code>
                          </li>
                          <li>Check the browser console for more details</li>
                        </ul>
                      </>
                    )
                  }
                  return errorMessage
                })()}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Editor */}
      <div className="flex-1 overflow-hidden">
        <ConfigEditor
          onSave={handleSave}
          onValidate={handleValidate}
        />
      </div>
    </div>
  )
}

