'use client'

import { forwardRef } from 'react'
import { cn } from '@/lib/utils'

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'destructive' | 'outline' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  icon?: React.ReactNode
  iconPosition?: 'left' | 'right'
  fullWidth?: boolean
}

const variantStyles = {
  primary:
    'bg-accent-600 text-white hover:bg-accent-500 focus-visible:ring-accent-500 shadow-sm shadow-accent-500/25',
  secondary:
    'bg-surface-700 text-slate-200 hover:bg-surface-600 focus-visible:ring-surface-500',
  destructive:
    'bg-danger-600 text-white hover:bg-danger-500 focus-visible:ring-danger-500 shadow-sm',
  outline:
    'border border-surface-600 bg-transparent text-slate-300 hover:bg-surface-800 hover:border-surface-500 focus-visible:ring-accent-500',
  ghost:
    'text-slate-400 hover:bg-surface-800 hover:text-slate-200 focus-visible:ring-surface-500',
}

const sizeStyles = {
  sm: 'px-3 py-1.5 text-sm gap-1.5',
  md: 'px-4 py-2 text-sm gap-2',
  lg: 'px-6 py-3 text-base gap-2.5',
}

const iconSizeStyles = {
  sm: 'w-4 h-4',
  md: 'w-4 h-4',
  lg: 'w-5 h-5',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      icon,
      iconPosition = 'left',
      fullWidth = false,
      disabled,
      className,
      children,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading

    // Loading spinner
    const loadingSpinner = (
      <svg
        className={cn('animate-spin', iconSizeStyles[size])}
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

    // Icon element with proper sizing
    const iconElement = icon && (
      <span className={cn('flex-shrink-0', iconSizeStyles[size])}>
        {icon}
      </span>
    )

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={cn(
          'inline-flex items-center justify-center font-medium rounded-lg',
          'transition-all duration-150',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-900',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          variantStyles[variant],
          sizeStyles[size],
          fullWidth && 'w-full',
          className
        )}
        {...props}
      >
        {loading ? (
          <>
            {loadingSpinner}
            <span>{children}</span>
          </>
        ) : (
          <>
            {iconPosition === 'left' && iconElement}
            {children && <span>{children}</span>}
            {iconPosition === 'right' && iconElement}
          </>
        )}
      </button>
    )
  }
)

Button.displayName = 'Button'

export default Button
