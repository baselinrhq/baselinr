/**
 * Unit tests for hooks API client
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  fetchHooks,
  fetchHook,
  createHook,
  updateHook,
  deleteHook,
  testHook,
  setHooksEnabled,
  HookError,
  HookTestError,
} from '@/lib/api/hooks'
import type { HookConfig } from '@/types/config'
import type { HookWithId, HooksListResponse, SaveHookResponse, HookTestResponse } from '@/types/hook'

// Mock fetch globally
global.fetch = vi.fn()

describe('hooks API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('fetchHooks', () => {
    it('should list hooks successfully', async () => {
      const mockResponse: HooksListResponse = {
        hooks: [
          {
            id: '0',
            hook: {
              type: 'logging',
              enabled: true,
              log_level: 'INFO',
            },
          },
        ],
        total: 1,
        hooks_enabled: true,
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await fetchHooks()

      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/config/hooks')
      )
    })

    it('should throw HookError on failure', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ detail: 'Server error' }),
      } as Response)

      await expect(fetchHooks()).rejects.toThrow(HookError)
    })
  })

  describe('fetchHook', () => {
    it('should get hook by ID successfully', async () => {
      const mockHook: HookWithId = {
        id: '0',
        hook: {
          type: 'logging',
          enabled: true,
          log_level: 'INFO',
        },
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockHook,
      } as Response)

      const result = await fetchHook('0')

      expect(result).toEqual(mockHook)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/config/hooks/0')
      )
    })

    it('should throw HookError when hook not found', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ detail: 'Hook not found: 0' }),
      } as Response)

      await expect(fetchHook('0')).rejects.toThrow(HookError)
    })
  })

  describe('createHook', () => {
    it('should create hook successfully', async () => {
      const hookConfig: HookConfig = {
        type: 'logging',
        enabled: true,
        log_level: 'INFO',
      }

      const mockResponse: SaveHookResponse = {
        id: '0',
        hook: {
          id: '0',
          hook: hookConfig,
        },
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await createHook(hookConfig)

      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/config/hooks'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ hook: hookConfig }),
        })
      )
    })

    it('should throw HookError on validation failure', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({ detail: 'Invalid hook configuration' }),
      } as Response)

      await expect(createHook({ type: 'invalid' as any })).rejects.toThrow(HookError)
    })
  })

  describe('updateHook', () => {
    it('should update hook successfully', async () => {
      const hookConfig: HookConfig = {
        type: 'logging',
        enabled: true,
        log_level: 'DEBUG',
      }

      const mockResponse: SaveHookResponse = {
        id: '0',
        hook: {
          id: '0',
          hook: hookConfig,
        },
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await updateHook('0', hookConfig)

      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/config/hooks/0'),
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify({ hook: hookConfig }),
        })
      )
    })
  })

  describe('deleteHook', () => {
    it('should delete hook successfully', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'Hook deleted successfully' }),
      } as Response)

      await deleteHook('0')

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/config/hooks/0'),
        expect.objectContaining({
          method: 'DELETE',
        })
      )
    })

    it('should throw HookError when hook not found', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ detail: 'Hook not found: 0' }),
      } as Response)

      await expect(deleteHook('0')).rejects.toThrow(HookError)
    })
  })

  describe('testHook', () => {
    it('should test hook successfully', async () => {
      const mockResponse: HookTestResponse = {
        success: true,
        message: 'Hook test successful',
        error: null,
        test_event: {
          event_type: 'DataDriftDetected',
          timestamp: '2024-01-01T00:00:00Z',
        },
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await testHook('0')

      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/config/hooks/0/test'),
        expect.objectContaining({
          method: 'POST',
        })
      )
    })

    it('should test hook with provided config', async () => {
      const hookConfig: HookConfig = {
        type: 'slack',
        enabled: true,
        webhook_url: 'https://hooks.slack.com/test',
      }

      const mockResponse: HookTestResponse = {
        success: true,
        message: 'Hook test successful',
        error: null,
        test_event: null,
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      await testHook('0', hookConfig)

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/config/hooks/0/test'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ hook: hookConfig }),
        })
      )
    })

    it('should throw HookTestError on test failure', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: false,
          message: 'Hook test failed',
          error: 'Connection error',
        }),
      } as Response)

      await expect(testHook('0')).rejects.toThrow(HookTestError)
    })
  })

  describe('setHooksEnabled', () => {
    it('should set hooks enabled successfully', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ enabled: true, message: 'Hooks enabled' }),
      } as Response)

      await setHooksEnabled(true)

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/config/hooks/enabled?enabled=true'),
        expect.objectContaining({
          method: 'PUT',
        })
      )
    })

    it('should throw HookError on failure', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ detail: 'Server error' }),
      } as Response)

      await expect(setHooksEnabled(true)).rejects.toThrow(HookError)
    })
  })
})

