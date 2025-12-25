/**
 * Test endpoint to debug data loading
 */

import { jsonResponse, errorResponse } from '../../lib/utils';
import { getRequest } from '../../lib/context';
import { getDemoDataBaseUrl } from '../../lib/utils';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    const request = getRequest(context);
    const baseUrl = getDemoDataBaseUrl(request);
    
    const diagnostics: any = {
      baseUrl,
      testUrls: {},
      results: {},
    };

    // Test fetching each file
    const files = [
      'runs.json', 
      'metrics.json', 
      'tables.json', 
      'drift_events.json', 
      'validation_results.json', 
      'metadata.json',
      'table_quality_scores.json',
      'column_quality_scores.json',
      'lineage.json'
    ];
    
    for (const file of files) {
      const fullUrl = `${baseUrl}/${file}`;
      diagnostics.testUrls[file] = fullUrl;
      
      try {
        const response = await fetch(fullUrl);
        diagnostics.results[file] = {
          status: response.status,
          statusText: response.statusText,
          ok: response.ok,
          contentType: response.headers.get('content-type'),
        };
        
        if (response.ok) {
          const data = await response.json();
          diagnostics.results[file].dataType = Array.isArray(data) ? 'array' : typeof data;
          diagnostics.results[file].length = Array.isArray(data) ? data.length : Object.keys(data).length;
          diagnostics.results[file].sample = Array.isArray(data) && data.length > 0 
            ? data.slice(0, 1)[0] 
            : (typeof data === 'object' && data !== null ? Object.keys(data).slice(0, 5) : data);
        } else {
          const text = await response.text();
          diagnostics.results[file].error = text.substring(0, 200);
        }
      } catch (error) {
        diagnostics.results[file] = {
          error: error instanceof Error ? error.message : String(error),
          stack: error instanceof Error ? error.stack : undefined,
        };
      }
    }

    return jsonResponse(diagnostics);
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    const errorStack = error instanceof Error ? error.stack : undefined;
    return errorResponse(`TEST_DATA_ERROR: ${errorMsg}. Stack: ${errorStack}`, 500);
  }
}
