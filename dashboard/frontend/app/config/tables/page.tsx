'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useMutation } from '@tanstack/react-query'
import { Save, Loader2, AlertCircle, CheckCircle, Table, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { TableSelection } from '@/components/config/TableSelection'
import { TableDiscovery } from '@/components/config/TableDiscovery'
import { useConfig } from '@/hooks/useConfig'
import { TablePattern, DiscoveryOptionsConfig } from '@/types/config'

export default function TablesPage() {
  const {
    currentConfig,
    loadConfig,
    updateConfigPath,
    saveConfig,
    isLoading: isConfigLoading,
    error: configError,
    canSave,
  } = useConfig()

  const [saveSuccess, setSaveSuccess] = useState(false)
  const [tableErrors, setTableErrors] = useState<Record<string, string>>({})
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

  // Get current profiling config
  const tables: TablePattern[] = currentConfig?.profiling?.tables || []
  const discoveryOptions: DiscoveryOptionsConfig | undefined =
    currentConfig?.profiling?.discovery_options

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async () => {
      setSaveSuccess(false)
      setTableErrors({})
      await saveConfig()
    },
    onSuccess: () => {
      setSaveSuccess(true)
      // Clear success message after 3 seconds
      setTimeout(() => setSaveSuccess(false), 3000)
    },
    onError: (error) => {
      // Handle validation errors
      if (error instanceof Error && error.message.includes('validation')) {
        // Could parse validation errors here if API provides field-level errors
        setTableErrors({
          general: error.message,
        })
      } else {
        setTableErrors({
          general: error instanceof Error ? error.message : 'Failed to save table configuration',
        })
      }
    },
  })

  // Handle tables change
  const handleTablesChange = (newTables: TablePattern[]) => {
    updateConfigPath(['profiling', 'tables'], newTables)
  }

  // Handle discovery options change
  const handleDiscoveryChange = (options: DiscoveryOptionsConfig) => {
    updateConfigPath(['profiling', 'discovery_options'], options)
  }

  // Handle save
  const handleSave = () => {
    saveMutation.mutate()
  }

  // Show loading state
  if (isConfigLoading && !currentConfig) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
      </div>
    )
  }

  // Show error state if config failed to load
  if (configError && !currentConfig) {
    return (
      <div className="max-w-2xl mx-auto p-6 lg:p-8">
        <Card>
          <div className="py-12 text-center">
            <AlertCircle className="h-12 w-12 text-rose-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">
              Failed to Load Configuration
            </h3>
            <p className="text-sm text-slate-400 mb-6">
              {typeof configError === 'string'
                ? configError
                : configError && typeof configError === 'object' && 'message' in configError
                ? String((configError as { message: unknown }).message)
                : 'Backend API Not Available'}
            </p>
            <Button variant="outline" onClick={() => loadConfig()}>
              Retry
            </Button>
          </div>
        </Card>
      </div>
    )
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
            <span className="text-white font-medium">Tables</span>
          </div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Table className="w-6 h-6" />
            Table Selection & Discovery
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Configure which tables to profile and how they are discovered
          </p>
        </div>
        <div className="flex items-center gap-3">
          {saveSuccess && (
            <div className="flex items-center gap-2 text-sm text-emerald-400">
              <CheckCircle className="w-4 h-4" />
              <span>Saved successfully</span>
            </div>
          )}
          {tableErrors.general && (
            <div className="flex items-center gap-2 text-sm text-rose-400">
              <AlertCircle className="w-4 h-4" />
              <span>{tableErrors.general}</span>
            </div>
          )}
          <Button
            onClick={handleSave}
            disabled={!canSave || saveMutation.isPending}
            loading={saveMutation.isPending}
            icon={<Save className="w-4 h-4" />}
          >
            Save Configuration
          </Button>
        </div>
      </div>

      {/* Main Content - Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Table Selection - Left Column (2/3 width) */}
        <div className="lg:col-span-2">
          <TableSelection
            tables={tables}
            onChange={handleTablesChange}
            errors={tableErrors}
            isLoading={isConfigLoading || saveMutation.isPending}
          />
        </div>

        {/* Discovery Settings - Right Column (1/3 width) */}
        <div className="lg:col-span-1">
          <TableDiscovery
            discoveryOptions={discoveryOptions || {}}
            onChange={handleDiscoveryChange}
            errors={tableErrors}
            isLoading={isConfigLoading || saveMutation.isPending}
          />
        </div>
      </div>
    </div>
  )
}

