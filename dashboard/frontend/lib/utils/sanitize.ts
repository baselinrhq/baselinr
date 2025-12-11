/**
 * Utilities for sanitizing sensitive data in configuration displays
 */

/**
 * Mask sensitive values in a configuration object
 * 
 * @param config - Configuration object to sanitize
 * @param showValues - If true, show partial values (first 4 chars), otherwise show placeholder
 * @returns Sanitized configuration with sensitive fields masked
 */
export function maskSensitiveConfig(
  config: unknown,
  showValues: boolean = false
): unknown {
  if (config === null || config === undefined) {
    return config
  }

  if (typeof config === 'string' || typeof config === 'number' || typeof config === 'boolean') {
    return config
  }

  if (Array.isArray(config)) {
    return config.map(item => maskSensitiveConfig(item, showValues))
  }

  if (typeof config === 'object') {
    const sanitized: Record<string, unknown> = {}
    const sensitiveFields = [
      'api_key',
      'apiKey',
      'password',
      'secret',
      'token',
      'access_key',
      'secret_key',
      'private_key',
      'api_secret',
    ]

    for (const [key, value] of Object.entries(config)) {
      const lowerKey = key.toLowerCase()
      const isSensitive = sensitiveFields.some(field => lowerKey.includes(field.toLowerCase()))

      if (isSensitive && typeof value === 'string' && value.length > 0) {
        // Check if it's already an environment variable reference
        if (value.startsWith('${') && value.endsWith('}')) {
          // Keep env var references as-is
          sanitized[key] = value
        } else if (showValues) {
          // Show first 4 characters and mask the rest
          const masked = value.length > 4 
            ? `${value.substring(0, 4)}${'*'.repeat(Math.min(value.length - 4, 20))}`
            : '****'
          sanitized[key] = masked
        } else {
          // Full mask
          sanitized[key] = '****'
        }
      } else {
        // Recursively sanitize nested objects
        sanitized[key] = maskSensitiveConfig(value, showValues)
      }
    }

    return sanitized
  }

  return config
}

/**
 * Check if a field name is considered sensitive
 */
export function isSensitiveField(fieldName: string): boolean {
  const lowerName = fieldName.toLowerCase()
  const sensitiveFields = [
    'api_key',
    'apikey',
    'password',
    'secret',
    'token',
    'access_key',
    'secret_key',
    'private_key',
    'api_secret',
  ]
  return sensitiveFields.some(field => lowerName.includes(field))
}

