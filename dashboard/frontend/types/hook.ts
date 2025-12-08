/**
 * TypeScript type definitions for hook management API
 */

import { HookConfig } from './config'

/**
 * Hook with ID (array index)
 */
export interface HookWithId {
  id: string
  hook: HookConfig
  last_tested?: string | null
  test_status?: string | null
}

/**
 * Hooks list response
 */
export interface HooksListResponse {
  hooks: HookWithId[]
  total: number
  hooks_enabled: boolean
}

/**
 * Save hook request
 */
export interface SaveHookRequest {
  hook: HookConfig
}

/**
 * Save hook response
 */
export interface SaveHookResponse {
  id: string
  hook: HookWithId
}

/**
 * Hook test request
 */
export interface HookTestRequest {
  hook?: HookConfig | null
}

/**
 * Hook test response
 */
export interface HookTestResponse {
  success: boolean
  message: string
  error?: string | null
  test_event?: Record<string, any> | null
}

