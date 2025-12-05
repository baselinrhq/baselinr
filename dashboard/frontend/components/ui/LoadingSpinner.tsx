'use client'

import { cn } from '@/lib/utils'

export interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  color?: 'primary' | 'white' | 'gray'
  fullPage?: boolean
  text?: string
  inline?: boolean
  className?: string
}

const sizeStyles = {
  sm: 'w-4 h-4',
  md: 'w-6 h-6',
  lg: 'w-10 h-10',
}

const colorStyles = {
  primary: 'text-primary-600',
  white: 'text-white',
  gray: 'text-gray-400',
}

const textSizeStyles = {
  sm: 'text-xs',
  md: 'text-sm',
  lg: 'text-base',
}

export function LoadingSpinner({
  size = 'md',
  color = 'primary',
  fullPage = false,
  text,
  inline = false,
  className,
}: LoadingSpinnerProps) {
  const spinner = (
    <svg
      className={cn('animate-spin', sizeStyles[size], colorStyles[color])}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  )

  // Inline spinner
  if (inline) {
    return (
      <span className={cn('inline-flex items-center gap-2', className)}>
        {spinner}
        {text && (
          <span className={cn('text-gray-600', textSizeStyles[size])}>
            {text}
          </span>
        )}
      </span>
    )
  }

  // Full page overlay
  if (fullPage) {
    return (
      <div
        className={cn(
          'fixed inset-0 z-50 flex flex-col items-center justify-center bg-white/80 backdrop-blur-sm',
          className
        )}
        role="status"
        aria-live="polite"
      >
        {spinner}
        {text && (
          <p className={cn('mt-3 text-gray-600', textSizeStyles[size])}>
            {text}
          </p>
        )}
        <span className="sr-only">Loading...</span>
      </div>
    )
  }

  // Default centered spinner
  return (
    <div
      className={cn('flex flex-col items-center justify-center', className)}
      role="status"
      aria-live="polite"
    >
      {spinner}
      {text && (
        <p className={cn('mt-2 text-gray-600', textSizeStyles[size])}>
          {text}
        </p>
      )}
      <span className="sr-only">Loading...</span>
    </div>
  )
}

export default LoadingSpinner
