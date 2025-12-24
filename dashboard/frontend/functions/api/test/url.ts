/**
 * Test endpoint to debug URL construction
 */

import { jsonResponse, errorResponse } from '../../lib/utils';

export async function onRequestGet(request: Request): Promise<Response> {
  try {
    const diagnostics: any = {
      hasRequest: !!request,
      requestType: typeof request,
      requestUrl: request?.url || 'MISSING',
      requestUrlType: typeof request?.url,
    };

    try {
      const url = new URL(request.url);
      diagnostics.urlConstructed = true;
      diagnostics.origin = url.origin;
      diagnostics.host = url.host;
      diagnostics.protocol = url.protocol;
      diagnostics.baseUrl = `${url.origin}/demo_data`;
      
      // Test if baseUrl is valid
      try {
        const testUrl = new URL(diagnostics.baseUrl);
        diagnostics.baseUrlValid = true;
        diagnostics.baseUrlFull = testUrl.toString();
      } catch (baseUrlError) {
        diagnostics.baseUrlValid = false;
        diagnostics.baseUrlError = baseUrlError instanceof Error ? baseUrlError.message : String(baseUrlError);
      }
    } catch (urlError) {
      diagnostics.urlConstructed = false;
      diagnostics.urlError = urlError instanceof Error ? urlError.message : String(urlError);
      diagnostics.urlErrorStack = urlError instanceof Error ? urlError.stack : undefined;
    }

    return jsonResponse(diagnostics);
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    const errorStack = error instanceof Error ? error.stack : undefined;
    return errorResponse(`TEST_ERROR: ${errorMsg}. Stack: ${errorStack}`, 500);
  }
}
