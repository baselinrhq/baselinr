/**
 * Test endpoint to debug URL construction
 */

import { jsonResponse, errorResponse } from '../../lib/utils';

export async function onRequestGet(context: any): Promise<Response> {
  try {
    // Handle both context.request and direct request parameter
    const request = context?.request || context;
    
    const diagnostics: any = {
      hasContext: !!context,
      contextType: typeof context,
      hasRequest: !!request,
      requestType: typeof request,
      requestUrl: request?.url || 'MISSING',
      requestUrlType: typeof request?.url,
      hasHeaders: !!request?.headers,
      headersType: typeof request?.headers,
      contextKeys: context ? Object.keys(context) : [],
    };

    // Safely get headers
    if (request?.headers) {
      try {
        diagnostics.headers = Object.fromEntries(request.headers.entries());
      } catch (headerError) {
        diagnostics.headersError = headerError instanceof Error ? headerError.message : String(headerError);
      }
    } else {
      diagnostics.headers = 'headers not available';
    }

    // Try to get URL from request.url or construct from headers
    let requestUrl: string | undefined = request?.url;
    if (!requestUrl && request?.headers) {
      try {
        const host = request.headers.get('host');
        const protocol = request.headers.get('x-forwarded-proto') || 'https';
        const path = request.headers.get('x-forwarded-uri') || '';
        if (host) {
          requestUrl = `${protocol}://${host}${path}`;
          diagnostics.constructedFromHeaders = true;
          diagnostics.constructedUrl = requestUrl;
        }
      } catch (headerAccessError) {
        diagnostics.headerAccessError = headerAccessError instanceof Error ? headerAccessError.message : String(headerAccessError);
      }
    }

    if (requestUrl) {
      try {
        const url = new URL(requestUrl);
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
    } else {
      diagnostics.urlConstructed = false;
      diagnostics.urlError = 'No URL available from request.url or headers';
    }

    return jsonResponse(diagnostics);
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    const errorStack = error instanceof Error ? error.stack : undefined;
    return errorResponse(`TEST_ERROR: ${errorMsg}. Stack: ${errorStack}`, 500);
  }
}
