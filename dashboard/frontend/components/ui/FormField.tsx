'use client'

import { cn, generateId } from '@/lib/utils'

export interface FormFieldProps {
  label?: string
  required?: boolean
  error?: string
  helperText?: string
  children: React.ReactNode
  htmlFor?: string
  className?: string
}

export function FormField({
  label,
  required = false,
  error,
  helperText,
  children,
  htmlFor,
  className,
}: FormFieldProps) {
  const id = htmlFor || generateId('field')
  
  return (
    <div className={cn('w-full', className)}>
      {label && (
        <label
          htmlFor={id}
          className="block text-sm font-medium text-gray-700 mb-2"
        >
          {label}
          {required && (
            <span className="ml-1 text-red-500" aria-hidden="true">
              *
            </span>
          )}
        </label>
      )}
      
      {children}
      
      {error && (
        <p
          id={`${id}-error`}
          className="mt-1.5 text-sm text-red-600"
          role="alert"
        >
          {error}
        </p>
      )}
      
      {helperText && !error && (
        <p id={`${id}-helper`} className="mt-1.5 text-sm text-gray-500">
          {helperText}
        </p>
      )}
    </div>
  )
}

export default FormField
