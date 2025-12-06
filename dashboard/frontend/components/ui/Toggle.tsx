'use client'

import { useState, useCallback } from 'react'
import { cn, generateId } from '@/lib/utils'

export interface ToggleProps {
  checked?: boolean
  defaultChecked?: boolean
  onChange?: (checked: boolean) => void
  label?: string
  labelPosition?: 'left' | 'right'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  className?: string
  id?: string
  'aria-label'?: string
  'aria-describedby'?: string
}

const trackSizes = {
  sm: 'w-8 h-5',
  md: 'w-11 h-6',
  lg: 'w-14 h-8',
}

const thumbSizes = {
  sm: 'w-3.5 h-3.5',
  md: 'w-4.5 h-4.5',
  lg: 'w-6 h-6',
}

const thumbTranslate = {
  sm: { off: 'translate-x-0.5', on: 'translate-x-4' },
  md: { off: 'translate-x-0.5', on: 'translate-x-5.5' },
  lg: { off: 'translate-x-1', on: 'translate-x-7' },
}

export function Toggle({
  checked: controlledChecked,
  defaultChecked = false,
  onChange,
  label,
  labelPosition = 'right',
  size = 'md',
  disabled = false,
  className,
  id: providedId,
  'aria-label': ariaLabel,
  'aria-describedby': ariaDescribedBy,
}: ToggleProps) {
  const id = providedId || generateId('toggle')
  
  // Support both controlled and uncontrolled modes
  const isControlled = controlledChecked !== undefined
  const [internalChecked, setInternalChecked] = useState(defaultChecked)
  const checked = isControlled ? controlledChecked : internalChecked

  const handleToggle = useCallback(() => {
    if (disabled) return
    
    const newValue = !checked
    
    if (!isControlled) {
      setInternalChecked(newValue)
    }
    
    onChange?.(newValue)
  }, [checked, disabled, isControlled, onChange])

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === ' ' || event.key === 'Enter') {
      event.preventDefault()
      handleToggle()
    }
  }

  const labelElement = label && (
    <span
      className={cn(
        'text-sm font-medium',
        disabled ? 'text-gray-400' : 'text-gray-700'
      )}
    >
      {label}
    </span>
  )

  return (
    <label
      className={cn(
        'inline-flex items-center gap-3',
        disabled ? 'cursor-not-allowed' : 'cursor-pointer',
        className
      )}
    >
      {labelPosition === 'left' && labelElement}
      
      <button
        type="button"
        role="switch"
        id={id}
        aria-checked={checked}
        aria-label={ariaLabel || label}
        aria-describedby={ariaDescribedBy}
        disabled={disabled}
        onClick={handleToggle}
        onKeyDown={handleKeyDown}
        className={cn(
          'relative inline-flex items-center rounded-full transition-colors duration-200',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2',
          trackSizes[size],
          disabled
            ? 'bg-gray-200 cursor-not-allowed'
            : checked
            ? 'bg-primary-600'
            : 'bg-gray-300'
        )}
      >
        <span
          className={cn(
            'absolute rounded-full bg-white shadow-sm transition-transform duration-200',
            thumbSizes[size],
            checked ? thumbTranslate[size].on : thumbTranslate[size].off
          )}
          style={{
            // Custom sizes that aren't in Tailwind
            width: size === 'md' ? '1.125rem' : undefined,
            height: size === 'md' ? '1.125rem' : undefined,
          }}
        />
      </button>
      
      {labelPosition === 'right' && labelElement}
    </label>
  )
}

export default Toggle
