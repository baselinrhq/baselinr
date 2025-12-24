/**
 * Cloudflare Pages Function for /api/quality/scores/schema/[schemaName] endpoint
 * Handles GET /api/quality/scores/schema/{schema_name} - Get quality scores for a schema
 */

import { getDemoDataService } from '../../../../lib/demo-data-service';
import { getDemoDataBaseUrl, parseQueryParams, jsonResponse, errorResponse } from '../../../../lib/utils';
import { getRequest } from '../../../../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    if (!request?.url) {
      return errorResponse('Request URL is missing', 500);
    }
    const url = new URL(request.url);
    const params = parseQueryParams(url);

    // Extract schema name from URL path: /api/quality/scores/schema/{schemaName}
    const pathParts = url.pathname.split('/').filter(p => p);
    const schemaIndex = pathParts.indexOf('schema');
    const schemaName = schemaIndex >= 0 && schemaIndex < pathParts.length - 1 ? pathParts[schemaIndex + 1] : null;

    if (!schemaName) {
      return errorResponse('schema_name is required', 400);
    }

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const scores = service.getQualityScores({ schema: schemaName });

    if (scores.length === 0) {
      return errorResponse(`No quality scores found for schema: ${schemaName}`, 404);
    }

    const avgScore = scores.reduce((sum, s) => sum + s.overall_score, 0) / scores.length;
    const healthy = scores.filter(s => s.status === 'healthy').length;
    const warning = scores.filter(s => s.status === 'warning').length;
    const critical = scores.filter(s => s.status === 'critical').length;

    return jsonResponse({
      schema_name: schemaName,
      overall_score: Math.round(avgScore * 100) / 100,
      status: avgScore >= 80 ? 'healthy' : avgScore >= 60 ? 'warning' : 'critical',
      table_count: scores.length,
      healthy_count: healthy,
      warning_count: warning,
      critical_count: critical,
      tables: scores,
    });
  } catch (error) {
    console.error('Error in /api/quality/scores/schema/[schemaName]:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
