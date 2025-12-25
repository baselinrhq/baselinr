/**
 * Cloudflare Pages Function for /api/lineage/graph endpoint
 * Handles GET /api/lineage/graph - Get lineage graph for a table
 */

import { getDemoDataService } from '../../lib/demo-data-service';
import { getDemoDataBaseUrl, parseQueryParams, jsonResponse, errorResponse, parseIntSafe, parseBooleanSafe } from '../../lib/utils';
import { getRequest } from '../../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    if (!request?.url) {
      return errorResponse('Request URL is missing', 500);
    }
    const url = new URL(request.url);
    const params = parseQueryParams(url);

    const table = params.table;
    if (!table) {
      return errorResponse('table query parameter is required', 400);
    }

    const schema = params.schema;
    const direction = (params.direction || 'both') as 'upstream' | 'downstream' | 'both';
    const depth = parseIntSafe(params.depth, 3);
    const confidenceThreshold = parseFloat(params.confidence_threshold || '0');

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    if (!service.lineage || !service.lineage.nodes || !service.lineage.edges) {
      return jsonResponse({ nodes: [], edges: [] });
    }

    // Find the starting node
    const startNodeId = schema ? `${schema}.${table}` : table;
    const startNode = service.lineage.nodes.find((n: any) => 
      n.id === startNodeId || 
      n.table === table && (!schema || n.schema === schema)
    );

    if (!startNode) {
      return jsonResponse({ nodes: [], edges: [] });
    }

    // Filter nodes and edges based on direction and depth
    const visited = new Set<string>();
    const resultNodes: any[] = [startNode];
    const resultEdges: any[] = [];
    visited.add(startNode.id);

    // Simple BFS to find connected nodes up to depth
    const queue: { nodeId: string; level: number }[] = [{ nodeId: startNode.id, level: 0 }];

    while (queue.length > 0) {
      const { nodeId, level } = queue.shift()!;
      if (level >= depth) continue;

      // Find edges connected to this node
      const connectedEdges = service.lineage.edges.filter((e: any) => {
        if (direction === 'upstream') return e.target === nodeId;
        if (direction === 'downstream') return e.source === nodeId;
        return e.source === nodeId || e.target === nodeId;
      });

      for (const edge of connectedEdges) {
        if (edge.confidence && edge.confidence < confidenceThreshold) continue;

        const otherNodeId = edge.source === nodeId ? edge.target : edge.source;
        if (!visited.has(otherNodeId)) {
          const otherNode = service.lineage.nodes.find((n: any) => n.id === otherNodeId);
          if (otherNode) {
            visited.add(otherNodeId);
            resultNodes.push(otherNode);
            queue.push({ nodeId: otherNodeId, level: level + 1 });
          }
        }

        if (!resultEdges.find(e => e.id === edge.id)) {
          resultEdges.push(edge);
        }
      }
    }

    return jsonResponse({
      nodes: resultNodes,
      edges: resultEdges,
    });
  } catch (error) {
    console.error('Error in /api/lineage/graph:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
