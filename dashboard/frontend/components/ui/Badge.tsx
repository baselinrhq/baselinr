'use client'

import { cn } from '@/lib/utils'

export interface BadgeProps {
  children: React.ReactNode
  variant?: 'success' | 'warning' | 'error' | 'info' | 'default'
  size?: 'sm' | 'md'
  icon?: React.ReactNode
  outline?: boolean
  className?: string
}

const variantStyles = {
  default: {
    solid: 'bg-gray-100 text-gray-800',
    outline: 'border-gray-300 text-gray-700',
  },
  success: {
    solid: 'bg-green-100 text-green-800',
    outline: 'border-green-500 text-green-700',
  },
  warning: {
    solid: 'bg-yellow-100 text-yellow-800',
    outline: 'border-yellow-500 text-yellow-700',
  },
  error: {
    solid: 'bg-red-100 text-red-800',
    outline: 'border-red-500 text-red-700',
  },
  info: {
    solid: 'bg-blue-100 text-blue-800',
    outline: 'border-blue-500 text-blue-700',
  },
}

const sizeStyles = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
}

export function Badge({
  children,
  variant = 'default',
  size = 'md',
  icon,
  outline = false,
  className,
}: BadgeProps) {
  const variantStyle = variantStyles[variant]
  const style = outline ? variantStyle.outline : variantStyle.solid

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 font-medium rounded-full',
        style,
        sizeStyles[size],
        outline && 'border bg-transparent',
        className
      )}
    >
      {icon && <span className="flex-shrink-0">{icon}</span>}
      {children}
    </span>
  )
}

export default Badge
