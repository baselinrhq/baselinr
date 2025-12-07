'use client'

import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Save, Loader2, AlertCircle, CheckCircle, BarChart3 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { ProfilingConfig } from '@/components/config/ProfilingConfig'
import { TableProfilingConfig } from '@/components/config/TableProfilingConfig'
import { useConfig } from '@/hooks/useConfig'
import { ProfilingConfig as ProfilingConfigType, TablePattern } from '@/types/config'
import { getTablePreview } from '@/lib/api/tables'

export default function ProfilingPage() {
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
  const [profilingErrors, setProfilingErrors] = useState<Record<string, string>>({})
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
  const profiling: ProfilingConfigType | undefined = currentConfig?.profiling

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async () => {
      setSaveSuccess(false)
      setProfilingErrors({})
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
        setProfilingErrors({
          general: error.message,
        })
      } else {
        setProfilingErrors({
          general: error instanceof Error ? error.message : 'Failed to save profiling configuration',
        })
      }
    },
  })

  // Handle profiling config changes
  const handleProfilingChange = (updatedProfiling: ProfilingConfigType) => {
    // Update each field via updateConfigPath
    Object.keys(updatedProfiling).forEach((key) => {
      const value = updatedProfiling[key as keyof ProfilingConfigType]
      updateConfigPath(['profiling', key], value)
    })
  }

  // Handle tables change
  const handleTablesChange = (tables: TablePattern[]) => {
    updateConfigPath(['profiling', 'tables'], tables)
  }

  // Handle get columns for column config
  const handleGetColumns = async (schema: string, table: string): Promise<string[]> => {
    try {
      const preview = await getTablePreview(schema, table)
      return preview.columns.map((col) => col.name)
    } catch (error) {
      console.error('Failed to get table columns:', error)
      return []
    }
  }

  // Handle save
  const handleSave = () => {
    saveMutation.mutate()
  }

  // Show loading state
  if (isConfigLoading && !currentConfig) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  // Show error state if config failed to load
  if (configError && !currentConfig) {
    return (
      <div className="max-w-2xl mx-auto">
        <Card>
          <div className="py-12 text-center">
            <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Failed to Load Configuration
            </h3>
            <p className="text-sm text-gray-600 mb-6">
              {configError instanceof Error
                ? configError.message
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <BarChart3 className="w-6 h-6" />
            Profiling Configuration
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            Configure profiling settings including metrics, sampling, partitions, and column-level overrides
          </p>
        </div>
        <div className="flex items-center gap-3">
          {saveSuccess && (
            <div className="flex items-center gap-2 text-sm text-green-600">
              <CheckCircle className="w-4 h-4" />
              <span>Saved successfully</span>
            </div>
          )}
          {profilingErrors.general && (
            <div className="flex items-center gap-2 text-sm text-red-600">
              <AlertCircle className="w-4 h-4" />
              <span>{profilingErrors.general}</span>
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

      {/* Main Content */}
      <div className="space-y-6">
        {/* Global Settings */}
        <ProfilingConfig
          profiling={profiling || {}}
          onChange={handleProfilingChange}
          errors={profilingErrors}
          isLoading={isConfigLoading || saveMutation.isPending}
        />

        {/* Per-Table Overrides */}
        <TableProfilingConfig
          tables={profiling?.tables || []}
          onChange={handleTablesChange}
          errors={profilingErrors}
          isLoading={isConfigLoading || saveMutation.isPending}
          onGetColumns={handleGetColumns}
        />
      </div>
    </div>
  )
}

