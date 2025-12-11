/**
 * YAML parsing and formatting utilities
 * 
 * Client-side YAML operations for the config editor
 */

import yaml from 'js-yaml'
import type { BaselinrConfig } from '@/types/config'

/**
 * Parse YAML string to BaselinrConfig object
 * 
 * @param yamlString - YAML string to parse
 * @returns Parsed config object
 * @throws Error if YAML is invalid or cannot be parsed
 */
export function parseYAML(yamlString: string): BaselinrConfig {
  try {
    const parsed = yaml.load(yamlString, {
      schema: yaml.DEFAULT_SAFE_SCHEMA,
      json: false,
    }) as BaselinrConfig
    
    if (!parsed || typeof parsed !== 'object') {
      throw new Error('YAML does not contain a valid configuration object')
    }
    
    return parsed
  } catch (error) {
    if (error instanceof yaml.YAMLException) {
      throw new Error(`YAML parsing error: ${error.message}`)
    }
    throw error
  }
}

/**
 * Convert BaselinrConfig object to YAML string
 * 
 * @param config - Configuration object to convert
 * @returns YAML string representation
 */
export function toYAML(config: BaselinrConfig): string {
  try {
    return yaml.dump(config, {
      indent: 2,
      lineWidth: -1, // No line width limit
      noRefs: true,
      sortKeys: false, // Preserve key order
      quotingType: '"',
      forceQuotes: false,
    })
  } catch (error) {
    throw new Error(`Failed to convert config to YAML: ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}

/**
 * Validate YAML syntax
 * 
 * @param yamlString - YAML string to validate
 * @returns Validation result with error message if invalid
 */
export function validateYAML(yamlString: string): { valid: boolean; error?: string } {
  // Empty string is invalid
  if (!yamlString.trim()) {
    return {
      valid: false,
      error: 'YAML string is empty',
    }
  }

  try {
    const parsed = yaml.load(yamlString, {
      schema: yaml.DEFAULT_SAFE_SCHEMA,
      json: false,
    })
    
    // Also check that it's an object (not just a string or number)
    if (parsed === null || parsed === undefined || typeof parsed !== 'object') {
      return {
        valid: false,
        error: 'YAML does not contain a valid configuration object',
      }
    }
    
    return { valid: true }
  } catch (error) {
    if (error instanceof yaml.YAMLException) {
      return {
        valid: false,
        error: error.message,
      }
    }
    return {
      valid: false,
      error: error instanceof Error ? error.message : 'Unknown YAML error',
    }
  }
}

/**
 * Format/pretty-print YAML string
 * 
 * @param yamlString - YAML string to format
 * @returns Formatted YAML string
 */
export function formatYAML(yamlString: string): string {
  try {
    // Parse and re-dump to format
    const parsed = yaml.load(yamlString, {
      schema: yaml.DEFAULT_SAFE_SCHEMA,
      json: false,
    })
    
    return yaml.dump(parsed, {
      indent: 2,
      lineWidth: -1,
      noRefs: true,
      sortKeys: false,
      quotingType: '"',
      forceQuotes: false,
    })
  } catch {
    // If parsing fails, return original string
    return yamlString
  }
}

