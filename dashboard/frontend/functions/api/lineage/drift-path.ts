/**
 * Cloudflare Pages Function for /api/lineage/drift-path endpoint
 * Handles GET /api/lineage/drift-path - Get drift propagation path
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

    const table = params.table;
    if (!table) {
      return errorResponse('table query parameter is required', 400);
    }

    // For demo mode, return empty drift path
    return jsonResponse({
      affected_tables: [],
      propagation_path: [],
    });
  } catch (error) {
    console.error('Error in /api/lineage/drift-path:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
