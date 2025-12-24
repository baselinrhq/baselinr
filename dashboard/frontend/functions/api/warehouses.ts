/**
 * Cloudflare Pages Function for /api/warehouses endpoint
 * Handles GET /api/warehouses - List available warehouses
 */

import { getDemoDataService } from '../lib/demo-data-service';
import { getDemoDataBaseUrl, jsonResponse, errorResponse } from '../lib/utils';
import { getRequest } from '../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
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
