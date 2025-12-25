/**
 * Cloudflare Pages Function for /api/runs/compare endpoint
 * Handles GET /api/runs/compare - Compare multiple runs side-by-side
 */

import { getDemoDataService } from '../../lib/demo-data-service';
import { getDemoDataBaseUrl, parseQueryParams, jsonResponse, errorResponse } from '../../lib/utils';
import { getRequest } from '../../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    if (!request?.url) {
      return errorResponse('Request URL is missing', 500);
    }
    const url = new URL(request.url);
    const params = parseQueryParams(url);

    const runIdsParam = params.run_ids;
    if (!runIdsParam) {
      return errorResponse('run_ids query parameter is required (comma-separated list)', 400);
    }

    const runIds = runIdsParam.split(',').map(id => id.trim());
    
    if (runIds.length < 2) {
      return errorResponse('At least 2 run IDs required for comparison', 400);
    }
    if (runIds.length > 5) {
      return errorResponse('Maximum 5 runs can be compared at once', 400);
    }

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const comparison = await service.compareRuns(runIds);

    return jsonResponse(comparison);
  } catch (error) {
    console.error('Error in /api/runs/compare:', error);
    if (error instanceof Error && error.message.includes('not found')) {
      return errorResponse(error.message, 400);
    }
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
