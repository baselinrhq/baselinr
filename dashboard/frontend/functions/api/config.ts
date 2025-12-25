/**
 * Cloudflare Pages Function for /api/config endpoint
 * Handles GET /api/config - Get configuration (read-only in demo mode)
 */

import { jsonResponse, errorResponse } from '../lib/utils';
import { getRequest } from '../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    // In demo mode, return a basic config structure
    // This is read-only, so we return a sample config
    const demoConfig = {
      version: '1.0',
      demo_mode: true,
      storage: {
        type: 'postgres',
        enabled: true,
      },
      profiling: {
        enabled: true,
        sample_size: 10000,
      },
      validation: {
        enabled: true,
      },
      drift_detection: {
        enabled: true,
      },
      quality_scoring: {
        enabled: true,
        weights: {
          completeness: 25,
          validity: 25,
          consistency: 20,
          freshness: 15,
          uniqueness: 10,
          accuracy: 5,
        },
      },
    };

    return jsonResponse({ config: demoConfig });
  } catch (error) {
    console.error('Error in /api/config:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}
