/**
 * Cloudflare Pages Function for /api/quality/scores endpoint
 * Handles GET /api/quality/scores - List quality scores
 */

import { getDemoDataService } from '../../lib/demo-data-service';
import { getDemoDataBaseUrl, parseQueryParams, jsonResponse, errorResponse } from '../../lib/utils';
import { getRequest } from '../../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    if (!request?.url) {
      return errorResponse('Request URL is missing', 500);
    }
    const url = new URL(request.url);
    const params = parseQueryParams(url);

    const filters = {
      schema: params.schema,
      status: params.status,
    };

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const scores = service.getQualityScores(filters);

    return jsonResponse({
      scores,
      total: scores.length,
    });
  } catch (error) {
    console.error('Error in /api/quality/scores:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
