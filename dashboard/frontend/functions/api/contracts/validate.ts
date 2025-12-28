/**
 * Cloudflare Pages Function for /api/contracts/validate endpoint
 * Handles GET /api/contracts/validate - Validate all contracts
 */

import { getRequest } from '../../lib/context';
import { jsonResponse, errorResponse, parseQueryParams } from '../../lib/utils';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    if (!request?.url) {
      return errorResponse('Request URL is missing', 500);
    }
    const url = new URL(request.url);
    const params = parseQueryParams(url);
    const strict = params.strict === 'true';

    // In demo mode, return validation result indicating all contracts are valid
    // In a real implementation, this would validate contracts from disk
    return jsonResponse({
      valid: true,
      contracts_checked: 0,
      errors: [],
      warnings: [],
    });
  } catch (error) {
    console.error('Error in /api/contracts/validate:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}

