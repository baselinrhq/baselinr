/**
 * Unit tests for configStore
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useConfigStore } from '@/lib/store/configStore'
import { fetchConfig, saveConfig, validateConfig } from '@/lib/api/config'
import type { BaselinrConfig } from '@/types/config'

// Mock the API functions
vi.mock('@/lib/api/config', () => ({
  fetchConfig: vi.fn(),
  saveConfig: vi.fn(),
  validateConfig: vi.fn(),
}))

describe('configStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useConfigStore.setState({
      currentConfig: null,
      modifiedConfig: null,
      originalConfig: null,
      isLoading: false,
      error: null,
      validationErrors: [],
      validationWarnings: [],
      lastSaved: null,
    })
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('should have null initial state', () => {
      const state = useConfigStore.getState()
      expect(state.currentConfig).toBeNull()
      expect(state.modifiedConfig).toBeNull()
      expect(state.originalConfig).toBeNull()
      expect(state.isDirty()).toBe(false)
    })
  })

  describe('loadConfig', () => {
    it('should load configuration successfully', async () => {
      const mockConfig: BaselinrConfig = {
        environment: 'development',
        source: {
          type: 'postgres',
          database: 'test_db',
        },
        storage: {
          connection: {
            type: 'postgres',
            database: 'test_db',
          },
        },
      }

      vi.mocked(fetchConfig).mockResolvedValue({
        config: mockConfig,
      })

      await useConfigStore.getState().loadConfig()

      const state = useConfigStore.getState()
      expect(state.currentConfig).toEqual(mockConfig)
      expect(state.originalConfig).toEqual(mockConfig)
      expect(state.modifiedConfig).toBeNull()
      expect(state.isLoading).toBe(false)
      expect(state.error).toBeNull()
    })

    it('should handle load errors', async () => {
      const errorMessage = 'Failed to fetch config'
      vi.mocked(fetchConfig).mockRejectedValue(new Error(errorMessage))

      await expect(useConfigStore.getState().loadConfig()).rejects.toThrow()

      const state = useConfigStore.getState()
      expect(state.isLoading).toBe(false)
      expect(state.error).toBe(errorMessage)
    })
  })

  describe('updateConfig', () => {
    it('should update modified config', () => {
      const originalConfig: BaselinrConfig = {
        environment: 'development',
        source: {
          type: 'postgres',
          database: 'original_db',
        },
        storage: {
          connection: {
            type: 'postgres',
            database: 'original_db',
          },
        },
      }

      useConfigStore.setState({ originalConfig })

      useConfigStore.getState().updateConfig({
        source: {
          type: 'postgres',
          database: 'updated_db',
        },
      })

      const state = useConfigStore.getState()
      expect(state.modifiedConfig).toMatchObject({
        source: {
          database: 'updated_db',
        },
      })
      expect(state.modifiedConfig?.source?.database).toBe('updated_db')
    })
  })

  describe('updateConfigPath', () => {
    it('should update nested config value by path', () => {
      const originalConfig: BaselinrConfig = {
        environment: 'development',
        source: {
          type: 'postgres',
          database: 'test_db',
        },
        storage: {
          connection: {
            type: 'postgres',
            database: 'test_db',
          },
        },
      }

      useConfigStore.setState({ originalConfig })

      useConfigStore.getState().updateConfigPath(['source', 'database'], 'new_db')

      const state = useConfigStore.getState()
      expect(state.modifiedConfig).toEqual({
        source: {
          database: 'new_db',
        },
      })
    })
  })

  describe('resetConfig', () => {
    it('should reset modified config to null', () => {
      useConfigStore.setState({
        modifiedConfig: {
          source: {
            database: 'modified_db',
          },
        },
        validationErrors: ['error1'],
        validationWarnings: ['warning1'],
      })

      useConfigStore.getState().resetConfig()

      const state = useConfigStore.getState()
      expect(state.modifiedConfig).toBeNull()
      expect(state.validationErrors).toEqual([])
      expect(state.validationWarnings).toEqual([])
    })
  })

  describe('isDirty', () => {
    it('should return false when no modifications', () => {
      const config: BaselinrConfig = {
        environment: 'development',
        source: {
          type: 'postgres',
          database: 'test_db',
        },
        storage: {
          connection: {
            type: 'postgres',
            database: 'test_db',
          },
        },
      }

      useConfigStore.setState({
        originalConfig: config,
        modifiedConfig: null,
      })

      expect(useConfigStore.getState().isDirty()).toBe(false)
    })

    it('should return true when modifications exist', () => {
      const originalConfig: BaselinrConfig = {
        environment: 'development',
        source: {
          type: 'postgres',
          database: 'original_db',
        },
        storage: {
          connection: {
            type: 'postgres',
            database: 'original_db',
          },
        },
      }

      useConfigStore.setState({
        originalConfig,
        modifiedConfig: {
          source: {
            database: 'modified_db',
          },
        },
      })

      expect(useConfigStore.getState().isDirty()).toBe(true)
    })
  })

  describe('saveConfig', () => {
    it('should save configuration successfully', async () => {
      const originalConfig: BaselinrConfig = {
        environment: 'development',
        source: {
          type: 'postgres',
          database: 'test_db',
        },
        storage: {
          connection: {
            type: 'postgres',
            database: 'test_db',
          },
        },
      }

      const savedConfig: BaselinrConfig = {
        ...originalConfig,
        source: {
          ...originalConfig.source,
          database: 'saved_db',
        },
      }

      useConfigStore.setState({
        originalConfig,
        modifiedConfig: {
          source: {
            database: 'saved_db',
          },
        },
      })

      vi.mocked(saveConfig).mockResolvedValue({
        config: savedConfig,
      })

      await useConfigStore.getState().saveConfig()

      const state = useConfigStore.getState()
      expect(state.currentConfig).toEqual(savedConfig)
      expect(state.originalConfig).toEqual(savedConfig)
      expect(state.modifiedConfig).toBeNull()
      expect(state.lastSaved).toBeTruthy()
    })
  })

  describe('validateConfig', () => {
    it('should validate configuration successfully', async () => {
      const config: BaselinrConfig = {
        environment: 'development',
        source: {
          type: 'postgres',
          database: 'test_db',
        },
        storage: {
          connection: {
            type: 'postgres',
            database: 'test_db',
          },
        },
      }

      useConfigStore.setState({
        originalConfig: config,
      })

      vi.mocked(validateConfig).mockResolvedValue({
        valid: true,
        errors: [],
        warnings: [],
      })

      const isValid = await useConfigStore.getState().validateConfig()

      expect(isValid).toBe(true)
      const state = useConfigStore.getState()
      expect(state.validationErrors).toEqual([])
      expect(state.validationWarnings).toEqual([])
    })

    it('should handle validation errors', async () => {
      const config: BaselinrConfig = {
        environment: 'development',
        source: {
          type: 'postgres',
          database: 'test_db',
        },
        storage: {
          connection: {
            type: 'postgres',
            database: 'test_db',
          },
        },
      }

      useConfigStore.setState({
        originalConfig: config,
      })

      vi.mocked(validateConfig).mockResolvedValue({
        valid: false,
        errors: ['Error 1', 'Error 2'],
        warnings: ['Warning 1'],
      })

      const isValid = await useConfigStore.getState().validateConfig()

      expect(isValid).toBe(false)
      const state = useConfigStore.getState()
      expect(state.validationErrors).toEqual(['Error 1', 'Error 2'])
      expect(state.validationWarnings).toEqual(['Warning 1'])
    })
  })
})

