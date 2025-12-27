/**
 * Cloudflare Pages Function for /api/recommendations/apply endpoint
 * Handles POST /api/recommendations/apply - Apply recommendations (demo mode - no-op)
 */

import { jsonResponse, errorResponse } from '../../lib/utils';
import { getRequest } from '../../lib/context';

export async function onRequestPost(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    const body = await request.json().catch(() => ({}));

    // In demo mode, we don't actually apply recommendations
    // Return a success response indicating the recommendations would be applied
    const selectedTables = body.selected_tables || [];
    
    const appliedTables = selectedTables.map((table: any) => ({
      schema: table.schema || 'public',
      table: table.table,
      database: table.database || null,
      column_checks_applied: Math.floor(Math.random() * 5) + 1, // Mock number
    }));

    return jsonResponse({
      success: true,
      applied_tables: appliedTables,
      total_tables_applied: appliedTables.length,
      total_column_checks_applied: appliedTables.reduce((sum: number, t: any) => 
        sum + t.column_checks_applied, 0
      ),
      message: 'Recommendations would be applied in production mode. This is a demo.',
    });
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error('[ERROR] /api/recommendations/apply:', errorMsg);
    return errorResponse(`Failed to apply recommendations: ${errorMsg}`, 500);
  }
}
