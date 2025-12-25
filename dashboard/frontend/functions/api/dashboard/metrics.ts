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
      
      // Verify data was actually loaded
      console.log(`[DEBUG] Data verification: ${service.runs.length} runs, ${service.tables.length} tables, ${service.metrics.length} metrics`);
      if (service.runs.length === 0 && service.tables.length === 0) {
        console.warn('[WARNING] Data arrays are empty after loadData. This may indicate fetch failures.');
        // Don't fail here - let the metrics calculation show zeros, but log the warning
      }
    } catch (loadError) {
      const errorMsg = loadError instanceof Error ? loadError.message : String(loadError);
      const errorStack = loadError instanceof Error ? loadError.stack : undefined;
      console.error('[ERROR] loadData failed:', { errorMsg, errorStack, baseUrl });
      return errorResponse(`LOAD_DATA_ERROR: ${errorMsg}${errorStack ? '. Stack: ' + errorStack.substring(0, 200) : ''}`, 500);
    }

    // Add diagnostic info to response temporarily
    const metrics = await service.getDashboardMetrics(filters);
    const diagnosticInfo = {
      runCount: service.runs.length,
      tableCount: service.tables.length,
      metricsCount: service.metrics.length,
      driftEventsCount: service.driftEvents.length,
    };
    
    // Include diagnostics in response for debugging
    return jsonResponse({
      ...metrics,
      _diagnostics: diagnosticInfo, // Temporary - remove after debugging
    });
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
