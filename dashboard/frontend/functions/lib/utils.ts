/**
 * Utility functions for Cloudflare Pages Functions
 */

/**
 * Get the base URL for demo data files
 */
export function getDemoDataBaseUrl(request: Request): string {
  const url = new URL(request.url);
  const origin = url.origin;
  return `${origin}/demo_data`;
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
