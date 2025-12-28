/**
 * Cloudflare Pages Function for /api/contracts/[contractId] endpoint
 * Handles GET /api/contracts/[contractId] - Get a specific contract
 * Handles PUT /api/contracts/[contractId] - Update a contract
 * Handles DELETE /api/contracts/[contractId] - Delete a contract
 */

import { getRequest } from '../../lib/context';
import { jsonResponse, errorResponse } from '../../lib/utils';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    if (!request?.url) {
      return errorResponse('Request URL is missing', 500);
    }

    const contractId = context.params?.contractId;
    if (!contractId) {
      return errorResponse('Contract ID is required', 400);
    }

    // In demo mode, return 404 for any contract ID
    // In a real implementation, this would load the contract from disk
    return errorResponse('Contract not found', 404);
  } catch (error) {
    console.error('Error in /api/contracts/[contractId] GET:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}

export async function onRequestPut(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    if (!request) {
      return errorResponse('Request is missing', 500);
    }

    const contractId = context.params?.contractId;
    if (!contractId) {
      return errorResponse('Contract ID is required', 400);
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
    });
  } catch (error) {
    console.error('Error in /api/contracts/[contractId] PUT:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}

export async function onRequestDelete(context: any): Promise<Response> {
  try {
    const contractId = context.params?.contractId;
    if (!contractId) {
      return errorResponse('Contract ID is required', 400);
    }

    // In demo mode, return success (no actual deletion)
    // In a real implementation, this would delete the contract file
    return new Response(null, { status: 204 });
  } catch (error) {
    console.error('Error in /api/contracts/[contractId] DELETE:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}

