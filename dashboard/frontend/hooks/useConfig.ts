/**
 * React hook for configuration state management
 * 
 * Provides access to config store with TanStack Query integration
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useConfigStore } from '@/lib/store/configStore'
import { fetchConfig } from '@/lib/api/config'
import { useCallback } from 'react'

export function useConfig() {
  const queryClient = useQueryClient()
  
  // Get store state and actions
  const store = useConfigStore()
  
  // TanStack Query for loading config
  const {
    data: configData,
    isLoading: isLoadingQuery,
    error: queryError,
  } = useQuery({
    queryKey: ['config'],
    queryFn: fetchConfig,
    enabled: false, // Don't auto-fetch, use loadConfig action instead
    staleTime: 60 * 1000, // 1 minute
  })

  // Load config action (uses both store and query)
  const loadConfig = useCallback(async () => {
    await store.loadConfig()
    // Also update query cache
    if (store.currentConfig) {
      queryClient.setQueryData(['config'], { config: store.currentConfig })
    }
  }, [store, queryClient])

  // Save config mutation
  const saveMutation = useMutation({
    mutationFn: async () => {
      await store.saveConfig()
      // Invalidate and refetch
      await queryClient.invalidateQueries({ queryKey: ['config'] })
    },
    onSuccess: () => {
      // Store handles state updates
    },
    onError: (error) => {
      // Store handles error state
    },
  })

  // Validate config mutation
  const validateMutation = useMutation({
    mutationFn: async () => {
      return await store.validateConfig()
    },
  })

  // Wrapper functions
  const saveConfig = useCallback(async () => {
    return saveMutation.mutateAsync()
  }, [saveMutation])

  const validateConfig = useCallback(async () => {
    return validateMutation.mutateAsync()
  }, [validateMutation])

  // Computed values
  const isDirty = store.isDirty()
  const isLoading = store.isLoading || isLoadingQuery || saveMutation.isPending || validateMutation.isPending
  const hasChanges = isDirty
  const canSave = hasChanges && !isLoading && store.validationErrors.length === 0

  return {
    // State
    currentConfig: store.currentConfig,
    modifiedConfig: store.modifiedConfig,
    originalConfig: store.originalConfig,
    isDirty,
    isLoading,
    error: store.error || (queryError instanceof Error ? queryError.message : null),
    validationErrors: store.validationErrors,
    validationWarnings: store.validationWarnings,
    lastSaved: store.lastSaved,

    // Actions
    loadConfig,
    updateConfig: store.updateConfig,
    updateConfigPath: store.updateConfigPath,
    resetConfig: store.resetConfig,
    saveConfig,
    validateConfig,
    clearError: store.clearError,

    // Computed
    hasChanges,
    canSave,
  }
}

