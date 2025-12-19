/**
 * API client for connection management endpoints
 */

import {
  ConnectionConfig,
} from '@/types/config'
import {
  SavedConnection,
  ConnectionsListResponse,
  SaveConnectionRequest,
  SaveConnectionResponse,
} from '@/types/connection'
import { testConnection } from './config'
import { getApiUrl } from '../demo-mode'

const API_URL = getApiUrl()

/**
 * Custom error class for connection API errors
 */
export class ConnectionError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: unknown
  ) {
    super(message)
    this.name = 'ConnectionError'
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
 * List all saved connections
 * 
 * @returns List of saved connections
 * @throws {ConnectionError} If the request fails
 */
export async function listConnections(): Promise<ConnectionsListResponse> {
  try {
    const url = `${API_URL}/api/config/connections`
    const response = await fetch(url)

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new ConnectionError(
        `Failed to list connections: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof ConnectionError) {
      throw error
    }
    throw new ConnectionError(
      `Failed to list connections: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Get a specific connection by ID
 * 
 * @param id - Connection ID
 * @returns Connection details
 * @throws {ConnectionError} If the request fails or connection not found
 */
export async function getConnection(id: string): Promise<SavedConnection> {
  try {
    const url = `${API_URL}/api/config/connections/${encodeURIComponent(id)}`
    const response = await fetch(url)

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      
      if (response.status === 404) {
        throw new ConnectionError(
          `Connection not found: ${id}`,
          404
        )
      }
      
      throw new ConnectionError(
        `Failed to get connection: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof ConnectionError) {
      throw error
    }
    throw new ConnectionError(
      `Failed to get connection: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Save a new connection
 * 
 * @param name - Connection name
 * @param connection - Connection configuration
 * @returns Saved connection response
 * @throws {ConnectionError} If the request fails
 */
export async function saveConnection(
  name: string,
  connection: ConnectionConfig
): Promise<SaveConnectionResponse> {
  try {
    const url = `${API_URL}/api/config/connections`
    const requestBody: SaveConnectionRequest = {
      name,
      connection,
    }
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new ConnectionError(
        `Failed to save connection: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof ConnectionError) {
      throw error
    }
    throw new ConnectionError(
      `Failed to save connection: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Update an existing connection
 * 
 * @param id - Connection ID
 * @param name - Connection name
 * @param connection - Connection configuration
 * @returns Updated connection response
 * @throws {ConnectionError} If the request fails or connection not found
 */
export async function updateConnection(
  id: string,
  name: string,
  connection: ConnectionConfig
): Promise<SaveConnectionResponse> {
  try {
    const url = `${API_URL}/api/config/connections/${encodeURIComponent(id)}`
    const requestBody: SaveConnectionRequest = {
      name,
      connection,
    }
    
    const response = await fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      
      if (response.status === 404) {
        throw new ConnectionError(
          `Connection not found: ${id}`,
          404
        )
      }
      
      throw new ConnectionError(
        `Failed to update connection: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof ConnectionError) {
      throw error
    }
    throw new ConnectionError(
      `Failed to update connection: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Delete a connection
 * 
 * @param id - Connection ID
 * @throws {ConnectionError} If the request fails or connection not found
 */
export async function deleteConnection(id: string): Promise<void> {
  try {
    const url = `${API_URL}/api/config/connections/${encodeURIComponent(id)}`
    const response = await fetch(url, {
      method: 'DELETE',
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      
      if (response.status === 404) {
        throw new ConnectionError(
          `Connection not found: ${id}`,
          404
        )
      }
      
      throw new ConnectionError(
        `Failed to delete connection: ${errorMessage}`,
        response.status
      )
    }
  } catch (error) {
    if (error instanceof ConnectionError) {
      throw error
    }
    throw new ConnectionError(
      `Failed to delete connection: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Re-export testConnection from config API for convenience
 */
export { testConnection }

