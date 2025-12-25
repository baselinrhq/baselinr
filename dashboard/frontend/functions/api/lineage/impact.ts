/**
 * Cloudflare Pages Function for /api/lineage/impact endpoint
 * Handles GET /api/lineage/impact - Get impact analysis
 */

import { getDemoDataService } from '../../lib/demo-data-service';
import { getDemoDataBaseUrl, parseQueryParams, jsonResponse, errorResponse, parseBooleanSafe } from '../../lib/utils';
import { getRequest } from '../../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    if (!request?.url) {
      return errorResponse('Request URL is missing', 500);
    }
    const url = new URL(request.url);
    const params = parseQueryParams(url);

    const table = params.table;
    if (!table) {
      return errorResponse('table query parameter is required', 400);
    }

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    // For demo mode, return basic impact analysis
    return jsonResponse({
      table,
      schema: params.schema,
      downstream_tables: [],
      upstream_tables: [],
      total_impact_score: 0,
      metrics: {},
    });
  } catch (error) {
    console.error('Error in /api/lineage/impact:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
