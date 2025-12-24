/**
 * Cloudflare Pages Function for /api/tables/[table]/validation-results endpoint
 * Handles GET /api/tables/{table}/validation-results - Get validation results for a specific table
 */

import { getDemoDataService } from '../../../lib/demo-data-service';
import { getDemoDataBaseUrl, parseQueryParams, jsonResponse, errorResponse, parseIntSafe } from '../../../lib/utils';
import { getRequest } from '../../../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    if (!request?.url) {
      return errorResponse('Request URL is missing', 500);
    }
    const url = new URL(request.url);
    const params = parseQueryParams(url);

    // Extract table name from URL path: /api/tables/{table}/validation-results
    const pathParts = url.pathname.split('/').filter(p => p);
    const tableIndex = pathParts.indexOf('tables');
    const tableName = tableIndex >= 0 && tableIndex < pathParts.length - 1 ? pathParts[tableIndex + 1] : null;

    if (!tableName) {
      return errorResponse('table is required', 400);
    }

    const schema = params.schema;
    const limit = parseIntSafe(params.limit, 100);

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const results = await service.getTableValidationResults(tableName, schema, limit);

    return jsonResponse(results);
  } catch (error) {
    console.error('Error in /api/tables/[table]/validation-results:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
