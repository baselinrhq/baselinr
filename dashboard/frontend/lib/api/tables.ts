/**
 * API client for table discovery endpoints
 */

import { TablePattern } from '@/types/config'
import { getApiUrl } from '../demo-mode'

const API_URL = getApiUrl()

/**
 * Table information
 */
export interface TableInfo {
  schema: string
  table: string
  table_type?: 'table' | 'view' | 'materialized_view'
  row_count?: number
  last_modified?: string
  database?: string
  tags?: string[]
}

/**
 * Table discovery response
 */
export interface TableDiscoveryResponse {
  tables: TableInfo[]
  total: number
  schemas: string[]
}

/**
 * Table preview response
 */
export interface TablePreviewResponse {
  tables: TableInfo[]
  total: number
  pattern: string
}

/**
 * Table metadata response
 */
export interface TableMetadataResponse {
  schema: string
  table: string
  columns: Array<{
    name: string
    type: string
    nullable: boolean
  }>
  row_count?: number
  table_type?: string
}

/**
 * Discovery filters
 */
export interface DiscoveryFilters {
  database?: string
  schemas?: string[]
  exclude_schemas?: string[]
  table_types?: string[]
  exclude_table_types?: string[]
  pattern?: string
  pattern_type?: 'wildcard' | 'regex'
  tags?: string[]
  tags_any?: string[]
}

/**
 * Custom error class for table API errors
 */
export class TableError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: unknown
  ) {
    super(message)
    this.name = 'TableError'
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
 * Discover tables with filters
 * 
 * @param filters - Discovery filters
 * @returns List of discovered tables
 * @throws {TableError} If the request fails
 */
export async function discoverTables(
  filters?: DiscoveryFilters,
  connectionId?: string
): Promise<TableDiscoveryResponse> {
  try {
    const url = new URL(`${API_URL}/api/tables/discover`)
    
    if (connectionId) {
      url.searchParams.append('connection_id', connectionId)
    }
    
    if (filters) {
      if (filters.database) {
        url.searchParams.append('database', filters.database)
      }
      if (filters.schemas) {
        filters.schemas.forEach(schema => {
          url.searchParams.append('schemas[]', schema)
        })
      }
      if (filters.exclude_schemas) {
        filters.exclude_schemas.forEach(schema => {
          url.searchParams.append('exclude_schemas[]', schema)
        })
      }
      if (filters.table_types) {
        filters.table_types.forEach(type => {
          url.searchParams.append('table_types[]', type)
        })
      }
      if (filters.exclude_table_types) {
        filters.exclude_table_types.forEach(type => {
          url.searchParams.append('exclude_table_types[]', type)
        })
      }
      if (filters.pattern) {
        url.searchParams.append('pattern', filters.pattern)
      }
      if (filters.pattern_type) {
        url.searchParams.append('pattern_type', filters.pattern_type)
      }
      if (filters.tags) {
        filters.tags.forEach(tag => {
          url.searchParams.append('tags[]', tag)
        })
      }
      if (filters.tags_any) {
        filters.tags_any.forEach(tag => {
          url.searchParams.append('tags_any[]', tag)
        })
      }
    }

    const response = await fetch(url.toString())

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new TableError(
        `Failed to discover tables: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof TableError) {
      throw error
    }
    throw new TableError(
      `Failed to discover tables: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Preview table pattern
 * 
 * @param pattern - Table pattern to preview
 * @returns List of matching tables
 * @throws {TableError} If the request fails
 */
export async function previewTablePattern(pattern: TablePattern): Promise<TablePreviewResponse> {
  try {
    const url = `${API_URL}/api/tables/discover`
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(pattern),
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new TableError(
        `Failed to preview table pattern: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof TableError) {
      throw error
    }
    throw new TableError(
      `Failed to preview table pattern: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Get table metadata preview
 * 
 * @param schema - Schema name
 * @param table - Table name
 * @returns Table metadata
 * @throws {TableError} If the request fails
 */
export async function getTablePreview(
  schema: string,
  table: string,
  connectionId?: string
): Promise<TableMetadataResponse> {
  try {
    const url = new URL(`${API_URL}/api/tables/${encodeURIComponent(schema)}/${encodeURIComponent(table)}/preview`)
    if (connectionId) {
      url.searchParams.append('connection_id', connectionId)
    }
    const response = await fetch(url.toString())

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      
      if (response.status === 404) {
        throw new TableError(
          `Table not found: ${schema}.${table}`,
          404
        )
      }
      
      throw new TableError(
        `Failed to get table preview: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof TableError) {
      throw error
    }
    throw new TableError(
      `Failed to get table preview: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

