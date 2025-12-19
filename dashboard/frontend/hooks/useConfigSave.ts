/**
 * React hook for configuration save operations with optimistic updates
 * 
 * Specialized hook for save operations with optimistic UI updates
 */

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useConfigStore } from '@/lib/store/configStore'
import { saveConfig as saveConfigAPI } from '@/lib/api/config'
import { useCallback } from 'react'
import type { BaselinrConfig } from '@/types/config'

/**
 * Deep merge utility
 */
function deepMerge(target: any, source: any): any {
  const output = { ...target }
  if (isObject(target) && isObject(source)) {
    Object.keys(source).forEach((key) => {
      if (isObject(source[key])) {
        if (!(key in target)) {
          Object.assign(output, { [key]: source[key] })
        } else {
          output[key] = deepMerge(target[key], source[key])
        }
      } else {
        Object.assign(output, { [key]: source[key] })
      }
    })
  }
  return output
}

function isObject(item: any): boolean {
  return item && typeof item === 'object' && !Array.isArray(item)
}

export function useConfigSave() {
  const queryClient = useQueryClient()
  const store = useConfigStore()

  // Save mutation with optimistic updates
  const saveMutation = useMutation({
    mutationFn: async () => {
      const { originalConfig, modifiedConfig } = useConfigStore.getState()
      
      if (!originalConfig) {
        throw new Error('Cannot save: no configuration loaded')
      }

      // Merge original with modifications
      const configToSave = modifiedConfig
        ? deepMerge(originalConfig, modifiedConfig)
        : originalConfig

      return await saveConfigAPI(configToSave)
    },
    onMutate: async () => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['config'] })

      // Snapshot the previous value for rollback
      const previousConfig = store.currentConfig
      const previousOriginal = store.originalConfig
      const previousModified = store.modifiedConfig

      // Optimistically update the store
      const { originalConfig, modifiedConfig } = useConfigStore.getState()
      if (originalConfig && modifiedConfig) {
        const optimisticConfig = deepMerge(originalConfig, modifiedConfig)
        useConfigStore.setState({
          currentConfig: optimisticConfig,
          originalConfig: JSON.parse(JSON.stringify(optimisticConfig)),
          modifiedConfig: null,
          lastSaved: new Date().toISOString(),
        })
      }

      // Return context with snapshot for rollback
      return { previousConfig, previousOriginal, previousModified }
    },
    onError: (error, variables, context) => {
      // Rollback on error
      if (context) {
        useConfigStore.setState({
          currentConfig: context.previousConfig,
          originalConfig: context.previousOriginal,
          modifiedConfig: context.previousModified,
          error: error instanceof Error ? error.message : 'Failed to save configuration',
        })
      }
    },
    onSuccess: (data) => {
      // Update with server response
      const savedConfig = data.config
      useConfigStore.setState({
        currentConfig: savedConfig,
        originalConfig: JSON.parse(JSON.stringify(savedConfig)),
        modifiedConfig: null,
        error: null,
        validationErrors: [],
        validationWarnings: [],
        lastSaved: new Date().toISOString(),
      })

      // Update query cache
      queryClient.setQueryData(['config'], data)
    },
    onSettled: () => {
      // Always refetch after error or success
      queryClient.invalidateQueries({ queryKey: ['config'] })
    },
  })

  const saveConfig = useCallback(async () => {
    return saveMutation.mutateAsync()
  }, [saveMutation])

  const isDirty = store.isDirty()
  const canSave = isDirty && !saveMutation.isPending && store.validationErrors.length === 0

  return {
    saveConfig,
    isSaving: saveMutation.isPending,
    saveError: saveMutation.error instanceof Error ? saveMutation.error.message : null,
    lastSaved: store.lastSaved,
    canSave,
  }
}

