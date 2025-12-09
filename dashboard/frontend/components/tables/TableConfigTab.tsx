'use client'

import { useQuery } from '@tanstack/react-query'
import { Settings, ExternalLink, CheckCircle2, AlertCircle } from 'lucide-react'
import { LoadingSpinner } from '@/components/ui'
import { Button } from '@/components/ui'
import { fetchTableConfig } from '@/lib/api'
import Link from 'next/link'

interface TableConfigTabProps {
  tableName: string
  schema?: string
}

export default function TableConfigTab({
  tableName,
  schema
}: TableConfigTabProps) {
  const { data: config, isLoading, error } = useQuery({
    queryKey: ['table-config', tableName, schema],
    queryFn: () => fetchTableConfig(tableName, { schema }),
    staleTime: 60000
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error || !config) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5" />
          <div className="flex-1">
            <p className="text-yellow-800 font-medium">Configuration Not Available</p>
            <p className="text-yellow-700 text-sm mt-1">
              Table configuration is not yet implemented. Use the configuration pages to manage table settings.
            </p>
            <div className="mt-4">
              <Button
                variant="primary"
                asChild
              >
                <Link href={`/config/tables?table=${encodeURIComponent(tableName)}`}>
                  <Settings className="w-4 h-4 mr-2" />
                  Configure Table
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const hasConfig = config.config && Object.keys(config.config).length > 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Table Configuration
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              {tableName}{schema && ` (${schema})`}
            </p>
          </div>
          <Button
            variant="primary"
            asChild
          >
            <Link href={`/config/tables?table=${encodeURIComponent(tableName)}${schema ? `&schema=${encodeURIComponent(schema)}` : ''}`}>
              <ExternalLink className="w-4 h-4 mr-2" />
              Edit Configuration
            </Link>
          </Button>
        </div>
      </div>

      {/* Configuration Status */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center gap-3 mb-4">
          {hasConfig ? (
            <>
              <CheckCircle2 className="w-5 h-5 text-green-600" />
              <span className="text-sm font-medium text-gray-900">Configuration Active</span>
            </>
          ) : (
            <>
              <AlertCircle className="w-5 h-5 text-yellow-600" />
              <span className="text-sm font-medium text-gray-900">Using Default Configuration</span>
            </>
          )}
        </div>

        {hasConfig ? (
          <div className="space-y-4">
            {/* Profiling Settings */}
            {config.config.profiling && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Profiling Settings</h3>
                <div className="bg-gray-50 rounded-lg p-4">
                  <pre className="text-xs text-gray-600 overflow-x-auto">
                    {JSON.stringify(config.config.profiling, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* Column Configuration */}
            {config.config.columns && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Column Configuration</h3>
                <div className="bg-gray-50 rounded-lg p-4">
                  <pre className="text-xs text-gray-600 overflow-x-auto">
                    {JSON.stringify(config.config.columns, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* Other Settings */}
            {Object.keys(config.config).filter(key => !['profiling', 'columns'].includes(key)).length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Other Settings</h3>
                <div className="bg-gray-50 rounded-lg p-4">
                  <pre className="text-xs text-gray-600 overflow-x-auto">
                    {JSON.stringify(
                      Object.fromEntries(
                        Object.entries(config.config).filter(([key]) => !['profiling', 'columns'].includes(key))
                      ),
                      null,
                      2
                    )}
                  </pre>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="bg-gray-50 rounded-lg p-6 text-center">
            <p className="text-gray-600 text-sm mb-4">
              This table is using default configuration settings. Configure profiling, sampling, and validation rules
              to customize how this table is monitored.
            </p>
            <Button
              variant="primary"
              asChild
            >
              <Link href={`/config/tables?table=${encodeURIComponent(tableName)}${schema ? `&schema=${encodeURIComponent(schema)}` : ''}`}>
                <Settings className="w-4 h-4 mr-2" />
                Configure Table
              </Link>
            </Button>
          </div>
        )}
      </div>

      {/* Quick Links */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Related Configuration</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Button
            variant="outline"
            asChild
            className="justify-start"
          >
            <Link href="/config/profiling">
              <Settings className="w-4 h-4 mr-2" />
              Profiling Settings
            </Link>
          </Button>
          <Button
            variant="outline"
            asChild
            className="justify-start"
          >
            <Link href="/config/validation">
              <Settings className="w-4 h-4 mr-2" />
              Validation Rules
            </Link>
          </Button>
          <Button
            variant="outline"
            asChild
            className="justify-start"
          >
            <Link href="/config/drift">
              <Settings className="w-4 h-4 mr-2" />
              Drift Detection
            </Link>
          </Button>
        </div>
      </div>
    </div>
  )
}

