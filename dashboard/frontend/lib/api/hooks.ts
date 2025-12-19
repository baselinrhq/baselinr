/**
 * API client for Baselinr hook management endpoints
 */

import {
  HookWithId,
  HooksListResponse,
  SaveHookResponse,
  HookTestResponse,
} from '@/types/hook'
import { HookConfig } from '@/types/config'
import { getApiUrl } from '../demo-mode'

const API_URL = getApiUrl()

/**
 * Custom error class for hook API errors
 */
export class HookError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: unknown
  ) {
    super(message)
    this.name = 'HookError'
  }
}

/**
 * Custom error class for hook test errors
 */
export class HookTestError extends HookError {
  constructor(message: string, public testError?: string) {
    super(message, 400)
    this.name = 'HookTestError'
  }
}

/**
 * Helper function to parse API error responses
 */
async function parseErrorResponse(response: Response): Promise<string> {
  try {
    const errorData = await response.json()
    return errorData.detail || errorData.message || errorData.error || response.statusText
  } catch {
    return response.statusText
  }
}

/**
 * Get all hooks
 * 
 * @returns List of all configured hooks
 * @throws {HookError} If the request fails
 */
export async function fetchHooks(): Promise<HooksListResponse> {
  try {
    const url = `${API_URL}/api/config/hooks`
    const response = await fetch(url)

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new HookError(
        `Failed to fetch hooks: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof HookError) {
      throw error
    }
    throw new HookError(
      `Failed to fetch hooks: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Get specific hook by ID
 * 
 * @param hookId - Hook identifier
 * @returns Hook details
 * @throws {HookError} If the request fails or hook not found
 */
export async function fetchHook(hookId: string): Promise<HookWithId> {
  try {
    const url = `${API_URL}/api/config/hooks/${encodeURIComponent(hookId)}`
    const response = await fetch(url)

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      
      if (response.status === 404) {
        throw new HookError(
          `Hook not found: ${hookId}`,
          404
        )
      }
      
      throw new HookError(
        `Failed to fetch hook: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof HookError) {
      throw error
    }
    throw new HookError(
      `Failed to fetch hook: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Create new hook
 * 
 * @param hook - Hook configuration
 * @returns Created hook with ID
 * @throws {HookError} If the request fails
 */
export async function createHook(hook: HookConfig): Promise<SaveHookResponse> {
  try {
    const url = `${API_URL}/api/config/hooks`
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ hook }),
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      
      if (response.status === 400) {
        throw new HookError(
          `Invalid hook configuration: ${errorMessage}`,
          400
        )
      }
      
      throw new HookError(
        `Failed to create hook: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof HookError) {
      throw error
    }
    throw new HookError(
      `Failed to create hook: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Update existing hook
 * 
 * @param hookId - Hook identifier
 * @param hook - Updated hook configuration
 * @returns Updated hook with ID
 * @throws {HookError} If the request fails
 */
export async function updateHook(
  hookId: string,
  hook: HookConfig
): Promise<SaveHookResponse> {
  try {
    const url = `${API_URL}/api/config/hooks/${encodeURIComponent(hookId)}`
    const response = await fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ hook }),
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      
      if (response.status === 400) {
        throw new HookError(
          `Invalid hook configuration: ${errorMessage}`,
          400
        )
      }
      
      if (response.status === 404) {
        throw new HookError(
          `Hook not found: ${hookId}`,
          404
        )
      }
      
      throw new HookError(
        `Failed to update hook: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof HookError) {
      throw error
    }
    throw new HookError(
      `Failed to update hook: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Delete hook
 * 
 * @param hookId - Hook identifier
 * @throws {HookError} If the request fails
 */
export async function deleteHook(hookId: string): Promise<void> {
  try {
    const url = `${API_URL}/api/config/hooks/${encodeURIComponent(hookId)}`
    const response = await fetch(url, {
      method: 'DELETE',
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      
      if (response.status === 404) {
        throw new HookError(
          `Hook not found: ${hookId}`,
          404
        )
      }
      
      throw new HookError(
        `Failed to delete hook: ${errorMessage}`,
        response.status
      )
    }
  } catch (error) {
    if (error instanceof HookError) {
      throw error
    }
    throw new HookError(
      `Failed to delete hook: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Test hook
 * 
 * @param hookId - Hook identifier (optional if hook config provided)
 * @param hook - Optional hook configuration to test (if not provided, uses saved hook)
 * @returns Test result
 * @throws {HookTestError} If the test fails
 * @throws {HookError} If the request fails
 */
export async function testHook(
  hookId: string,
  hook?: HookConfig | null
): Promise<HookTestResponse> {
  try {
    const url = `${API_URL}/api/config/hooks/${encodeURIComponent(hookId)}/test`
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ hook: hook || null }),
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      
      if (response.status === 404) {
        throw new HookError(
          `Hook not found: ${hookId}`,
          404
        )
      }
      
      throw new HookTestError(errorMessage)
    }

    const result = await response.json()
    
    // If the response indicates failure, throw HookTestError
    if (!result.success) {
      throw new HookTestError(
        result.message || 'Hook test failed',
        result.error
      )
    }

    return result
  } catch (error) {
    if (error instanceof HookTestError || error instanceof HookError) {
      throw error
    }
    throw new HookTestError(
      `Failed to test hook: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Set master switch for all hooks
 * 
 * @param enabled - Whether hooks are enabled
 * @throws {HookError} If the request fails
 */
export async function setHooksEnabled(enabled: boolean): Promise<void> {
  try {
    const url = `${API_URL}/api/config/hooks/enabled?enabled=${enabled}`
    const response = await fetch(url, {
      method: 'PUT',
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new HookError(
        `Failed to set hooks enabled: ${errorMessage}`,
        response.status
      )
    }
  } catch (error) {
    if (error instanceof HookError) {
      throw error
    }
    throw new HookError(
      `Failed to set hooks enabled: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

