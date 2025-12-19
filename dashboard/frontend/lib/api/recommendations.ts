/**
 * API client for Baselinr recommendation endpoints
 */

import type {
  RecommendationReport,
  ColumnCheckRecommendation,
  ApplyRecommendationsRequest,
  ApplyRecommendationsResponse,
} from '@/types/recommendation'
import { getApiUrl } from '../demo-mode'

const API_URL = getApiUrl()

export interface RecommendationOptions {
  connection_id: string
  schema?: string
  include_columns?: boolean
  refresh?: boolean
}

export interface ColumnRecommendationOptions {
  connection_id: string
  table: string
  schema?: string
  use_profiling_data?: boolean
}

/**
 * Fetch smart selection recommendations
 */
export async function fetchRecommendations(
  options: RecommendationOptions
): Promise<RecommendationReport> {
  const params = new URLSearchParams()
  params.append('connection_id', options.connection_id)
  if (options.schema) params.append('schema', options.schema)
  if (options.include_columns) params.append('include_columns', 'true')
  if (options.refresh) params.append('refresh', 'true')

  const url = `${API_URL}/api/recommendations?${params.toString()}`
  const response = await fetch(url)

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`API error: ${response.status} ${response.statusText} - ${errorText}`)
  }

  return response.json()
}

/**
 * Fetch column-level recommendations for a specific table
 */
export async function fetchColumnRecommendations(
  options: ColumnRecommendationOptions
): Promise<ColumnCheckRecommendation[]> {
  const params = new URLSearchParams()
  params.append('connection_id', options.connection_id)
  params.append('table', options.table)
  if (options.schema) params.append('schema', options.schema)
  if (options.use_profiling_data !== undefined) {
    params.append('use_profiling_data', options.use_profiling_data.toString())
  }

  const url = `${API_URL}/api/recommendations/columns?${params.toString()}`
  const response = await fetch(url)

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`API error: ${response.status} ${response.statusText} - ${errorText}`)
  }

  return response.json()
}

/**
 * Apply recommendations to configuration
 */
export async function applyRecommendations(
  request: ApplyRecommendationsRequest
): Promise<ApplyRecommendationsResponse> {
  const url = `${API_URL}/api/recommendations/apply`
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`API error: ${response.status} ${response.statusText} - ${errorText}`)
  }

  return response.json()
}

/**
 * Refresh recommendations
 */
export async function refreshRecommendations(
  options: RecommendationOptions
): Promise<RecommendationReport> {
  const url = `${API_URL}/api/recommendations/refresh`
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      connection_id: options.connection_id,
      schema: options.schema,
      include_columns: options.include_columns,
      refresh: true,
    }),
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`API error: ${response.status} ${response.statusText} - ${errorText}`)
  }

  return response.json()
}


