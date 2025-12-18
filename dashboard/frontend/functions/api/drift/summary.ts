/**
 * Cloudflare Pages Function for /api/drift/summary endpoint
 * Handles GET /api/drift/summary - Get drift summary statistics
 */

import { getDemoDataService } from '../../lib/demo-data-service';
import { getDemoDataBaseUrl, parseQueryParams, jsonResponse, errorResponse, parseIntSafe } from '../../lib/utils';

export async function onRequestGet(request: Request): Promise<Response> {

  try {
    const url = new URL(request.url);
    const params = parseQueryParams(url);

    const filters = {
      warehouse: params.warehouse,
      days: parseIntSafe(params.days, 30),
    };

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const summary = await service.getDriftSummary(filters);

    return jsonResponse(summary);
  } catch (error) {
    console.error('Error in /api/drift/summary:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
