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
  primary: 'text-accent-500',
  white: 'text-white',
  gray: 'text-slate-400',
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
    <div
      className={cn(
        'rounded-full border-2 border-current animate-spin',
        sizeStyles[size],
        colorStyles[color]
      )}
      style={{ borderTopColor: 'transparent' }}
      aria-hidden="true"
    />
  )

  // Inline spinner
  if (inline) {
    return (
      <span className={cn('inline-flex items-center gap-2', className)}>
        {spinner}
        {text && (
          <span className={cn('text-slate-400', textSizeStyles[size])}>
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
          'fixed inset-0 z-50 flex flex-col items-center justify-center bg-surface-950/80 backdrop-blur-sm',
          className
        )}
        role="status"
        aria-live="polite"
      >
        {spinner}
        {text && (
          <p className={cn('mt-3 text-slate-400', textSizeStyles[size])}>
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
        <p className={cn('mt-2 text-slate-400', textSizeStyles[size])}>
          {text}
        </p>
      )}
      <span className="sr-only">Loading...</span>
    </div>
  )
}

export default LoadingSpinner
