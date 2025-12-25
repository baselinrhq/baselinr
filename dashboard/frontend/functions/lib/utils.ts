/**
 * Utility functions for Cloudflare Pages Functions
 */

/**
 * Get the base URL for demo data files
 */
export function getDemoDataBaseUrl(requestOrContext: Request | any): string {
  try {
    // Handle both direct Request object and context object
    const request = requestOrContext?.request || requestOrContext;
    
    if (!request) {
      throw new Error('Request object is null or undefined');
    }

    let origin: string | undefined;
    
    // Try method 1: Use request.url if it's a valid absolute URL
    let requestUrl: string | undefined = request.url;
    if (requestUrl) {
      try {
        // Only use request.url if it's an absolute URL (starts with http:// or https://)
        if (requestUrl.startsWith('http://') || requestUrl.startsWith('https://')) {
          const url = new URL(requestUrl);
          origin = url.origin;
          console.log('Got origin from request.url:', origin);
        } else {
          // request.url is relative, ignore it and try other methods
          console.log('request.url is relative, ignoring:', requestUrl);
          requestUrl = undefined;
        }
      } catch (urlError) {
        // request.url is invalid, ignore it
        console.log('request.url is invalid, ignoring:', requestUrl, urlError);
        requestUrl = undefined;
      }
    }
    
    // Try method 2: Construct from headers if we don't have an origin yet
    if (!origin && request.headers) {
      try {
        const host = request.headers.get('host');
        const protocol = request.headers.get('x-forwarded-proto') || 
                        request.headers.get('cf-visitor')?.includes('https') ? 'https' : 'https';
        
        if (host) {
          origin = `${protocol}://${host}`;
          console.log('Constructed origin from headers:', origin);
        }
      } catch (headerError) {
        console.error('Error reading headers:', headerError);
      }
    }
    
    // Try method 3: Use Cloudflare environment variable (if available)
    if (!origin && typeof process !== 'undefined' && (process as any).env) {
      const cfPagesUrl = (process as any).env.CF_PAGES_URL;
      if (cfPagesUrl) {
        try {
          const url = new URL(cfPagesUrl);
          origin = url.origin;
          console.log('Got origin from CF_PAGES_URL:', origin);
        } catch (envUrlError) {
          console.error('Error parsing CF_PAGES_URL:', envUrlError);
        }
      }
    }
    
    if (!origin) {
      throw new Error('Cannot determine origin: request.url is invalid/relative, headers unavailable, and CF_PAGES_URL not set');
    }

    // Validate origin
    if (origin === 'null' || origin === 'undefined' || !origin.startsWith('http')) {
      throw new Error(`Invalid origin: "${origin}"`);
    }

    const baseUrl = `${origin}/demo_data`;
    console.log('Constructed baseUrl:', baseUrl);
    return baseUrl;
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error('Error constructing demo data base URL:', {
      error: errorMsg,
      requestUrl: requestOrContext?.url || requestOrContext?.request?.url,
      requestType: typeof requestOrContext,
      hasHeaders: !!requestOrContext?.headers || !!requestOrContext?.request?.headers,
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
