import { type ClassValue, clsx } from 'clsx'

/**
 * Utility function to merge class names
 * Combines clsx for conditional classes
 */
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

/**
 * Generate a unique ID with optional prefix
 */
let idCounter = 0
export function generateId(prefix: string = 'id'): string {
  idCounter += 1
  return `${prefix}-${idCounter}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

/**
 * Clamp a number between min and max values
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

/**
 * Debounce a function call
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null

  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null
      func(...args)
    }

    if (timeout) {
      clearTimeout(timeout)
    }
    timeout = setTimeout(later, wait)
  }
}

/**
 * Format a date to a readable string
 */
export function formatDate(
  date: Date | string | number,
  options?: Intl.DateTimeFormatOptions
): string {
  const dateObj = typeof date === 'string' || typeof date === 'number' 
    ? new Date(date) 
    : date
  
  if (isNaN(dateObj.getTime())) {
    return 'Invalid Date'
  }

  const defaultOptions: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    ...options,
  }

  return new Intl.DateTimeFormat('en-US', defaultOptions).format(dateObj)
}

/**
 * Format a number with locale-specific formatting
 */
export function formatNumber(
  value: number,
  options?: Intl.NumberFormatOptions
): string {
  const defaultOptions: Intl.NumberFormatOptions = {
    maximumFractionDigits: 2,
    ...options,
  }

  return new Intl.NumberFormat('en-US', defaultOptions).format(value)
}

/**
 * Get initials from a name string
 */
export function getInitials(name: string, maxInitials: number = 2): string {
  if (!name || name.trim().length === 0) {
    return ''
  }

  const parts = name.trim().split(/\s+/)
  if (parts.length === 1) {
    return parts[0].charAt(0).toUpperCase()
  }

  const initials = parts
    .slice(0, maxInitials)
    .map(part => part.charAt(0).toUpperCase())
    .join('')

  return initials
}

