/**
 * API client for Baselinr RCA endpoints
 */

import type {
  RCAResult,
  RCAListItem,
  RCAStatistics,
  PipelineRun,
  CodeDeployment,
  EventTimelineItem,
  AnalyzeRequest,
  RCAFilters,
} from '@/types/rca'
import { getApiUrl } from '../demo-mode'

const API_URL = getApiUrl()

export class RCAError extends Error {
  constructor(message: string, public statusCode?: number) {
    super(message)
    this.name = 'RCAError'
  }
}

/**
 * List recent RCA results
 */
export async function listRCAResults(
  options: RCAFilters & { limit?: number } = {}
): Promise<RCAListItem[]> {
  const params = new URLSearchParams()
  if (options.limit) params.append('limit', options.limit.toString())
  if (options.status) params.append('status', options.status)

  const url = `${API_URL}/api/rca${params.toString() ? `?${params.toString()}` : ''}`
  const response = await fetch(url)

  if (!response.ok) {
    const errorText = await response.text()
    throw new RCAError(
      `API error: ${response.status} ${response.statusText} - ${errorText}`,
      response.status
    )
  }

  return response.json()
}

/**
 * Get detailed RCA result for an anomaly
 */
export async function getRCAResult(anomalyId: string): Promise<RCAResult> {
  const url = `${API_URL}/api/rca/${anomalyId}`
  const response = await fetch(url)

  if (!response.ok) {
    const errorText = await response.text()
    throw new RCAError(
      `API error: ${response.status} ${response.statusText} - ${errorText}`,
      response.status
    )
  }

  return response.json()
}

/**
 * Trigger RCA analysis for an anomaly
 */
export async function analyzeAnomaly(request: AnalyzeRequest): Promise<RCAResult> {
  const url = `${API_URL}/api/rca/analyze`
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new RCAError(
      `API error: ${response.status} ${response.statusText} - ${errorText}`,
      response.status
    )
  }

  return response.json()
}

/**
 * Re-run RCA analysis for an existing anomaly
 */
export async function reanalyzeAnomaly(anomalyId: string): Promise<RCAResult> {
  const url = `${API_URL}/api/rca/${anomalyId}/reanalyze`
  const response = await fetch(url, {
    method: 'POST',
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new RCAError(
      `API error: ${response.status} ${response.statusText} - ${errorText}`,
      response.status
    )
  }

  return response.json()
}

/**
 * Dismiss an RCA result
 */
export async function dismissRCAResult(
  anomalyId: string,
  reason?: string
): Promise<{ status: string; anomaly_id: string }> {
  const params = new URLSearchParams()
  if (reason) params.append('reason', reason)

  const url = `${API_URL}/api/rca/${anomalyId}${params.toString() ? `?${params.toString()}` : ''}`
  const response = await fetch(url, {
    method: 'DELETE',
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new RCAError(
      `API error: ${response.status} ${response.statusText} - ${errorText}`,
      response.status
    )
  }

  return response.json()
}

/**
 * Get RCA statistics
 */
export async function getRCAStatistics(): Promise<RCAStatistics> {
  const url = `${API_URL}/api/rca/statistics/summary`
  const response = await fetch(url)

  if (!response.ok) {
    const errorText = await response.text()
    throw new RCAError(
      `API error: ${response.status} ${response.statusText} - ${errorText}`,
      response.status
    )
  }

  return response.json()
}

/**
 * Get recent pipeline runs
 */
export async function getRecentPipelineRuns(
  options: {
    limit?: number
    pipeline_name?: string
    status?: string
  } = {}
): Promise<PipelineRun[]> {
  const params = new URLSearchParams()
  if (options.limit) params.append('limit', options.limit.toString())
  if (options.pipeline_name) params.append('pipeline_name', options.pipeline_name)
  if (options.status) params.append('status', options.status)

  const url = `${API_URL}/api/rca/pipeline-runs/recent${params.toString() ? `?${params.toString()}` : ''}`
  const response = await fetch(url)

  if (!response.ok) {
    const errorText = await response.text()
    throw new RCAError(
      `API error: ${response.status} ${response.statusText} - ${errorText}`,
      response.status
    )
  }

  return response.json()
}

/**
 * Get recent code deployments
 */
export async function getRecentDeployments(
  options: {
    limit?: number
    git_commit_sha?: string
  } = {}
): Promise<CodeDeployment[]> {
  const params = new URLSearchParams()
  if (options.limit) params.append('limit', options.limit.toString())
  if (options.git_commit_sha) params.append('git_commit_sha', options.git_commit_sha)

  const url = `${API_URL}/api/rca/deployments/recent${params.toString() ? `?${params.toString()}` : ''}`
  const response = await fetch(url)

  if (!response.ok) {
    const errorText = await response.text()
    throw new RCAError(
      `API error: ${response.status} ${response.statusText} - ${errorText}`,
      response.status
    )
  }

  return response.json()
}

/**
 * Get events timeline
 */
export async function getEventsTimeline(options: {
  start_time: string
  end_time: string
  asset_name?: string
}): Promise<EventTimelineItem[]> {
  const params = new URLSearchParams()
  params.append('start_time', options.start_time)
  params.append('end_time', options.end_time)
  if (options.asset_name) params.append('asset_name', options.asset_name)

  const url = `${API_URL}/api/rca/timeline?${params.toString()}`
  const response = await fetch(url)

  if (!response.ok) {
    const errorText = await response.text()
    throw new RCAError(
      `API error: ${response.status} ${response.statusText} - ${errorText}`,
      response.status
    )
  }

  return response.json()
}

