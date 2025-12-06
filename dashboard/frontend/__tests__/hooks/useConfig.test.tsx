/**
 * Unit tests for useConfig hook
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useConfig } from '@/hooks/useConfig'
import { useConfigStore } from '@/lib/store/configStore'
import { fetchConfig } from '@/lib/api/config'

// Mock the API
vi.mock('@/lib/api/config', () => ({
  fetchConfig: vi.fn(),
}))

// Mock the store
vi.mock('@/lib/store/configStore', () => ({
  useConfigStore: vi.fn(),
}))

describe('useConfig', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
    vi.clearAllMocks()
  })

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )

  it('should provide store state', () => {
    const mockStore = {
      currentConfig: null,
      modifiedConfig: null,
      originalConfig: null,
      isLoading: false,
      error: null,
      validationErrors: [],
      validationWarnings: [],
      lastSaved: null,
      isDirty: () => false,
      loadConfig: vi.fn(),
      updateConfig: vi.fn(),
      updateConfigPath: vi.fn(),
      resetConfig: vi.fn(),
      saveConfig: vi.fn(),
      validateConfig: vi.fn(),
      clearError: vi.fn(),
    }

    vi.mocked(useConfigStore).mockReturnValue(mockStore as any)

    const { result } = renderHook(() => useConfig(), { wrapper })

    expect(result.current.currentConfig).toBeNull()
    expect(result.current.isDirty).toBe(false)
    expect(result.current.hasChanges).toBe(false)
    expect(result.current.canSave).toBe(false)
  })

  it('should compute isDirty correctly', () => {
    const mockStore = {
      currentConfig: null,
      modifiedConfig: { source: { database: 'modified' } },
      originalConfig: { source: { database: 'original' } } as any,
      isLoading: false,
      error: null,
      validationErrors: [],
      validationWarnings: [],
      lastSaved: null,
      isDirty: () => true,
      loadConfig: vi.fn(),
      updateConfig: vi.fn(),
      updateConfigPath: vi.fn(),
      resetConfig: vi.fn(),
      saveConfig: vi.fn(),
      validateConfig: vi.fn(),
      clearError: vi.fn(),
    }

    vi.mocked(useConfigStore).mockReturnValue(mockStore as any)

    const { result } = renderHook(() => useConfig(), { wrapper })

    expect(result.current.isDirty).toBe(true)
    expect(result.current.hasChanges).toBe(true)
  })

  it('should provide action functions', () => {
    const mockLoadConfig = vi.fn()
    const mockUpdateConfig = vi.fn()
    const mockResetConfig = vi.fn()

    const mockStore = {
      currentConfig: null,
      modifiedConfig: null,
      originalConfig: null,
      isLoading: false,
      error: null,
      validationErrors: [],
      validationWarnings: [],
      lastSaved: null,
      isDirty: () => false,
      loadConfig: mockLoadConfig,
      updateConfig: mockUpdateConfig,
      updateConfigPath: vi.fn(),
      resetConfig: mockResetConfig,
      saveConfig: vi.fn(),
      validateConfig: vi.fn(),
      clearError: vi.fn(),
    }

    vi.mocked(useConfigStore).mockReturnValue(mockStore as any)

    const { result } = renderHook(() => useConfig(), { wrapper })

    result.current.loadConfig()
    expect(mockLoadConfig).toHaveBeenCalled()

    result.current.updateConfig({})
    expect(mockUpdateConfig).toHaveBeenCalled()

    result.current.resetConfig()
    expect(mockResetConfig).toHaveBeenCalled()
  })
})

