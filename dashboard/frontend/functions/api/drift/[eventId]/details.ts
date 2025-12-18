/**
 * Cloudflare Pages Function for /api/drift/[eventId]/details endpoint
 * Handles GET /api/drift/{event_id}/details - Get detailed drift information for a specific event
 */

import { getDemoDataService } from '../../../lib/demo-data-service';
import { getDemoDataBaseUrl, jsonResponse, errorResponse } from '../../../lib/utils';

export async function onRequestGet(request: Request): Promise<Response> {

  try {
    const url = new URL(request.url);

    // Extract eventId from URL path: /api/drift/{eventId}/details
    const pathParts = url.pathname.split('/').filter(p => p);
    const driftIndex = pathParts.indexOf('drift');
    const eventId = driftIndex >= 0 && driftIndex < pathParts.length - 1 ? pathParts[driftIndex + 1] : null;

    if (!eventId) {
      return errorResponse('event_id is required', 400);
    }

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const details = await service.getDriftDetails(eventId);

    if (!details) {
      return errorResponse(`Drift event ${eventId} not found`, 404);
    }

    return jsonResponse(details);
  } catch (error) {
    console.error('Error in /api/drift/[eventId]/details:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
