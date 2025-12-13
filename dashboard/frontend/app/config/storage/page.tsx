'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Save, Loader2, AlertCircle, CheckCircle, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { StorageConfig } from '@/components/config/StorageConfig'
import { StorageStatus } from '@/components/config/StorageStatus'
import { useConfig } from '@/hooks/useConfig'
import { getStorageStatus } from '@/lib/api/config'
import { StorageConfig as StorageConfigType } from '@/types/config'

export default function StoragePage() {
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
  const [storageErrors, setStorageErrors] = useState<Record<string, string>>({})
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

  // Get current storage config
  const storage: StorageConfigType | undefined = currentConfig?.storage

  // Fetch storage status
  const {
    data: storageStatus,
    isLoading: isLoadingStatus,
    error: statusError,
    refetch: refetchStatus,
  } = useQuery({
    queryKey: ['storage-status'],
    queryFn: getStorageStatus,
    enabled: !!storage?.connection && !!currentConfig, // Only fetch if config is loaded
    retry: false, // Don't retry on 404 - backend not implemented yet
  })

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async () => {
      setSaveSuccess(false)
      setStorageErrors({})
      await saveConfig()
    },
    onSuccess: () => {
      setSaveSuccess(true)
      // Clear success message after 3 seconds
      setTimeout(() => setSaveSuccess(false), 3000)
      // Refetch status after save
      refetchStatus()
    },
    onError: (error) => {
      // Handle validation errors
      if (error instanceof Error && error.message.includes('validation')) {
        // Could parse validation errors here if API provides field-level errors
        setStorageErrors({
          general: error.message,
        })
      } else {
        setStorageErrors({
          general: error instanceof Error ? error.message : 'Failed to save storage configuration',
        })
      }
    },
  })

  // Handle storage config changes
  const handleStorageChange = (updatedStorage: StorageConfigType) => {
    // Update each field via updateConfigPath
    if (updatedStorage.connection !== storage?.connection) {
      updateConfigPath(['storage', 'connection'], updatedStorage.connection)
    }
    if (updatedStorage.results_table !== storage?.results_table) {
      updateConfigPath(['storage', 'results_table'], updatedStorage.results_table || null)
    }
    if (updatedStorage.runs_table !== storage?.runs_table) {
      updateConfigPath(['storage', 'runs_table'], updatedStorage.runs_table || null)
    }
    if (updatedStorage.create_tables !== storage?.create_tables) {
      updateConfigPath(['storage', 'create_tables'], updatedStorage.create_tables ?? true)
    }
  }

  // Handle save
  const handleSave = async () => {
    await saveMutation.mutateAsync()
  }

  // Handle test connection (refresh status)
  const handleTestConnection = async () => {
    await refetchStatus()
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
      })
    }
  }, [currentConfig, storage, updateConfigPath])

  if (isConfigLoading && !currentConfig) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-cyan-400 mx-auto" />
          <p className="mt-4 text-sm text-slate-400">Loading storage configuration...</p>
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
              ? 'The backend API endpoint is not implemented yet. The storage configuration UI is ready, but requires the backend API to be running.'
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
                // Initialize with default storage config for demo purposes
                updateConfigPath(['storage'], {
                  connection: {
                    type: 'postgres',
                    database: '',
                  },
                  results_table: 'baselinr_results',
                  runs_table: 'baselinr_runs',
                  create_tables: true,
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

  if (!storage) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-cyan-400 mx-auto" />
          <p className="mt-4 text-sm text-slate-400">Initializing storage configuration...</p>
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
          <span className="text-white font-medium">Storage</span>
        </div>
        <h1 className="text-2xl font-bold text-white">Storage Configuration</h1>
        <p className="mt-1 text-sm text-slate-400">
          Configure the database connection and table names for storing profiling results
        </p>
      </div>

      {/* Success Message */}
      {saveSuccess && (
        <div className="mb-6 glass-card border-emerald-500/30 bg-emerald-500/10 p-4 flex items-center gap-3">
          <CheckCircle className="w-5 h-5 text-emerald-400" />
          <p className="text-sm font-medium text-emerald-300">
            Storage configuration saved successfully
          </p>
        </div>
      )}

      {/* Error Message */}
      {storageErrors.general && (
        <div className="mb-6 glass-card border-rose-500/30 bg-rose-500/10 p-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400" />
          <p className="text-sm font-medium text-rose-300">{storageErrors.general}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Configuration Form */}
        <div className="lg:col-span-2">
          <Card className="p-6">
            <StorageConfig
              storage={storage}
              onChange={handleStorageChange}
              errors={storageErrors}
              isLoading={isConfigLoading || saveMutation.isPending}
              onTestConnection={handleTestConnection}
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

        {/* Status Panel */}
        <div className="lg:col-span-1">
          <StorageStatus
            status={storageStatus}
            isLoading={isLoadingStatus}
            error={statusError instanceof Error ? statusError.message : null}
            onRefresh={refetchStatus}
          />
        </div>
      </div>
    </div>
  )
}

