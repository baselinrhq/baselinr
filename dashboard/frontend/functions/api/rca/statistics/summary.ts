/**
 * Cloudflare Pages Function for /api/rca/statistics/summary endpoint
 * Handles GET /api/rca/statistics/summary - Get RCA statistics
 */

import { jsonResponse, errorResponse } from '../../../../lib/utils';
import { getRequest } from '../../../../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);

    // For demo mode, return empty statistics since we don't have RCA demo data
    // In a real implementation, this would calculate from the database
    const statistics = {
      total_analyses: 0,
      analyzed: 0,
      dismissed: 0,
      pending: 0,
      avg_causes_per_anomaly: 0,
    };

    return jsonResponse(statistics);
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error('[ERROR] /api/rca/statistics/summary:', errorMsg);
    return errorResponse(`Failed to fetch RCA statistics: ${errorMsg}`, 500);
  }
}
