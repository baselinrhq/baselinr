/**
 * Cloudflare Pages Function for /api/export/runs endpoint
 * Handles GET /api/export/runs - Export run history data
 */

import { getDemoDataService } from '../../lib/demo-data-service';
import { getDemoDataBaseUrl, parseQueryParams, errorResponse, parseDate, parseIntSafe } from '../../lib/utils';
import { getRequest } from '../../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    if (!request?.url) {
      return errorResponse('Request URL is missing', 500);
    }
    const url = new URL(request.url);
    const params = parseQueryParams(url);

    const format = params.format || 'json';
    if (format !== 'json' && format !== 'csv') {
      return errorResponse('format must be "json" or "csv"', 400);
    }

    const filters = {
      format,
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
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const data = await service.exportRuns(filters);

    if (format === 'csv') {
      return new Response(data as string, {
        headers: {
          'Content-Type': 'text/csv',
          'Content-Disposition': 'attachment; filename="runs.csv"',
          'Access-Control-Allow-Origin': '*',
        },
      });
    }

    // JSON format
    return new Response(JSON.stringify(data), {
      headers: {
        'Content-Type': 'application/json',
        'Content-Disposition': 'attachment; filename="runs.json"',
        'Access-Control-Allow-Origin': '*',
      },
    });
  } catch (error) {
    console.error('Error in /api/export/runs:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
