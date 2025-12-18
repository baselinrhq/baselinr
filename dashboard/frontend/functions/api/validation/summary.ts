/**
 * Cloudflare Pages Function for /api/validation/summary endpoint
 * Handles GET /api/validation/summary - Get validation summary statistics
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

    const summary = await service.getValidationSummary(filters);

    return jsonResponse(summary);
  } catch (error) {
    console.error('Error in /api/validation/summary:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
