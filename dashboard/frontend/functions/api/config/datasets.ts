/**
 * Cloudflare Pages Function for /api/config/datasets endpoint
 * Handles GET /api/config/datasets - List all datasets
 */

import { jsonResponse, errorResponse } from '../../lib/utils';
import { getRequest } from '../../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);

    // For demo mode, return empty dataset list since we don't have dataset config demo data
    // In a real implementation, this would fetch from the database
    const datasets = {
      datasets: [] as any[],
      total: 0,
    };

    return jsonResponse(datasets);
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error('[ERROR] /api/config/datasets:', errorMsg);
    return errorResponse(`Failed to fetch datasets: ${errorMsg}`, 500);
  }
}
