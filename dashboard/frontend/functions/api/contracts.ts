/**
 * Cloudflare Pages Function for /api/contracts endpoint
 * Handles GET /api/contracts - List all contracts
 * Handles POST /api/contracts - Create a new contract
 */

import { getRequest } from '../lib/context';
import { jsonResponse, errorResponse, parseQueryParams } from '../lib/utils';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    if (!request?.url) {
      return errorResponse('Request URL is missing', 500);
    }
    const url = new URL(request.url);
    const params = parseQueryParams(url);

    // In demo mode, return empty contracts list
    // In a real implementation, this would load contracts from the file system
    const contracts: any[] = [];
    const total = 0;

    return jsonResponse({
      contracts,
      total,
    });
  } catch (error) {
    console.error('Error in /api/contracts GET:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}

export async function onRequestPost(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    if (!request) {
      return errorResponse('Request is missing', 500);
    }

    const body = await request.json();
    const { contract } = body;

    if (!contract) {
      return errorResponse('Contract data is required', 400);
    }

    // In demo mode, return the contract as-is (no persistence)
    // In a real implementation, this would save the contract to disk
    return jsonResponse({
      contract,
    }, 201);
  } catch (error) {
    console.error('Error in /api/contracts POST:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}

