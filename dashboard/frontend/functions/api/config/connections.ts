/**
 * Cloudflare Pages Function for /api/config/connections endpoint
 * Handles GET /api/config/connections - List connections (demo mode)
 */

import { jsonResponse, errorResponse } from '../../lib/utils';
import { getRequest } from '../../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);

    // In demo mode, return a demo connection
    const demoConnection = {
      id: 'demo-connection-1',
      name: 'Demo Warehouse',
      connection: {
        type: 'postgres',
        host: 'demo.example.com',
        port: 5432,
        database: 'demo_db',
        username: 'demo_user',
        password: '***',
      },
      created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(), // 30 days ago
      updated_at: new Date().toISOString(),
      last_tested: new Date().toISOString(),
      is_active: true,
    };

    return jsonResponse({
      connections: [demoConnection],
      total: 1,
    });
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error('[ERROR] /api/config/connections:', errorMsg);
    return errorResponse(`Failed to fetch connections: ${errorMsg}`, 500);
  }
}
