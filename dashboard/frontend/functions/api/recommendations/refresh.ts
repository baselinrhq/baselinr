/**
 * Cloudflare Pages Function for /api/recommendations/refresh endpoint
 * Handles POST /api/recommendations/refresh - Refresh recommendations
 */

import { getDemoDataService } from '../../lib/demo-data-service';
import { getDemoDataBaseUrl, jsonResponse, errorResponse } from '../../lib/utils';
import { getRequest } from '../../lib/context';

export async function onRequestPost(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    const body = await request.json().catch(() => ({}));

    // In demo mode, refresh is the same as fetching
    // Just reload data and return fresh recommendations
    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const options: any = {};
    if (body.schema) {
      options.schema = body.schema;
    }
    if (body.include_columns === true) {
      options.include_columns = true;
    }

    const recommendations = service.getRecommendations(options);

    return jsonResponse(recommendations);
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error('[ERROR] /api/recommendations/refresh:', errorMsg);
    return errorResponse(`Failed to refresh recommendations: ${errorMsg}`, 500);
  }
}
