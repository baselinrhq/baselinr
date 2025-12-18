/**
 * Cloudflare Pages Function for /api/warehouses endpoint
 * Handles GET /api/warehouses - List available warehouses
 */

import { getDemoDataService } from '../lib/demo-data-service';
import { getDemoDataBaseUrl, jsonResponse, errorResponse } from '../lib/utils';

export async function onRequestGet(request: Request): Promise<Response> {

  try {
    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const warehouses = await service.getWarehouses();

    return jsonResponse({ warehouses });
  } catch (error) {
    console.error('Error in /api/warehouses:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
