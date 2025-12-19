/**
 * Demo mode detection and configuration utilities
 */

/**
 * Check if demo mode is enabled
 */
export function isDemoMode(): boolean {
  return process.env.NEXT_PUBLIC_DEMO_MODE === 'true';
}

/**
 * Get the base API URL
 * In demo mode, returns empty string to use relative paths (Pages Functions)
 * Otherwise, uses NEXT_PUBLIC_API_URL or defaults to localhost:8000
 */
export function getApiUrl(): string {
  if (isDemoMode()) {
    // Use relative paths for Cloudflare Pages Functions
    return '';
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
}
