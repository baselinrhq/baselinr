/**
 * Cloudflare Pages Function for /api/runs/[runId] endpoint
 * Handles GET /api/runs/{run_id} - Get detailed profiling result for a specific run
 */

import { getDemoDataService } from '../../lib/demo-data-service';
import { getDemoDataBaseUrl, jsonResponse, errorResponse } from '../../lib/utils';
import { getRequest } from '../../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    if (!request?.url) {
      return errorResponse('Request URL is missing', 500);
    }
    // Extract runId from URL path: /api/runs/{runId}
    const url = new URL(request.url);
    const pathParts = url.pathname.split('/').filter(p => p);
    const runIdIndex = pathParts.indexOf('runs');
    const runId = runIdIndex >= 0 && runIdIndex < pathParts.length - 1 ? pathParts[runIdIndex + 1] : null;

    if (!runId) {
      return errorResponse('run_id is required', 400);
    }

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const run = await service.getRunDetails(runId);
    
    if (!run) {
      return errorResponse(`Run ${runId} not found`, 404);
    }

    // Get metrics for this run
    const metrics = service.getMetricsForRun(runId);

    // Build response matching FastAPI ProfilingResultResponse format
    const response = {
      run_id: run.run_id,
      dataset_name: run.dataset_name,
      schema_name: run.schema_name,
      warehouse_type: run.warehouse_type,
      profiled_at: run.profiled_at,
      environment: 'production', // Default in demo mode
      row_count: run.row_count || 0,
      column_count: run.column_count || 0,
      columns: metrics.map(m => ({
        column_name: m.column_name,
        column_type: m.column_type,
        null_count: m.null_count,
        null_percent: m.null_percent,
        distinct_count: m.distinct_count,
        distinct_percent: m.distinct_percent,
        min_value: m.min_value,
        max_value: m.max_value,
        mean: m.mean,
        stddev: m.stddev,
        histogram: null,
      })),
      metadata: {},
    };

    return jsonResponse(response);
  } catch (error) {
    console.error('Error in /api/runs/[runId]:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
