/**
 * Cloudflare Pages Function for /api/lineage/node/[nodeId] endpoint
 * Handles GET /api/lineage/node/{node_id} - Get node details
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

    // Extract nodeId from URL path: /api/lineage/node/{nodeId}
    const pathParts = url.pathname.split('/').filter(p => p);
    const nodeIndex = pathParts.indexOf('node');
    const nodeId = nodeIndex >= 0 && nodeIndex < pathParts.length - 1 ? pathParts[nodeIndex + 1] : null;

    if (!nodeId) {
      return errorResponse('node_id is required', 400);
    }

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    if (!service.lineage || !service.lineage.nodes) {
      return errorResponse('Lineage data not available', 404);
    }

    const node = service.lineage.nodes.find((n: any) => n.id === nodeId);
    if (!node) {
      return errorResponse(`Node ${nodeId} not found`, 404);
    }

    // Count upstream and downstream connections
    const upstreamEdges = service.lineage.edges.filter((e: any) => e.target === nodeId);
    const downstreamEdges = service.lineage.edges.filter((e: any) => e.source === nodeId);

    return jsonResponse({
      id: node.id,
      label: node.label,
      type: node.type,
      table: node.table,
      column: node.column,
      schema: node.schema,
      database: node.database,
      upstream_count: upstreamEdges.length,
      downstream_count: downstreamEdges.length,
      providers: node.metadata?.providers || [],
    });
  } catch (error) {
    console.error('Error in /api/lineage/node/[nodeId]:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
