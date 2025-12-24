/**
 * Cloudflare Pages Function for /api/quality/scores/[tableName]/trend endpoint
 * Handles GET /api/quality/scores/{table_name}/trend - Get quality score trend analysis
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

    // Extract table name from URL path: /api/quality/scores/{tableName}/trend
    const pathParts = url.pathname.split('/').filter(p => p);
    const scoresIndex = pathParts.indexOf('scores');
    const tableName = scoresIndex >= 0 && scoresIndex < pathParts.length - 1 ? pathParts[scoresIndex + 1] : null;

    if (!tableName) {
      return errorResponse('table_name is required', 400);
    }

    const schema = params.schema;
    const days = parseIntSafe(params.days, 30);

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const history = service.getTableQualityScoreHistory(tableName, schema, days);

    if (history.length < 2) {
      return jsonResponse({
        direction: 'stable',
        rate_of_change: 0,
        confidence: 0,
        periods_analyzed: history.length,
        overall_change: 0,
      });
    }

    // Calculate trend
    const scores = history.map(h => h.overall_score);
    const firstScore = scores[scores.length - 1];
    const lastScore = scores[0];
    const change = lastScore - firstScore;
    const rateOfChange = change / history.length;
    const direction = Math.abs(change) < 0.5 ? 'stable' : change > 0 ? 'improving' : 'degrading';

    return jsonResponse({
      direction,
      rate_of_change: Math.round(rateOfChange * 100) / 100,
      confidence: Math.min(history.length / 10, 1.0), // Confidence based on data points
      periods_analyzed: history.length,
      overall_change: Math.round(change * 100) / 100,
    });
  } catch (error) {
    console.error('Error in /api/quality/scores/[tableName]/trend:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
