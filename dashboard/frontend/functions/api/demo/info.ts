/**
 * Cloudflare Pages Function for /api/demo/info endpoint
 * Handles GET /api/demo/info - Get demo mode information and metadata
 */

import { getDemoDataService } from '../../lib/demo-data-service';
import { getDemoDataBaseUrl, jsonResponse, errorResponse } from '../../lib/utils';
import { getRequest } from '../../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const response = {
      demo_mode: true,
      metadata: service.metadataData,
      statistics: {
        total_runs: service.runs.length,
        total_metrics: service.metrics.length,
        total_drift_events: service.driftEvents.length,
        total_tables: service.tables.length,
        total_validation_results: service.validationResults.length,
      },
      features: {
        read_only: true,
        real_time_updates: false,
        data_source: 'pre-generated_json',
      },
    };

    return jsonResponse(response);
  } catch (error) {
    console.error('Error in /api/demo/info:', error);
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error('Full error:', error);
    return errorResponse(`Failed to load demo data: ${errorMessage}`, 500);
  }
}
