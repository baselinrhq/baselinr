/**
 * Cloudflare Pages Function for /api/quality/scores/system endpoint
 * Handles GET /api/quality/scores/system - Get system quality score
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

    const systemScore = service.getSystemQualityScore();

    return jsonResponse(systemScore);
  } catch (error) {
    console.error('Error in /api/quality/scores/system:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
