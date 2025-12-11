/**
 * API client for Baselinr configuration endpoints
 */

import {
  BaselinrConfig,
  ConnectionConfig,
  ConfigResponse,
  ConfigValidationResponse,
  ConnectionTestResponse,
  ConfigHistoryResponse,
  ConfigVersionResponse,
  StorageStatusResponse,
} from '@/types/config'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Custom error class for configuration API errors
 */
export class ConfigError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: unknown
  ) {
    super(message)
    this.name = 'ConfigError'
  }
}

/**
 * Custom error class for validation errors
 */
export class ValidationError extends ConfigError {
  constructor(message: string, public validationErrors?: string[]) {
    super(message, 400)
    this.name = 'ValidationError'
  }
}

/**
 * Custom error class for connection test errors
 */
export class ConnectionTestError extends ConfigError {
  constructor(message: string, public connectionError?: string) {
    super(message, 400)
    this.name = 'ConnectionTestError'
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
 * Get current configuration
 * 
 * @returns Current Baselinr configuration
 * @throws {ConfigError} If the request fails
 */
export async function fetchConfig(): Promise<ConfigResponse> {
  try {
    const url = `${API_URL}/api/config`
    const response = await fetch(url)

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new ConfigError(
        `Failed to fetch configuration: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof ConfigError) {
      throw error
    }
    throw new ConfigError(
      `Failed to fetch configuration: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Save configuration
 * 
 * @param config - Baselinr configuration to save
 * @returns Updated configuration response
 * @throws {ConfigError} If the request fails
 * @throws {ValidationError} If the configuration is invalid
 */
export async function saveConfig(config: BaselinrConfig): Promise<ConfigResponse> {
  try {
    const url = `${API_URL}/api/config`
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ config }),
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      
      if (response.status === 400) {
        // Try to extract validation errors
        try {
          const errorData = await response.json()
          const validationErrors = errorData.errors || errorData.validation_errors
          if (validationErrors) {
            throw new ValidationError(errorMessage, validationErrors)
          }
        } catch {
          // If parsing fails, just throw ValidationError with message
        }
        throw new ValidationError(errorMessage)
      }
      
      throw new ConfigError(
        `Failed to save configuration: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof ConfigError || error instanceof ValidationError) {
      throw error
    }
    throw new ConfigError(
      `Failed to save configuration: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Validate configuration
 * 
 * @param config - Partial Baselinr configuration to validate
 * @returns Validation result with errors and warnings
 * @throws {ConfigError} If the request fails
 */
export async function validateConfig(
  config: Partial<BaselinrConfig>
): Promise<ConfigValidationResponse> {
  try {
    const url = `${API_URL}/api/config/validate`
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ config }),
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new ConfigError(
        `Failed to validate configuration: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof ConfigError) {
      throw error
    }
    throw new ConfigError(
      `Failed to validate configuration: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Test database connection
 * 
 * @param connectionConfig - Connection configuration to test
 * @returns Connection test result
 * @throws {ConnectionTestError} If the connection test fails
 * @throws {ConfigError} If the request fails
 */
export async function testConnection(
  connectionConfig: ConnectionConfig
): Promise<ConnectionTestResponse> {
  try {
    const url = `${API_URL}/api/config/test-connection`
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ connection: connectionConfig }),
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      
      // Try to extract connection error details
      try {
        const errorData = await response.json()
        const connectionError = errorData.error || errorData.connection_error || errorMessage
        throw new ConnectionTestError(errorMessage, connectionError)
      } catch {
        // If parsing fails, just throw ConnectionTestError with message
        throw new ConnectionTestError(errorMessage)
      }
    }

    const result = await response.json()
    
    // If the response indicates failure, throw ConnectionTestError
    if (!result.success) {
      throw new ConnectionTestError(
        result.message || 'Connection test failed',
        result.error
      )
    }

    return result
  } catch (error) {
    if (error instanceof ConnectionTestError || error instanceof ConfigError) {
      throw error
    }
    throw new ConnectionTestError(
      `Failed to test connection: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Get configuration version history
 * 
 * @returns List of configuration versions
 * @throws {ConfigError} If the request fails
 */
export async function getConfigHistory(): Promise<ConfigHistoryResponse> {
  try {
    const url = `${API_URL}/api/config/history`
    const response = await fetch(url)

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new ConfigError(
        `Failed to fetch configuration history: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof ConfigError) {
      throw error
    }
    throw new ConfigError(
      `Failed to fetch configuration history: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Load specific configuration version
 * 
 * @param versionId - Version ID to load
 * @returns Configuration version data
 * @throws {ConfigError} If the request fails or version not found
 */
export async function loadConfigVersion(versionId: string): Promise<ConfigVersionResponse> {
  try {
    const url = `${API_URL}/api/config/history/${encodeURIComponent(versionId)}`
    const response = await fetch(url)

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      
      if (response.status === 404) {
        throw new ConfigError(
          `Configuration version not found: ${versionId}`,
          404
        )
      }
      
      throw new ConfigError(
        `Failed to load configuration version: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof ConfigError) {
      throw error
    }
    throw new ConfigError(
      `Failed to load configuration version: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Get storage connection and table status
 * 
 * @returns Storage status information
 * @throws {ConfigError} If the request fails
 */
export async function getStorageStatus(): Promise<StorageStatusResponse> {
  try {
    const url = `${API_URL}/api/config/storage/status`
    const response = await fetch(url)

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new ConfigError(
        `Failed to get storage status: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof ConfigError) {
      throw error
    }
    throw new ConfigError(
      `Failed to get storage status: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Parse YAML string to configuration object
 * 
 * @param yaml - YAML string to parse
 * @returns Parsed configuration with errors if any
 * @throws {ConfigError} If the request fails
 */
export async function parseYAML(yaml: string): Promise<{ config: BaselinrConfig; errors: string[] }> {
  try {
    const url = `${API_URL}/api/config/parse-yaml`
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ yaml }),
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new ConfigError(
        `Failed to parse YAML: ${errorMessage}`,
        response.status
      )
    }

    const result = await response.json()
    return {
      config: result.config,
      errors: result.errors || [],
    }
  } catch (error) {
    if (error instanceof ConfigError) {
      throw error
    }
    throw new ConfigError(
      `Failed to parse YAML: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Convert configuration object to YAML string
 * 
 * @param config - Configuration object to convert
 * @returns YAML string representation
 * @throws {ConfigError} If the request fails
 */
export async function configToYAML(config: BaselinrConfig): Promise<string> {
  try {
    const url = `${API_URL}/api/config/to-yaml`
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ config }),
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new ConfigError(
        `Failed to convert config to YAML: ${errorMessage}`,
        response.status
      )
    }

    const result = await response.json()
    return result.yaml
  } catch (error) {
    if (error instanceof ConfigError) {
      throw error
    }
    throw new ConfigError(
      `Failed to convert config to YAML: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

