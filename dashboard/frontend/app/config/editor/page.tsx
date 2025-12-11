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
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-white">
        <div className="flex items-center gap-2 text-sm text-gray-600 mb-2">
          <Link href="/config" className="hover:text-primary-600">
            Configuration
          </Link>
          <ChevronRight className="w-4 h-4" />
          <span className="text-gray-900 font-medium">Editor</span>
        </div>
        <h1 className="text-2xl font-bold text-gray-900">Configuration Editor</h1>
        <p className="text-sm text-gray-600 mt-1">
          Edit your Baselinr configuration with visual and YAML views
        </p>
      </div>

      {/* Error State */}
      {configError && !currentConfig && (
        <div className="mx-6 mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-start gap-3">
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

      {/* Editor */}
      <div className="flex-1 overflow-hidden">
        <ConfigEditor
          config={currentConfig}
          onSave={handleSave}
          onValidate={handleValidate}
        />
      </div>
    </div>
  )
}

