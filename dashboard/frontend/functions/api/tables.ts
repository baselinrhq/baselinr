/**
 * Cloudflare Pages Function for /api/tables endpoint
 * Handles GET /api/tables - List profiled tables with filters, sorting, and pagination
 */

import { getDemoDataService } from '../lib/demo-data-service';
import { getDemoDataBaseUrl, parseQueryParams, jsonResponse, errorResponse, parseIntSafe, parseBooleanSafe } from '../lib/utils';
import { getRequest } from '../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    if (!request?.url) {
      return errorResponse('Request URL is missing', 500);
    }
    const url = new URL(request.url);
    const params = parseQueryParams(url);

    // Parse filters
    const filters = {
      warehouse: params.warehouse,
      schema: params.schema,
      search: params.search,
      hasDrift: parseBooleanSafe(params.has_drift),
      hasFailedValidations: parseBooleanSafe(params.has_failed_validations),
      sortBy: params.sort_by || 'table_name',
      sortOrder: params.sort_order || 'asc',
      page: parseIntSafe(params.page, 1),
      pageSize: parseIntSafe(params.page_size, 50),
    };

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const result = await service.getTables(filters);

    // Convert to response format matching FastAPI TableListResponse
    const response = {
      tables: result.tables.map(t => ({
        table_name: t.table_name,
        schema_name: t.schema_name,
        warehouse_type: t.warehouse_type,
        last_profiled: t.last_profiled,
        row_count: t.row_count,
        column_count: t.column_count,
        total_runs: t.total_runs || 0,
        drift_count: t.drift_count || 0,
        validation_pass_rate: t.validation_pass_rate,
        has_recent_drift: t.has_recent_drift || false,
        has_failed_validations: t.has_failed_validations || false,
      })),
      total: result.total,
      page: result.page,
      page_size: result.pageSize,
    };

    return jsonResponse(response);
  } catch (error) {
    console.error('Error in /api/tables:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
