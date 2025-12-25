/**
 * Cloudflare Pages Function for /api/lineage/search endpoint
 * Handles GET /api/lineage/search - Search for tables by name
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
    
    const query = params.q || '';
    const limit = parseIntSafe(params.limit, 20);

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    if (!service.lineage || !service.lineage.nodes) {
      return jsonResponse([]);
    }

    const searchLower = query.toLowerCase();
    const tables = service.lineage.nodes
      .filter((n: any) => {
        if (n.type !== 'table') return false;
        const label = (n.label || `${n.schema || ''}.${n.table || ''}`).toLowerCase();
        const table = (n.table || '').toLowerCase();
        return label.includes(searchLower) || table.includes(searchLower);
      })
      .slice(0, limit)
      .map((n: any) => ({
        table: n.table || n.label,
        schema: n.schema,
        database: n.database,
      }));

    return jsonResponse(tables);
  } catch (error) {
    console.error('Error in /api/lineage/search:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
