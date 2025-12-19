/**
 * Cloudflare Pages Function for /api/dashboard/metrics endpoint
 * Handles GET /api/dashboard/metrics - Get aggregate metrics for dashboard overview
 */

import { getDemoDataService } from '../../lib/demo-data-service';
import { getDemoDataBaseUrl, parseQueryParams, jsonResponse, errorResponse, parseDate, parseIntSafe } from '../../lib/utils';

export async function onRequestGet(request: Request): Promise<Response> {

  try {
    const url = new URL(request.url);
    const params = parseQueryParams(url);

    // Parse filters
    const filters = {
      warehouse: params.warehouse,
      startDate: undefined as Date | undefined,
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

    const metrics = await service.getDashboardMetrics(filters);

    return jsonResponse(metrics);
  } catch (error) {
    console.error('Error in /api/dashboard/metrics:', error);
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error('Full error details:', {
      message: errorMessage,
      stack: error instanceof Error ? error.stack : undefined,
      requestUrl: request.url,
    });
    return errorResponse(`Error: ${errorMessage}`, 500);
  }
}
