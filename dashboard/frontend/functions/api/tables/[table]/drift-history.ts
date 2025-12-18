/**
 * Cloudflare Pages Function for /api/tables/[table]/drift-history endpoint
 * Handles GET /api/tables/{table}/drift-history - Get drift history for a specific table
 */

import { getDemoDataService } from '../../../lib/demo-data-service';
import { getDemoDataBaseUrl, parseQueryParams, jsonResponse, errorResponse, parseIntSafe } from '../../../lib/utils';

export async function onRequestGet(request: Request): Promise<Response> {

  try {
    const url = new URL(request.url);
    const params = parseQueryParams(url);

    // Extract table name from URL path: /api/tables/{table}/drift-history
    const pathParts = url.pathname.split('/').filter(p => p);
    const tableIndex = pathParts.indexOf('tables');
    const tableName = tableIndex >= 0 && tableIndex < pathParts.length - 1 ? pathParts[tableIndex + 1] : null;

    if (!tableName) {
      return errorResponse('table is required', 400);
    }

    const schema = params.schema;
    const warehouse = params.warehouse;
    const limit = parseIntSafe(params.limit, 100);

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const history = await service.getTableDriftHistory(tableName, schema, warehouse, limit);

    return jsonResponse(history);
  } catch (error) {
    console.error('Error in /api/tables/[table]/drift-history:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
