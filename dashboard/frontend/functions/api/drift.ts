/**
 * Cloudflare Pages Function for /api/drift endpoint
 * Handles GET /api/drift - List drift alerts with filters
 */

import { getDemoDataService } from '../lib/demo-data-service';
import { getDemoDataBaseUrl, parseQueryParams, jsonResponse, errorResponse, parseDate, parseIntSafe } from '../lib/utils';
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
      severity: params.severity,
      startDate: undefined as Date | undefined,
      endDate: undefined as Date | undefined,
      sortBy: params.sort_by || 'timestamp',
      sortOrder: params.sort_order || 'desc',
      limit: parseIntSafe(params.limit, 100),
      offset: parseIntSafe(params.offset, 0),
    };

    // Handle days parameter (default 30)
    const days = parseIntSafe(params.days, 30);
    if (days) {
      filters.startDate = new Date();
      filters.startDate.setDate(filters.startDate.getDate() - days);
    }

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const alerts = await service.getDriftAlerts(filters);

    return jsonResponse(alerts);
  } catch (error) {
    console.error('Error in /api/drift:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
