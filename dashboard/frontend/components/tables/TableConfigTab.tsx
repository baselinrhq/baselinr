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
      <div className="bg-surface-800/40 border border-amber-500/20 rounded-lg p-6">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-400 mt-0.5" />
          <div className="flex-1">
            <p className="text-amber-400 font-medium">Configuration Not Available</p>
            <p className="text-slate-400 text-sm mt-1">
              Table configuration is not yet implemented. Use the configuration pages to manage table settings.
            </p>
            <div className="mt-4">
              <Link href={`/config/tables?table=${encodeURIComponent(tableName)}`}>
                <Button
                  variant="primary"
                  icon={<Settings className="w-4 h-4" />}
                  iconPosition="left"
                >
                  Configure Table
                </Button>
              </Link>
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
      <div className="glass-card p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Settings className="w-5 h-5 text-cyan-400" />
              Table Configuration
            </h2>
            <p className="text-sm text-slate-400 mt-1">
              {tableName}{schema && ` (${schema})`}
            </p>
          </div>
          <Link href={`/config/tables?table=${encodeURIComponent(tableName)}${schema ? `&schema=${encodeURIComponent(schema)}` : ''}`}>
            <Button
              variant="primary"
              icon={<ExternalLink className="w-4 h-4" />}
              iconPosition="left"
            >
              Edit Configuration
            </Button>
          </Link>
        </div>
      </div>

      {/* Configuration Status */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-3 mb-4">
          {hasConfig ? (
            <>
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <span className="text-sm font-medium text-white">Configuration Active</span>
            </>
          ) : (
            <>
              <AlertCircle className="w-5 h-5 text-amber-400" />
              <span className="text-sm font-medium text-white">Using Default Configuration</span>
            </>
          )}
        </div>

        {hasConfig ? (
          <div className="space-y-4">
            {/* Profiling Settings */}
            {config.config.profiling && (
              <div>
                <h3 className="text-sm font-semibold text-slate-300 mb-2">Profiling Settings</h3>
                <div className="bg-surface-800/50 rounded-lg p-4">
                  <pre className="text-xs text-slate-300 overflow-x-auto">
                    {JSON.stringify(config.config.profiling, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* Column Configuration */}
            {config.config.columns && (
              <div>
                <h3 className="text-sm font-semibold text-slate-300 mb-2">Column Configuration</h3>
                <div className="bg-surface-800/50 rounded-lg p-4">
                  <pre className="text-xs text-slate-300 overflow-x-auto">
                    {JSON.stringify(config.config.columns, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* Other Settings */}
            {Object.keys(config.config).filter(key => !['profiling', 'columns'].includes(key)).length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-slate-300 mb-2">Other Settings</h3>
                <div className="bg-surface-800/50 rounded-lg p-4">
                  <pre className="text-xs text-slate-300 overflow-x-auto">
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
          <div className="bg-surface-800/50 rounded-lg p-6 text-center">
            <p className="text-slate-400 text-sm mb-4">
              This table is using default configuration settings. Configure profiling, sampling, and validation rules
              to customize how this table is monitored.
            </p>
            <Link href={`/config/tables?table=${encodeURIComponent(tableName)}${schema ? `&schema=${encodeURIComponent(schema)}` : ''}`}>
              <Button
                variant="primary"
                icon={<Settings className="w-4 h-4" />}
                iconPosition="left"
              >
                Configure Table
              </Button>
            </Link>
          </div>
        )}
      </div>

      {/* Quick Links */}
      <div className="glass-card p-6">
        <h3 className="text-sm font-semibold text-slate-300 mb-4">Related Configuration</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link href="/config/profiling">
            <Button
              variant="outline"
              className="justify-start w-full"
              icon={<Settings className="w-4 h-4" />}
              iconPosition="left"
            >
              Profiling Settings
            </Button>
          </Link>
          <Link href="/config/validation">
            <Button
              variant="outline"
              className="justify-start w-full"
              icon={<Settings className="w-4 h-4" />}
              iconPosition="left"
            >
              Validation Rules
            </Button>
          </Link>
          <Link href="/config/drift">
            <Button
              variant="outline"
              className="justify-start w-full"
              icon={<Settings className="w-4 h-4" />}
              iconPosition="left"
            >
              Drift Detection
            </Button>
          </Link>
        </div>
      </div>
    </div>
  )
}

