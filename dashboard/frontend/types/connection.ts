/**
 * TypeScript type definitions for connection management
 */

import { ConnectionConfig } from './config'

/**
 * Saved connection with metadata
 */
export interface SavedConnection {
  id: string
  name: string
  connection: ConnectionConfig
  created_at: string
  updated_at?: string
  last_tested?: string
  is_active?: boolean
}

/**
 * Response for listing connections
 */
export interface ConnectionsListResponse {
  connections: SavedConnection[]
  total: number
}

/**
 * Request body for saving a connection
 */
export interface SaveConnectionRequest {
  name: string
  connection: ConnectionConfig
}

/**
 * Response for saving a connection
 */
export interface SaveConnectionResponse {
  id: string
  connection: SavedConnection
}

