'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useMutation } from '@tanstack/react-query'
import { Save, Loader2, AlertCircle, CheckCircle, TrendingUp, ChevronRight, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { DriftConfig } from '@/components/config/DriftConfig'
import { BaselineConfig } from '@/components/config/BaselineConfig'
import { TypeSpecificThresholds } from '@/components/config/TypeSpecificThresholds'
import { useConfig } from '@/hooks/useConfig'
import { DriftDetectionConfig } from '@/types/config'

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

export default function DriftPage() {
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
  const [driftErrors, setDriftErrors] = useState<Record<string, string>>({})
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

  // Get effective config (current + modifications) and extract drift detection
  const effectiveConfig = currentConfig && modifiedConfig
    ? deepMerge(currentConfig as unknown as Record<string, unknown>, modifiedConfig as unknown as Record<string, unknown>)
    : (currentConfig || {}) as unknown as Record<string, unknown>
  const driftDetection: DriftDetectionConfig | undefined = effectiveConfig?.drift_detection as DriftDetectionConfig | undefined

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async () => {
      setSaveSuccess(false)
      setDriftErrors({})
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
        setDriftErrors({
          general: error.message,
        })
      } else {
        setDriftErrors({
          general: error instanceof Error ? error.message : 'Failed to save drift detection configuration',
        })
      }
    },
  })

  // Handle drift detection config changes
  const handleDriftChange = (updatedDrift: DriftDetectionConfig) => {
    // Update each field via updateConfigPath
    Object.keys(updatedDrift).forEach((key) => {
      const value = updatedDrift[key as keyof DriftDetectionConfig]
      updateConfigPath(['drift_detection', key], value)
    })
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
            <span className="text-white font-medium">Drift Detection</span>
          </div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <TrendingUp className="w-6 h-6" />
            Drift Detection Configuration
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Configure drift detection strategies, thresholds, and baseline selection
          </p>
        </div>
        <div className="flex items-center gap-3">
          {saveSuccess && (
            <div className="flex items-center gap-2 text-sm text-emerald-400">
              <CheckCircle className="w-4 h-4" />
              <span>Saved successfully</span>
            </div>
          )}
          {driftErrors.general && (
            <div className="flex items-center gap-2 text-sm text-rose-400">
              <AlertCircle className="w-4 h-4" />
              <span>{driftErrors.general}</span>
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

      {/* Banner linking to contracts */}
      <div className="glass-card border-amber-500/30 bg-amber-500/10 p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div>
            <p className="text-sm font-medium text-amber-300">
              Contract-level drift configurations
            </p>
            <p className="text-xs text-amber-400/80 mt-1">
              Configure drift detection strategy and thresholds per contract
            </p>
          </div>
        </div>
        <Link href="/config/contracts">
          <Button variant="outline" icon={<ArrowRight className="w-4 h-4" />}>
            Manage in Contracts
          </Button>
        </Link>
      </div>

      {/* Main Content */}
      <div className="space-y-6">
        {/* Drift Detection Strategy */}
        <DriftConfig
          driftDetection={driftDetection || {}}
          onChange={handleDriftChange}
          errors={driftErrors}
          isLoading={isConfigLoading || saveMutation.isPending}
        />

        {/* Baseline Configuration */}
        <BaselineConfig
          baselines={driftDetection?.baselines || {}}
          onChange={(baselines) => {
            updateConfigPath(['drift_detection', 'baselines'], baselines)
          }}
          errors={driftErrors}
          isLoading={isConfigLoading || saveMutation.isPending}
        />

        {/* Type-Specific Thresholds */}
        <TypeSpecificThresholds
          enableTypeSpecificThresholds={driftDetection?.enable_type_specific_thresholds ?? true}
          typeSpecificThresholds={driftDetection?.type_specific_thresholds || {}}
          onChange={(enabled, thresholds) => {
            updateConfigPath(['drift_detection', 'enable_type_specific_thresholds'], enabled)
            if (thresholds) {
              updateConfigPath(['drift_detection', 'type_specific_thresholds'], thresholds)
            }
          }}
          errors={driftErrors}
          isLoading={isConfigLoading || saveMutation.isPending}
        />
      </div>
    </div>
  )
}

