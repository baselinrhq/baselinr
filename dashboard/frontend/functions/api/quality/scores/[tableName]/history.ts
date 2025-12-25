/**
 * Cloudflare Pages Function for /api/quality/scores/[tableName]/history endpoint
 * Handles GET /api/quality/scores/{table_name}/history - Get quality score history
 */

import { getDemoDataService } from '../../../../lib/demo-data-service';
import { getDemoDataBaseUrl, parseQueryParams, jsonResponse, errorResponse, parseIntSafe } from '../../../../lib/utils';
import { getRequest } from '../../../../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    if (!request?.url) {
      return errorResponse('Request URL is missing', 500);
    }
    const url = new URL(request.url);
    const params = parseQueryParams(url);

    // Extract table name from URL path: /api/quality/scores/{tableName}/history
    const pathParts = url.pathname.split('/').filter(p => p);
    const scoresIndex = pathParts.indexOf('scores');
    const tableName = scoresIndex >= 0 && scoresIndex < pathParts.length - 1 ? pathParts[scoresIndex + 1] : null;

    if (!tableName) {
      return errorResponse('table_name is required', 400);
    }

    const schema = params.schema;
    const days = parseIntSafe(params.days);

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const scores = service.getTableQualityScoreHistory(tableName, schema, days);

    return jsonResponse({
      scores,
      total: scores.length,
    });
  } catch (error) {
    console.error('Error in /api/quality/scores/[tableName]/history:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
