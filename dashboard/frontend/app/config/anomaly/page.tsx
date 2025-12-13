'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useMutation } from '@tanstack/react-query'
import { Save, Loader2, AlertCircle, CheckCircle, Activity, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { AnomalyConfig } from '@/components/config/AnomalyConfig'
import { ExpectationLearning } from '@/components/config/ExpectationLearning'
import { useConfig } from '@/hooks/useConfig'
import { StorageConfig } from '@/types/config'

/**
 * Deep merge utility for merging config updates
 */
function deepMerge(target: Record<string, unknown>, source: Record<string, unknown>): Record<string, unknown> {
  const output = { ...target }
  if (isObject(target) && isObject(source)) {
    Object.keys(source).forEach((key) => {
      if (isObject(source[key])) {
        if (!(key in target)) {
          Object.assign(output, { [key]: source[key] })
        } else {
          output[key] = deepMerge(target[key] as Record<string, unknown>, source[key] as Record<string, unknown>)
        }
      } else {
        Object.assign(output, { [key]: source[key] })
      }
    })
  }
  return output
}

function isObject(item: unknown): boolean {
  return item && typeof item === 'object' && !Array.isArray(item)
}

export default function AnomalyPage() {
  const {
    currentConfig,
    modifiedConfig,
    loadConfig,
    updateConfigPath,
    saveConfig,
    isLoading: isConfigLoading,
    error: configError,
    canSave,
  } = useConfig()

  const [saveSuccess, setSaveSuccess] = useState(false)
  const [anomalyErrors, setAnomalyErrors] = useState<Record<string, string>>({})
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

  // Get effective config (current + modifications) and extract storage
  const effectiveConfig = currentConfig && modifiedConfig
    ? deepMerge(currentConfig as unknown as Record<string, unknown>, modifiedConfig as unknown as Record<string, unknown>)
    : (currentConfig || {}) as unknown as Record<string, unknown>
  const storage: StorageConfig | undefined = effectiveConfig?.storage as StorageConfig | undefined

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async () => {
      setSaveSuccess(false)
      setAnomalyErrors({})
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
        setAnomalyErrors({
          general: error.message,
        })
      } else {
        setAnomalyErrors({
          general: error instanceof Error ? error.message : 'Failed to save anomaly detection configuration',
        })
      }
    },
  })

  // Handle storage config changes (for anomaly/expectation learning settings)
  const handleStorageChange = (updatedStorage: StorageConfig) => {
    // Update storage config via updateConfigPath
    Object.keys(updatedStorage).forEach((key) => {
      const value = updatedStorage[key as keyof StorageConfig]
      updateConfigPath(['storage', key], value)
    })
  }

  // Handle save
  const handleSave = () => {
    saveMutation.mutate()
  }

  // Initialize default storage if needed
  useEffect(() => {
    if (currentConfig && !storage) {
      // Initialize with default storage config
      updateConfigPath(['storage'], {
        connection: {
          type: 'postgres',
          database: '',
        },
        results_table: 'baselinr_results',
        runs_table: 'baselinr_runs',
        create_tables: true,
        enable_expectation_learning: false,
        enable_anomaly_detection: false,
      })
    }
  }, [currentConfig, storage, updateConfigPath])

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

  if (!storage) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-cyan-400 mx-auto" />
          <p className="mt-4 text-sm text-slate-400">Initializing configuration...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 lg:p-8 max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
            <Link href="/config" className="hover:text-cyan-400">
              Configuration
            </Link>
            <ChevronRight className="w-4 h-4" />
            <span className="text-white font-medium">Anomaly Detection</span>
          </div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Activity className="w-6 h-6" />
            Anomaly Detection & Expectation Learning
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Configure automatic anomaly detection and expectation learning from historical data
          </p>
        </div>
        <div className="flex items-center gap-3">
          {saveSuccess && (
            <div className="flex items-center gap-2 text-sm text-emerald-400">
              <CheckCircle className="w-4 h-4" />
              <span>Saved successfully</span>
            </div>
          )}
          {anomalyErrors.general && (
            <div className="flex items-center gap-2 text-sm text-rose-400">
              <AlertCircle className="w-4 h-4" />
              <span>{anomalyErrors.general}</span>
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

      {/* Success Message */}
      {saveSuccess && (
        <div className="mb-6 glass-card border-emerald-500/30 bg-emerald-500/10 p-4 flex items-center gap-3">
          <CheckCircle className="w-5 h-5 text-emerald-400" />
          <p className="text-sm font-medium text-emerald-300">
            Configuration saved successfully
          </p>
        </div>
      )}

      {/* Error Message */}
      {anomalyErrors.general && (
        <div className="mb-6 glass-card border-rose-500/30 bg-rose-500/10 p-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400" />
          <p className="text-sm font-medium text-rose-300">{anomalyErrors.general}</p>
        </div>
      )}

      {/* Main Content */}
      <div className="space-y-6">
        {/* Expectation Learning Configuration */}
        <ExpectationLearning
          storage={storage}
          onChange={handleStorageChange}
          errors={anomalyErrors}
          isLoading={isConfigLoading || saveMutation.isPending}
        />

        {/* Anomaly Detection Configuration */}
        <AnomalyConfig
          storage={storage}
          onChange={handleStorageChange}
          errors={anomalyErrors}
          isLoading={isConfigLoading || saveMutation.isPending}
        />
      </div>
    </div>
  )
}

