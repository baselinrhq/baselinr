/**
 * Cloudflare Pages Function for /api/runs endpoint
 * Handles GET /api/runs - List profiling runs with filters
 */

import { getDemoDataService } from '../lib/demo-data-service';
import { getDemoDataBaseUrl, parseQueryParams, jsonResponse, errorResponse, parseDate, parseIntSafe, parseFloatSafe } from '../lib/utils';
import { getRequest } from '../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    if (!request?.url) {
      return errorResponse('Request URL is missing', 500);
    }
    const url = new URL(request.url);
    const params = parseQueryParams(url);

    // Parse filters
    const filters = {
      warehouse: params.warehouse,
      schema: params.schema,
      table: params.table,
      status: params.status,
      startDate: parseDate(params.start_date),
      endDate: parseDate(params.end_date),
      minDuration: parseFloatSafe(params.min_duration),
      maxDuration: parseFloatSafe(params.max_duration),
      sortBy: params.sort_by || 'profiled_at',
      sortOrder: params.sort_order || 'desc',
      limit: parseIntSafe(params.limit, 100),
      offset: parseIntSafe(params.offset, 0),
    };

    // Handle 'days' parameter (fallback to start_date if not provided)
    if (params.days && !filters.startDate) {
      const days = parseIntSafe(params.days, 30);
      filters.startDate = new Date();
      filters.startDate.setDate(filters.startDate.getDate() - days);
    }

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const runs = await service.getRuns(filters);

    return jsonResponse(runs);
  } catch (error) {
    console.error('Error in /api/runs:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
