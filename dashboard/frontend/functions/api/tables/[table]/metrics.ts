/**
 * Cloudflare Pages Function for /api/tables/[table]/metrics endpoint
 * Handles GET /api/tables/{table_name}/metrics - Get detailed metrics for a specific table
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

    // Extract table name from URL path: /api/tables/{table}/metrics
    const pathParts = url.pathname.split('/').filter(p => p);
    const tableIndex = pathParts.indexOf('tables');
    const tableName = tableIndex >= 0 && tableIndex < pathParts.length - 1 ? pathParts[tableIndex + 1] : null;

    if (!tableName) {
      return errorResponse('table_name is required', 400);
    }

    const schema = params.schema;
    const warehouse = params.warehouse;

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const metrics = await service.getTableMetrics(tableName, schema, warehouse);

    if (!metrics) {
      return errorResponse(`Table ${tableName} not found`, 404);
    }

    return jsonResponse(metrics);
  } catch (error) {
    console.error('Error in /api/tables/[table]/metrics:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
