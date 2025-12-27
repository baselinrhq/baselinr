/**
 * Cloudflare Pages Function for /api/rca/statistics/summary endpoint
 * Handles GET /api/rca/statistics/summary - Get RCA statistics
 */

import { getDemoDataService } from '../../../lib/demo-data-service';
import { getDemoDataBaseUrl, jsonResponse, errorResponse } from '../../../lib/utils';
import { getRequest } from '../../../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const statistics = service.getRCAStatistics();

    return jsonResponse(statistics);
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error('[ERROR] /api/rca/statistics/summary:', errorMsg);
    return errorResponse(`Failed to fetch RCA statistics: ${errorMsg}`, 500);
  }
}
