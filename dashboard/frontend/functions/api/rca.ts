/**
 * Cloudflare Pages Function for /api/rca endpoint
 * Handles GET /api/rca - List RCA results
 */

import { getDemoDataService } from '../lib/demo-data-service';
import { getDemoDataBaseUrl, parseQueryParams, jsonResponse, errorResponse, parseIntSafe } from '../lib/utils';
import { getRequest } from '../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    const url = new URL(request.url);
    const params = parseQueryParams(url);
    const limit = parseIntSafe(params.limit, 100);

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const filters: any = {};
    if (params.status) filters.status = params.status;
    if (params.table) filters.table = params.table;
    if (params.schema) filters.schema = params.schema;
    filters.limit = limit;

    const rcaResults = service.getRCAListItems(filters).slice(0, limit);

    return jsonResponse(rcaResults);
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error('[ERROR] /api/rca:', errorMsg);
    return errorResponse(`Failed to fetch RCA results: ${errorMsg}`, 500);
  }
}
