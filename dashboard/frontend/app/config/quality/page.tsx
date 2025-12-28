'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useMutation } from '@tanstack/react-query'
import { Save, Loader2, AlertCircle, CheckCircle, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { QualityScoringConfig } from '@/components/config/QualityScoringConfig'
import { useConfig } from '@/hooks/useConfig'
import { QualityScoringConfig as QualityScoringConfigType } from '@/types/config'

export default function QualityPage() {
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
  const [qualityErrors, setQualityErrors] = useState<Record<string, string>>({})
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

  // Get current quality scoring config
  const quality: QualityScoringConfigType | undefined = currentConfig?.quality_scoring

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async () => {
      setSaveSuccess(false)
      setQualityErrors({})
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
        setQualityErrors({
          general: error.message,
        })
      } else {
        setQualityErrors({
          general: error instanceof Error ? error.message : 'Failed to save quality scoring configuration',
        })
      }
    },
  })

  // Handle quality config changes
  const handleQualityChange = (updatedQuality: QualityScoringConfigType) => {
    updateConfigPath(['quality_scoring'], updatedQuality)
  }

  // Handle save
  const handleSave = async () => {
    await saveMutation.mutateAsync()
  }

  // Initialize default quality config if needed
  useEffect(() => {
    if (currentConfig && !quality) {
      // Initialize with default quality scoring config
      updateConfigPath(['quality_scoring'], {
        enabled: true,
        weights: {
          completeness: 25,
          validity: 25,
          consistency: 20,
          freshness: 15,
          uniqueness: 10,
          accuracy: 5,
        },
        thresholds: {
          healthy: 80,
          warning: 60,
          critical: 0,
        },
        freshness: {
          excellent: 24,
          good: 48,
          acceptable: 168,
        },
        store_history: true,
        history_retention_days: 90,
      })
    }
  }, [currentConfig, quality, updateConfigPath])

  if (isConfigLoading && !currentConfig) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-cyan-400 mx-auto" />
          <p className="mt-4 text-sm text-slate-400">Loading quality scoring configuration...</p>
        </div>
      </div>
    )
  }

  if (configError && !currentConfig) {
    const isBackendNotAvailable = configError.includes('404') || configError.includes('Not Found') || configError.includes('Failed to fetch')
    
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="p-6 max-w-md">
          <div className="flex items-center gap-3 text-rose-400 mb-4">
            <AlertCircle className="w-5 h-5" />
            <h2 className="text-lg font-semibold text-white">Backend API Not Available</h2>
          </div>
          <p className="text-sm text-slate-400 mb-4">
            {isBackendNotAvailable 
              ? 'The backend API endpoint is not implemented yet. The quality scoring configuration UI is ready, but requires the backend API to be running.'
              : configError}
          </p>
          <div className="flex gap-2">
            <Button 
              onClick={() => {
                setHasTriedLoad(false)
                loadConfig().catch(() => {})
              }} 
              variant="primary"
            >
              Retry
            </Button>
            <Button 
              onClick={() => {
                // Initialize with default quality config for demo purposes
                updateConfigPath(['quality_scoring'], {
                  enabled: true,
                  weights: {
                    completeness: 25,
                    validity: 25,
                    consistency: 20,
                    freshness: 15,
                    uniqueness: 10,
                    accuracy: 5,
                  },
                  thresholds: {
                    healthy: 80,
                    warning: 60,
                    critical: 0,
                  },
                  freshness: {
                    excellent: 24,
                    good: 48,
                    acceptable: 168,
                  },
                  store_history: true,
                  history_retention_days: 90,
                })
              }} 
              variant="secondary"
            >
              Use Default Config
            </Button>
          </div>
        </Card>
      </div>
    )
  }

  if (!quality) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-cyan-400 mx-auto" />
          <p className="mt-4 text-sm text-slate-400">Initializing quality scoring configuration...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-6 py-8 max-w-4xl">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
          <Link href="/config" className="hover:text-cyan-400">
            Configuration
          </Link>
          <ChevronRight className="w-4 h-4" />
          <span className="text-white font-medium">Quality Scoring</span>
        </div>
        <h1 className="text-2xl font-bold text-white">Quality Scoring Configuration</h1>
        <p className="mt-1 text-sm text-slate-400">
          Configure component weights, thresholds, and freshness settings for data quality scores
        </p>
      </div>

      {/* Success Message */}
      {saveSuccess && (
        <div className="mb-6 glass-card border-emerald-500/30 bg-emerald-500/10 p-4 flex items-center gap-3">
          <CheckCircle className="w-5 h-5 text-emerald-400" />
          <p className="text-sm font-medium text-emerald-300">
            Quality scoring configuration saved successfully
          </p>
        </div>
      )}

      {/* Error Message */}
      {qualityErrors.general && (
        <div className="mb-6 glass-card border-rose-500/30 bg-rose-500/10 p-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400" />
          <p className="text-sm font-medium text-rose-300">{qualityErrors.general}</p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6">
        {/* Main Configuration Form */}
        <Card className="p-6">
          <QualityScoringConfig
            config={quality}
            onChange={handleQualityChange}
            errors={qualityErrors}
            isLoading={isConfigLoading || saveMutation.isPending}
          />

          {/* Save Button */}
          <div className="mt-6 pt-6 border-t border-surface-700/50 flex items-center justify-end gap-4">
            <Button
              variant="primary"
              onClick={handleSave}
              disabled={!canSave || saveMutation.isPending}
            >
              {saveMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save Configuration
                </>
              )}
            </Button>
          </div>
        </Card>
      </div>
    </div>
  )
}









