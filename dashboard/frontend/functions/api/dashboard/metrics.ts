/**
 * Cloudflare Pages Function for /api/dashboard/metrics endpoint
 * Handles GET /api/dashboard/metrics - Get aggregate metrics for dashboard overview
 */

import { getDemoDataService } from '../../lib/demo-data-service';
import { getDemoDataBaseUrl, parseQueryParams, jsonResponse, errorResponse, parseDate, parseIntSafe } from '../../lib/utils';

export async function onRequestGet(context: any): Promise<Response> {
  // Handle both context.request and direct request parameter
  const request = context?.request || context;

  try {
    if (!request || !request.url) {
      return errorResponse('Request URL is missing', 500);
    }
    
    const url = new URL(request.url);
    const params = parseQueryParams(url);

    // Parse filters
    const filters = {
      warehouse: params.warehouse,
      startDate: undefined as Date | undefined,
    };

    // Handle days parameter (default 30)
    const days = parseIntSafe(params.days, 30);
    if (days) {
      filters.startDate = new Date();
      filters.startDate.setDate(filters.startDate.getDate() - days);
    }

    const service = getDemoDataService();
    let baseUrl: string;
    try {
      baseUrl = getDemoDataBaseUrl(request);
      // Log the baseUrl for debugging (remove after fixing)
      console.log('[DEBUG] baseUrl constructed:', baseUrl);
    } catch (baseUrlError) {
      const errorMsg = baseUrlError instanceof Error ? baseUrlError.message : String(baseUrlError);
      return errorResponse(`BASE_URL_ERROR: ${errorMsg}`, 500);
    }
    
    try {
      console.log('[DEBUG] About to call loadData with baseUrl:', baseUrl);
      await service.loadData(baseUrl);
      console.log('[DEBUG] loadData completed successfully');
    } catch (loadError) {
      const errorMsg = loadError instanceof Error ? loadError.message : String(loadError);
      const errorStack = loadError instanceof Error ? loadError.stack : undefined;
      console.error('[ERROR] loadData failed:', { errorMsg, errorStack, baseUrl });
      return errorResponse(`LOAD_DATA_ERROR: ${errorMsg}${errorStack ? '. Stack: ' + errorStack.substring(0, 200) : ''}`, 500);
    }

    const metrics = await service.getDashboardMetrics(filters);

    return jsonResponse(metrics);
  } catch (error) {
    console.error('Error in /api/dashboard/metrics:', error);
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error('Full error details:', {
      message: errorMessage,
      stack: error instanceof Error ? error.stack : undefined,
      requestUrl: request?.url,
    });
    return errorResponse(`Error: ${errorMessage}`, 500);
  }
}
