'use client'

import { forwardRef } from 'react'
import { cn, generateId } from '@/lib/utils'

export interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  helperText?: string
  error?: string
  indeterminate?: boolean
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ label, helperText, error, indeterminate, className, id: providedId, ...props }, ref) => {
    const id = providedId || generateId('checkbox')

    return (
      <div className={cn('flex items-start gap-2', className)}>
        <input
          ref={(el) => {
            if (typeof ref === 'function') {
              ref(el)
            } else if (ref) {
              ref.current = el
            }
            if (el) {
              el.indeterminate = indeterminate || false
            }
          }}
          type="checkbox"
          id={id}
          className={cn(
            'mt-0.5 h-4 w-4 rounded border-surface-600 bg-surface-800/50 text-accent-500',
            'focus:ring-accent-500 focus:ring-2 focus:ring-offset-0 focus:ring-offset-surface-900',
            'disabled:cursor-not-allowed disabled:opacity-50',
            'checked:bg-accent-500 checked:border-accent-500',
            error && 'border-danger-500'
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
                  props.disabled ? 'text-slate-600' : 'text-slate-300',
                  error && 'text-danger-400'
                )}
              >
                {label}
              </label>
            )}
            {error && (
              <p className="mt-1 text-sm text-danger-400">{error}</p>
            )}
            {helperText && !error && (
              <p className="mt-1 text-sm text-slate-500">{helperText}</p>
            )}
          </div>
        )}
      </div>
    )
  }
)

Checkbox.displayName = 'Checkbox'

export default Checkbox
