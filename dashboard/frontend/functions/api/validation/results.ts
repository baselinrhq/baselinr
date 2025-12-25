/**
 * Cloudflare Pages Function for /api/validation/results endpoint
 * Handles GET /api/validation/results - List validation results with filtering and pagination
 */

import { getDemoDataService } from '../../lib/demo-data-service';
import { getDemoDataBaseUrl, parseQueryParams, jsonResponse, errorResponse, parseIntSafe, parseBooleanSafe } from '../../lib/utils';
import { getRequest } from '../../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    if (!request?.url) {
      return errorResponse('Request URL is missing', 500);
    }
    const url = new URL(request.url);
    const params = parseQueryParams(url);

    const filters = {
      table: params.table,
      schema: params.schema,
      ruleType: params.rule_type,
      severity: params.severity,
      passed: parseBooleanSafe(params.passed),
      days: parseIntSafe(params.days, 30),
      page: parseIntSafe(params.page, 1),
      pageSize: parseIntSafe(params.page_size, 50),
    };

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const result = await service.getValidationResultsList(filters);

    return jsonResponse(result);
  } catch (error) {
    console.error('Error in /api/validation/results:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
