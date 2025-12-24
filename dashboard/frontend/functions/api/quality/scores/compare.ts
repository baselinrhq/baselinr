/**
 * Cloudflare Pages Function for /api/quality/scores/compare endpoint
 * Handles GET /api/quality/scores/compare - Compare quality scores for multiple tables
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

    const tablesParam = params.tables;
    if (!tablesParam) {
      return errorResponse('tables query parameter is required (comma-separated list)', 400);
    }

    const tableNames = tablesParam.split(',').map(t => t.trim());
    const schema = params.schema;

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const scores = tableNames
      .map(tableName => service.getTableQualityScore(tableName, schema))
      .filter(score => score !== null);

    if (scores.length === 0) {
      return errorResponse('No quality scores found for the specified tables', 404);
    }

    const sortedByScore = [...scores].sort((a, b) => b.overall_score - a.overall_score);
    const bestPerformer = sortedByScore[0];
    const worstPerformer = sortedByScore[sortedByScore.length - 1];
    const avgScore = scores.reduce((sum, s) => sum + s.overall_score, 0) / scores.length;
    const minScore = Math.min(...scores.map(s => s.overall_score));
    const maxScore = Math.max(...scores.map(s => s.overall_score));

    return jsonResponse({
      tables: scores,
      comparison_metrics: {
        best_performer: `${bestPerformer.schema_name ? bestPerformer.schema_name + '.' : ''}${bestPerformer.table_name}`,
        worst_performer: `${worstPerformer.schema_name ? worstPerformer.schema_name + '.' : ''}${worstPerformer.table_name}`,
        average_score: Math.round(avgScore * 100) / 100,
        score_range: {
          min: Math.round(minScore * 100) / 100,
          max: Math.round(maxScore * 100) / 100,
        },
      },
    });
  } catch (error) {
    console.error('Error in /api/quality/scores/compare:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
