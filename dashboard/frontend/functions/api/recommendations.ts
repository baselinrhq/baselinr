/**
 * Cloudflare Pages Function for /api/recommendations endpoint
 * Handles GET /api/recommendations - Fetch recommendations
 */

import { getDemoDataService } from '../lib/demo-data-service';
import { getDemoDataBaseUrl, parseQueryParams, jsonResponse, errorResponse } from '../lib/utils';
import { getRequest } from '../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    const url = new URL(request.url);
    const params = parseQueryParams(url);

    // Validate required parameters
    if (!params.connection_id) {
      return errorResponse('connection_id parameter is required', 400);
    }

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const options: any = {};
    if (params.schema) {
      options.schema = params.schema;
    }
    if (params.include_columns === 'true') {
      options.include_columns = true;
    }

    const recommendations = service.getRecommendations(options);

    return jsonResponse(recommendations);
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error('[ERROR] /api/recommendations:', errorMsg);
    return errorResponse(`Failed to fetch recommendations: ${errorMsg}`, 500);
  }
}
