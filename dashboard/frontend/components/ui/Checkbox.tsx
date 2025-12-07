'use client'

import { forwardRef } from 'react'
import { cn, generateId } from '@/lib/utils'

export interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  helperText?: string
  error?: string
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ label, helperText, error, className, id: providedId, ...props }, ref) => {
    const id = providedId || generateId('checkbox')

    return (
      <div className={cn('flex items-start gap-2', className)}>
        <input
          ref={ref}
          type="checkbox"
          id={id}
          className={cn(
            'mt-0.5 h-4 w-4 rounded border-gray-300 text-primary-600',
            'focus:ring-primary-500 focus:ring-2 focus:ring-offset-0',
            'disabled:cursor-not-allowed disabled:opacity-50',
            error && 'border-red-500'
          )}
          {...props}
        />
        {(label || helperText || error) && (
          <div className="flex-1">
            {label && (
              <label
                htmlFor={id}
                className={cn(
                  'text-sm font-medium',
                  props.disabled ? 'text-gray-400' : 'text-gray-700',
                  error && 'text-red-600'
                )}
              >
                {label}
              </label>
            )}
            {error && (
              <p className="mt-1 text-sm text-red-600">{error}</p>
            )}
            {helperText && !error && (
              <p className="mt-1 text-sm text-gray-500">{helperText}</p>
            )}
          </div>
        )}
      </div>
    )
  }
)

Checkbox.displayName = 'Checkbox'

export default Checkbox

