/**
 * Cloudflare Pages Function for /api/tables/[table]/config endpoint
 * Handles GET /api/tables/{table}/config - Get table configuration (placeholder)
 */

import { parseQueryParams, jsonResponse, errorResponse } from '../../../lib/utils';

export async function onRequestGet(request: Request): Promise<Response> {

  try {
    const url = new URL(request.url);
    const params = parseQueryParams(url);

    // Extract table name from URL path: /api/tables/{table}/config
    const pathParts = url.pathname.split('/').filter(p => p);
    const tableIndex = pathParts.indexOf('tables');
    const tableName = tableIndex >= 0 && tableIndex < pathParts.length - 1 ? pathParts[tableIndex + 1] : null;

    if (!tableName) {
      return errorResponse('table is required', 400);
    }

    const schema = params.schema;

    // Placeholder response (matches FastAPI implementation)
    const response = {
      table_name: tableName,
      schema_name: schema,
      config: {},
    };

    return jsonResponse(response);
  } catch (error) {
    console.error('Error in /api/tables/[table]/config:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
