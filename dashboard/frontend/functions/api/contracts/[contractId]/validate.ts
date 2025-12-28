/**
 * Cloudflare Pages Function for /api/contracts/[contractId]/validate endpoint
 * Handles GET /api/contracts/[contractId]/validate - Validate a specific contract
 */

import { getRequest } from '../../../lib/context';
import { jsonResponse, errorResponse, parseQueryParams } from '../../../lib/utils';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    if (!request?.url) {
      return errorResponse('Request URL is missing', 500);
    }
    const url = new URL(request.url);
    const params = parseQueryParams(url);
    const strict = params.strict === 'true';

    const contractId = context.params?.contractId;
    if (!contractId) {
      return errorResponse('Contract ID is required', 400);
    }

    // In demo mode, return validation result indicating the contract is valid
    // In a real implementation, this would validate the contract from disk
    return jsonResponse({
      valid: true,
      contracts_checked: 1,
      errors: [],
      warnings: [],
    });
  } catch (error) {
    console.error('Error in /api/contracts/[contractId]/validate:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}

