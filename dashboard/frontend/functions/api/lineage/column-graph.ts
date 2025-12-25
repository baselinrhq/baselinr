/**
 * Cloudflare Pages Function for /api/lineage/column-graph endpoint
 * Handles GET /api/lineage/column-graph - Get column-level lineage graph
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
    const column = params.column;
    if (!table || !column) {
      return errorResponse('table and column query parameters are required', 400);
    }

    // For demo mode, return empty graph for column lineage
    // Column-level lineage would require more detailed data
    return jsonResponse({
      nodes: [],
      edges: [],
    });
  } catch (error) {
    console.error('Error in /api/lineage/column-graph:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
