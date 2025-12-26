/**
 * Cloudflare Pages Function for /api/rca endpoint
 * Handles GET /api/rca - List RCA results
 */

import { parseQueryParams, jsonResponse, errorResponse, parseIntSafe } from '../../lib/utils';
import { getRequest } from '../../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    const url = new URL(request.url);
    const params = parseQueryParams(url);
    const limit = parseIntSafe(params.limit, 100);

    // For demo mode, return empty array since we don't have RCA demo data
    // In a real implementation, this would fetch from the database
    const rcaResults: any[] = [];

    return jsonResponse(rcaResults);
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error('[ERROR] /api/rca:', errorMsg);
    return errorResponse(`Failed to fetch RCA results: ${errorMsg}`, 500);
  }
}
