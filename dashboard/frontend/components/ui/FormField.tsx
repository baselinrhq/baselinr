'use client'

import React from 'react'
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
  
  // Clone children to pass id prop if it's a React element
  const childrenWithId = React.Children.map(children, (child) => {
    if (React.isValidElement(child)) {
      // For Input and other components that accept id, pass it
      // Select component generates its own id, so we don't override it
      const childType = child.type
      if (childType && typeof childType !== 'string') {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const componentName = (childType as { displayName?: string; name?: string }).displayName || 
                             (childType as { displayName?: string; name?: string }).name
        // Only pass id to components that need it (Input, but not Select)
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        if (componentName !== 'Select' && 'id' in (child.props as Record<string, unknown>)) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          return React.cloneElement(child, { id, ...child.props } as Record<string, unknown>)
        }
      }
      // For string elements or components that don't need id, return as-is
      return child
    }
    return child
  })
  
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
      
      {childrenWithId}
      
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
