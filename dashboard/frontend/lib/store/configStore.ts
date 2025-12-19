/**
 * Zustand store for configuration state management
 * 
 * Manages configuration editing state with dirty checking and validation
 */

import { create } from 'zustand'
import type { BaselinrConfig } from '@/types/config'
import { fetchConfig, saveConfig as saveConfigAPI, validateConfig as validateConfigAPI } from '@/lib/api/config'

interface ConfigStore {
  // State
  currentConfig: BaselinrConfig | null
  modifiedConfig: Partial<BaselinrConfig> | null
  originalConfig: BaselinrConfig | null
  isLoading: boolean
  error: string | null
  validationErrors: string[]
  validationWarnings: string[]
  lastSaved: string | null

  // Computed (getters)
  isDirty: () => boolean

  // Actions
  loadConfig: () => Promise<void>
  updateConfig: (updates: Partial<BaselinrConfig>) => void
  updateConfigPath: (path: string[], value: unknown) => void
  resetConfig: () => void
  saveConfig: () => Promise<void>
  validateConfig: () => Promise<boolean>
  setError: (error: string | null) => void
  clearError: () => void
}

/**
 * Deep comparison utility for dirty checking
 */
function deepEqual(obj1: unknown, obj2: unknown): boolean {
  if (obj1 === obj2) return true
  if (obj1 == null || obj2 == null) return false
  if (typeof obj1 !== 'object' || typeof obj2 !== 'object') return false

  const keys1 = Object.keys(obj1)
  const keys2 = Object.keys(obj2)

  if (keys1.length !== keys2.length) return false

  for (const key of keys1) {
    if (!keys2.includes(key)) return false
    if (!deepEqual(obj1[key], obj2[key])) return false
  }

  return true
}

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

/**
 * Set nested value by path array
 */
function setNestedValue(obj: Record<string, unknown>, path: string[], value: unknown): Record<string, unknown> {
  const result = { ...obj }
  let current: Record<string, unknown> = result

  for (let i = 0; i < path.length - 1; i++) {
    const key = path[i]
    if (!(key in current) || !isObject(current[key])) {
      current[key] = {}
    } else {
      current[key] = { ...(current[key] as Record<string, unknown>) }
    }
    current = current[key] as Record<string, unknown>
  }

  current[path[path.length - 1]] = value
  return result
}

export const useConfigStore = create<ConfigStore>((set, get) => ({
  // Initial state
  currentConfig: null,
  modifiedConfig: null,
  originalConfig: null,
  isLoading: false,
  error: null,
  validationErrors: [],
  validationWarnings: [],
  lastSaved: null,

  // Computed: Check if config is dirty
  isDirty: () => {
    const { originalConfig, modifiedConfig } = get()
    if (!originalConfig || !modifiedConfig) return false
    
    // Merge original with modifications to get full config
    const mergedConfig = deepMerge(originalConfig as unknown as Record<string, unknown>, modifiedConfig as unknown as Record<string, unknown>)
    return !deepEqual(originalConfig, mergedConfig)
  },

  // Load configuration from API
  loadConfig: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await fetchConfig()
      const config = response.config
      set({
        currentConfig: config,
        originalConfig: JSON.parse(JSON.stringify(config)), // Deep clone
        modifiedConfig: null,
        isLoading: false,
        error: null,
        validationErrors: [],
        validationWarnings: [],
      })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load configuration'
      set({
        isLoading: false,
        error: errorMessage,
      })
      throw error
    }
  },

  // Update modified config
  updateConfig: (updates: Partial<BaselinrConfig>) => {
    const { modifiedConfig } = get()
    const currentModified = modifiedConfig || {}
    const newModified = deepMerge(currentModified, updates)
    
    set({ modifiedConfig: newModified })
  },

  // Update nested config value by path
  updateConfigPath: (path: string[], value: unknown) => {
    const { modifiedConfig, originalConfig } = get()
    
    if (!originalConfig) {
      throw new Error('Cannot update config: no original config loaded')
    }

    // Start with original config merged with current modifications
    const baseConfig = modifiedConfig 
      ? deepMerge(originalConfig as unknown as Record<string, unknown>, modifiedConfig as unknown as Record<string, unknown>) as unknown as BaselinrConfig
      : originalConfig
    
    // Set the nested value
    const updatedConfig = setNestedValue(baseConfig as unknown as Record<string, unknown>, path, value) as unknown as BaselinrConfig
    
    // Calculate the diff (what changed from original)
    const diff = getConfigDiff(originalConfig as unknown as Record<string, unknown>, updatedConfig as unknown as Record<string, unknown>)
    
    set({ modifiedConfig: diff as Partial<BaselinrConfig> })
  },

  // Reset modified config to original
  resetConfig: () => {
    set({
      modifiedConfig: null,
      validationErrors: [],
      validationWarnings: [],
      error: null,
    })
  },

  // Save configuration
  saveConfig: async () => {
    const { originalConfig, modifiedConfig } = get()
    
    if (!originalConfig) {
      throw new Error('Cannot save: no configuration loaded')
    }

    // Merge original with modifications
    const configToSave = modifiedConfig
      ? deepMerge(originalConfig as unknown as Record<string, unknown>, modifiedConfig as unknown as Record<string, unknown>) as unknown as BaselinrConfig
      : originalConfig

    set({ isLoading: true, error: null })
    
    try {
      const response = await saveConfigAPI(configToSave)
      const savedConfig = response.config
      
      set({
        currentConfig: savedConfig,
        originalConfig: JSON.parse(JSON.stringify(savedConfig)), // Deep clone
        modifiedConfig: null,
        isLoading: false,
        error: null,
        lastSaved: new Date().toISOString(),
        validationErrors: [],
        validationWarnings: [],
      })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to save configuration'
      set({
        isLoading: false,
        error: errorMessage,
      })
      throw error
    }
  },

  // Validate configuration
  validateConfig: async () => {
    const { originalConfig, modifiedConfig } = get()
    
    if (!originalConfig) {
      throw new Error('Cannot validate: no configuration loaded')
    }

    // Merge original with modifications
    const configToValidate = modifiedConfig
      ? deepMerge(originalConfig as unknown as Record<string, unknown>, modifiedConfig as unknown as Record<string, unknown>) as unknown as BaselinrConfig
      : originalConfig

    set({ isLoading: true, error: null })
    
    try {
      const result = await validateConfigAPI(configToValidate)
      
      set({
        isLoading: false,
        validationErrors: result.errors || [],
        validationWarnings: result.warnings || [],
        error: result.valid ? null : 'Validation failed',
      })
      
      return result.valid
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to validate configuration'
      set({
        isLoading: false,
        error: errorMessage,
        validationErrors: [],
        validationWarnings: [],
      })
      throw error
    }
  },

  // Set error state
  setError: (error: string | null) => {
    set({ error })
  },

  // Clear error state
  clearError: () => {
    set({ error: null })
  },
}))

/**
 * Helper function to calculate diff between original and updated config
 * Returns only the changed paths
 */
function getConfigDiff(original: Record<string, unknown>, updated: Record<string, unknown>, path: string[] = []): Record<string, unknown> | undefined {
  if (original === updated) return undefined
  
  if (!isObject(original) || !isObject(updated)) {
    return updated
  }

  const diff: Record<string, unknown> = {}
  const allKeys = new Set([...Object.keys(original), ...Object.keys(updated)])

  for (const key of Array.from(allKeys)) {
    const originalValue = original[key]
    const updatedValue = updated[key]
    const currentPath = [...path, key]

    if (!(key in original)) {
      // New key added
      diff[key] = updatedValue
    } else if (!(key in updated)) {
      // Key removed (shouldn't happen in our case, but handle it)
      continue
    } else if (!deepEqual(originalValue, updatedValue)) {
      if (isObject(originalValue) && isObject(updatedValue)) {
        const nestedDiff = getConfigDiff(originalValue as Record<string, unknown>, updatedValue as Record<string, unknown>, currentPath)
        if (nestedDiff !== undefined && Object.keys(nestedDiff).length > 0) {
          diff[key] = nestedDiff
        }
      } else {
        diff[key] = updatedValue
      }
    }
  }

  return Object.keys(diff).length > 0 ? diff : undefined
}

