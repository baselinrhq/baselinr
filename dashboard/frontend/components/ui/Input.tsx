'use client'

import { forwardRef } from 'react'
import { cn, generateId } from '@/lib/utils'

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helperText?: string
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
  state?: 'default' | 'error' | 'success'
  containerClassName?: string
}

const stateStyles = {
  default: 'border-surface-600 focus:border-accent-500 focus:ring-accent-500',
  error: 'border-danger-500 focus:border-danger-500 focus:ring-danger-500',
  success: 'border-success-500 focus:border-success-500 focus:ring-success-500',
}

const stateIconColors = {
  default: 'text-slate-500',
  error: 'text-danger-400',
  success: 'text-success-400',
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      helperText,
      leftIcon,
      rightIcon,
      state: stateProp,
      className,
      containerClassName,
      disabled,
      id: providedId,
      ...props
    },
    ref
  ) => {
    const id = providedId || generateId('input')
    
    // Determine state from error prop if not explicitly set
    const state = stateProp || (error ? 'error' : 'default')

    return (
      <div className={cn('w-full', containerClassName)}>
        {label && (
          <label
            htmlFor={id}
            className="block text-sm font-medium text-slate-300 mb-2"
          >
            {label}
          </label>
        )}
        
        <div className="relative">
          {leftIcon && (
            <div
              className={cn(
                'absolute left-3 top-1/2 -translate-y-1/2',
                stateIconColors[state]
              )}
            >
              {leftIcon}
            </div>
          )}
          
          <input
            ref={ref}
            id={id}
            disabled={disabled}
            className={cn(
              'w-full px-3 py-2 border rounded-lg bg-surface-800/50',
              'text-slate-200 placeholder:text-slate-500',
              'focus:outline-none focus:ring-2',
              'transition-colors',
              'disabled:bg-surface-900 disabled:text-slate-600 disabled:cursor-not-allowed',
              stateStyles[state],
              leftIcon && 'pl-10',
              rightIcon && 'pr-10',
              className
            )}
            aria-invalid={state === 'error'}
            aria-describedby={
              error ? `${id}-error` : helperText ? `${id}-helper` : undefined
            }
            {...props}
          />
          
          {rightIcon && (
            <div
              className={cn(
                'absolute right-3 top-1/2 -translate-y-1/2',
                stateIconColors[state]
              )}
            >
              {rightIcon}
            </div>
          )}
        </div>
        
        {error && (
          <p id={`${id}-error`} className="mt-1.5 text-sm text-danger-400">
            {error}
          </p>
        )}
        
        {helperText && !error && (
          <p id={`${id}-helper`} className="mt-1.5 text-sm text-slate-500">
            {helperText}
          </p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'

export default Input
