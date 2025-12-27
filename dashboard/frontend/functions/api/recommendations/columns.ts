/**
 * Cloudflare Pages Function for /api/recommendations/columns endpoint
 * Handles GET /api/recommendations/columns - Fetch column recommendations for a table
 */

import { getDemoDataService } from '../../lib/demo-data-service';
import { getDemoDataBaseUrl, parseQueryParams, jsonResponse, errorResponse } from '../../lib/utils';
import { getRequest } from '../../lib/context';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    const url = new URL(request.url);
    const params = parseQueryParams(url);

    // Validate required parameters
    if (!params.connection_id) {
      return errorResponse('connection_id parameter is required', 400);
    }
    if (!params.table) {
      return errorResponse('table parameter is required', 400);
    }

    const service = getDemoDataService();
    const baseUrl = getDemoDataBaseUrl(request);
    await service.loadData(baseUrl);

    const tableName = params.table;
    const schema = params.schema || 'public';

    // Find the table
    const table = service.tables.find((t: any) => 
      t.table_name === tableName && (t.schema_name || 'public') === schema
    );

    if (!table) {
      return jsonResponse([]);
    }

    // Generate column recommendations
    const columnRecommendations: any[] = [];
    if (table.columns && Array.isArray(table.columns)) {
      table.columns.forEach((col: any, colIndex: number) => {
        const colName = col.column_name || col.name || `column_${colIndex}`;
        const colType = col.data_type || col.type || 'unknown';
        
        // Generate suggested checks based on column type and name
        const suggestedChecks: any[] = [];
        const signals: string[] = [];
        
        // ID columns
        if (colName.toLowerCase().endsWith('_id') || colName.toLowerCase() === 'id') {
          signals.push('Column name matches pattern: *_id');
          signals.push('Primary key indicator');
          suggestedChecks.push({
            type: 'uniqueness',
            confidence: 0.98,
            config: { threshold: 1.0 },
          });
          suggestedChecks.push({
            type: 'completeness',
            confidence: 0.95,
            config: { min_completeness: 1.0 },
          });
        }
        
        // Timestamp columns
        if (colType.toLowerCase().includes('timestamp') || 
            colType.toLowerCase().includes('date') ||
            colName.toLowerCase().includes('_at') ||
            colName.toLowerCase().includes('date')) {
          signals.push('Timestamp column, updated continuously');
          signals.push('Required temporal marker');
          suggestedChecks.push({
            type: 'freshness',
            confidence: 0.95,
            config: { max_age_hours: 24 },
          });
          suggestedChecks.push({
            type: 'completeness',
            confidence: 0.95,
            config: { min_completeness: 1.0 },
          });
        }
        
        // Email columns
        if (colName.toLowerCase().includes('email')) {
          signals.push('Email pattern match in column name');
          suggestedChecks.push({
            type: 'format_email',
            confidence: 0.92,
            config: { pattern: 'email' },
          });
        }
        
        // Default completeness check for all columns
        if (suggestedChecks.length === 0) {
          signals.push('Standard column recommendation');
          suggestedChecks.push({
            type: 'completeness',
            confidence: 0.75,
            config: { min_completeness: 0.90 },
          });
        }

        if (suggestedChecks.length > 0) {
          columnRecommendations.push({
            column: colName,
            data_type: colType,
            confidence: Math.min(0.95, 0.7 + Math.random() * 0.25),
            signals,
            suggested_checks: suggestedChecks,
          });
        }
      });
    }

    return jsonResponse(columnRecommendations);
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error('[ERROR] /api/recommendations/columns:', errorMsg);
    return errorResponse(`Failed to fetch column recommendations: ${errorMsg}`, 500);
  }
}
