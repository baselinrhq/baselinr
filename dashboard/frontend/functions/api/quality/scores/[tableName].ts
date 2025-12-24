/**
 * Cloudflare Pages Function for /api/quality/scores/[tableName] endpoint
 * Handles GET /api/quality/scores/{table_name} - Get quality score for a specific table
 */

import { getDemoDataService } from '../../../lib/demo-data-service';
import { getDemoDataBaseUrl, parseQueryParams, jsonResponse, errorResponse } from '../../../lib/utils';
import { getRequest } from '../../../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    if (!request?.url) {
      return errorResponse('Request URL is missing', 500);
    }
    const url = new URL(request.url);
    const params = parseQueryParams(url);

    // Extract table name from URL path: /api/quality/scores/{tableName}
    const pathParts = url.pathname.split('/').filter(p => p);
    const scoresIndex = pathParts.indexOf('scores');
    const tableName = scoresIndex >= 0 && scoresIndex < pathParts.length - 1 ? pathParts[scoresIndex + 1] : null;

    if (!tableName) {
      return errorResponse('table_name is required', 400);
    }

    const schema = params.schema;

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const score = service.getTableQualityScore(tableName, schema);

    if (!score) {
      return errorResponse(`Quality score not found for table: ${tableName}`, 404);
    }

    return jsonResponse(score);
  } catch (error) {
    console.error('Error in /api/quality/scores/[tableName]:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
