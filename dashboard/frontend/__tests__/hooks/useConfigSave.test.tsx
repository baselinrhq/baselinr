/**
 * Unit tests for useConfigSave hook
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useConfigSave } from '@/hooks/useConfigSave'
import { useConfigStore } from '@/lib/store/configStore'
import { saveConfig } from '@/lib/api/config'

// Mock the API
vi.mock('@/lib/api/config', () => ({
  saveConfig: vi.fn(),
}))

// Mock the store
vi.mock('@/lib/store/configStore', () => ({
  useConfigStore: vi.fn(),
}))

describe('useConfigSave', () => {
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

  it('should provide save functionality', () => {
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
      getState: () => ({
        originalConfig: null,
        modifiedConfig: null,
      }),
      setState: vi.fn(),
    }

    vi.mocked(useConfigStore).mockReturnValue(mockStore as any)

    const { result } = renderHook(() => useConfigSave(), { wrapper })

    expect(result.current.saveConfig).toBeDefined()
    expect(result.current.isSaving).toBe(false)
    expect(result.current.canSave).toBe(false)
  })

  it('should indicate canSave when config is dirty and no validation errors', () => {
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
      getState: () => ({
        originalConfig: { source: { database: 'original' } },
        modifiedConfig: { source: { database: 'modified' } },
      }),
      setState: vi.fn(),
    }

    vi.mocked(useConfigStore).mockReturnValue(mockStore as any)

    const { result } = renderHook(() => useConfigSave(), { wrapper })

    expect(result.current.canSave).toBe(true)
  })

  it('should indicate cannot save when validation errors exist', () => {
    const mockStore = {
      currentConfig: null,
      modifiedConfig: { source: { database: 'modified' } },
      originalConfig: { source: { database: 'original' } } as any,
      isLoading: false,
      error: null,
      validationErrors: ['Error 1'],
      validationWarnings: [],
      lastSaved: null,
      isDirty: () => true,
      getState: () => ({
        originalConfig: { source: { database: 'original' } },
        modifiedConfig: { source: { database: 'modified' } },
      }),
      setState: vi.fn(),
    }

    vi.mocked(useConfigStore).mockReturnValue(mockStore as any)

    const { result } = renderHook(() => useConfigSave(), { wrapper })

    expect(result.current.canSave).toBe(false)
  })
})

