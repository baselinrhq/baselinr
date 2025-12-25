/**
 * Cloudflare Pages Function for /api/drift/[eventId]/impact endpoint
 * Handles GET /api/drift/{event_id}/impact - Get drift impact analysis
 */

import { getDemoDataService } from '../../../lib/demo-data-service';
import { getDemoDataBaseUrl, jsonResponse, errorResponse } from '../../../lib/utils';
import { getRequest } from '../../../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    if (!request?.url) {
      return errorResponse('Request URL is missing', 500);
    }
    const url = new URL(request.url);

    // Extract eventId from URL path: /api/drift/{eventId}/impact
    const pathParts = url.pathname.split('/').filter(p => p);
    const driftIndex = pathParts.indexOf('drift');
    const eventId = driftIndex >= 0 && driftIndex < pathParts.length - 1 ? pathParts[driftIndex + 1] : null;

    if (!eventId) {
      return errorResponse('event_id is required', 400);
    }

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    // Get drift event details first
    const eventDetails = await service.getDriftDetails(eventId);
    if (!eventDetails) {
      return errorResponse(`Drift event ${eventId} not found`, 404);
    }

    // Build impact analysis based on event and lineage
    const event = eventDetails.event;
    const tableName = event.table_name;

    // Find affected tables from lineage (downstream tables)
    const affectedTables: string[] = [];
    for (const edge of service.lineage.edges) {
      const source = edge.source || '';
      if (tableName && source.includes(tableName)) {
        const target = edge.target || '';
        if (target.includes('.')) {
          const parts = target.split('.');
          if (parts.length >= 2) {
            affectedTables.push(parts[parts.length - 1]);
          }
        }
      }
    }

    // Calculate impact score based on severity
    const severityScores: Record<string, number> = { low: 0.3, medium: 0.6, high: 0.9 };
    const baseScore = severityScores[event.severity] || 0.5;
    const impactScore = Math.min(baseScore + (affectedTables.length * 0.1), 1.0);

    // Generate recommendations
    const recommendations = [
      `Investigate ${event.metric_name} changes in ${tableName}`,
      'Check data quality in upstream sources',
      `Review ${affectedTables.length} downstream tables for cascading issues`,
    ];

    const impact = {
      event_id: eventId,
      affected_tables: affectedTables,
      affected_metrics: 1,
      impact_score: impactScore,
      recommendations,
    };

    return jsonResponse(impact);
  } catch (error) {
    console.error('Error in /api/drift/[eventId]/impact:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
