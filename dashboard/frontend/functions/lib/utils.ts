/**
 * Utility functions for Cloudflare Pages Functions
 */

/**
 * Get the base URL for demo data files
 */
export function getDemoDataBaseUrl(request: Request): string {
  try {
    if (!request) {
      throw new Error('Request object is null or undefined');
    }

    let requestUrl: string | undefined = request.url;
    
    // Fallback: construct URL from headers if request.url is undefined
    if (!requestUrl) {
      const host = request.headers.get('host');
      const protocol = request.headers.get('x-forwarded-proto') || 'https';
      const path = request.headers.get('x-forwarded-uri') || '';
      
      if (host) {
        requestUrl = `${protocol}://${host}${path}`;
        console.log('Constructed URL from headers:', requestUrl);
      } else {
        throw new Error('Cannot determine URL: request.url is undefined and headers are missing');
      }
    }

    let url: URL;
    try {
      url = new URL(requestUrl);
    } catch (urlError) {
      const urlErrorMsg = urlError instanceof Error ? urlError.message : String(urlError);
      throw new Error(`Invalid request URL: "${requestUrl}". Error: ${urlErrorMsg}`);
    }

    const origin = url.origin;
    if (!origin || origin === 'null' || origin === 'undefined') {
      throw new Error(`Could not determine origin from request URL: ${requestUrl}. Origin: ${origin}`);
    }

    const baseUrl = `${origin}/demo_data`;
    console.log('Constructed baseUrl:', baseUrl);
    return baseUrl;
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error('Error constructing demo data base URL:', {
      error: errorMsg,
      requestUrl: request?.url,
      requestType: typeof request,
      headers: request ? Object.fromEntries(request.headers.entries()) : 'no request',
    });
    throw new Error(`Failed to construct demo data base URL: ${errorMsg}`);
  }
}

/**
 * Create a JSON response
 */
export function jsonResponse(data: unknown, status: number = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}

/**
 * Create an error response
 */
export function errorResponse(message: string, status: number = 500): Response {
  return jsonResponse({ detail: message }, status);
}

/**
 * Parse query parameters from URL
 */
export function parseQueryParams(url: URL): Record<string, string | undefined> {
  const params: Record<string, string | undefined> = {};
  url.searchParams.forEach((value, key) => {
    params[key] = value || undefined;
  });
  return params;
}

/**
 * Parse a date string safely
 */
export function parseDate(dateString: string | undefined): Date | undefined {
  if (!dateString) return undefined;
  const date = new Date(dateString);
  return isNaN(date.getTime()) ? undefined : date;
}

/**
 * Parse an integer safely with default value
 */
export function parseIntSafe(value: string | undefined, defaultValue: number = 0): number {
  if (!value) return defaultValue;
  const parsed = parseInt(value, 10);
  return isNaN(parsed) ? defaultValue : parsed;
}

/**
 * Parse a float safely
 */
export function parseFloatSafe(value: string | undefined): number | undefined {
  if (!value) return undefined;
  const parsed = parseFloat(value);
  return isNaN(parsed) ? undefined : parsed;
}

/**
 * Parse a boolean safely
 */
export function parseBooleanSafe(value: string | undefined): boolean | undefined {
  if (!value) return undefined;
  const lower = value.toLowerCase();
  if (lower === 'true' || lower === '1' || lower === 'yes') return true;
  if (lower === 'false' || lower === '0' || lower === 'no') return false;
  return undefined;
}
