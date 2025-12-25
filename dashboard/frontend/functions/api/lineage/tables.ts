/**
 * Cloudflare Pages Function for /api/lineage/tables endpoint
 * Handles GET /api/lineage/tables - Get all tables with lineage data
 */

import { getDemoDataService } from '../../lib/demo-data-service';
import { getDemoDataBaseUrl, parseQueryParams, jsonResponse, errorResponse, parseIntSafe } from '../../lib/utils';
import { getRequest } from '../../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    if (!request?.url) {
      return errorResponse('Request URL is missing', 500);
    }
    const url = new URL(request.url);
    const params = parseQueryParams(url);
    const limit = parseIntSafe(params.limit, 100);

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    if (!service.lineage || !service.lineage.nodes) {
      return jsonResponse([]);
    }

    const tables = service.lineage.nodes
      .filter((n: any) => n.type === 'table')
      .slice(0, limit)
      .map((n: any) => ({
        table: n.table || n.label,
        schema: n.schema,
        database: n.database,
      }));

    return jsonResponse(tables);
  } catch (error) {
    console.error('Error in /api/lineage/tables:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
