/**
 * Cloudflare Pages Function for /api/config/history endpoint
 * Handles GET /api/config/history - Get configuration version history
 */

import { jsonResponse, errorResponse } from '../../lib/utils';
import { getRequest } from '../../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);

    // For demo mode, return empty history since we don't have config history demo data
    // In a real implementation, this would fetch from the database
    const history = {
      versions: [] as any[],
      total: 0,
    };

    return jsonResponse(history);
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error('[ERROR] /api/config/history:', errorMsg);
    return errorResponse(`Failed to fetch configuration history: ${errorMsg}`, 500);
  }
}
