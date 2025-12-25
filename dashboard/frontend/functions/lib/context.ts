/**
 * Helper functions for Cloudflare Pages Functions context handling
 */

/**
 * Extract Request object from context parameter
 * Handles both direct Request and context.request patterns
 */
export function getRequest(context: any): Request {
  return context?.request || context;
}
