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
    solid: 'bg-surface-700 text-slate-300',
    outline: 'border-surface-600 text-slate-400',
  },
  success: {
    solid: 'bg-success-500/20 text-success-400',
    outline: 'border-success-500/50 text-success-400',
  },
  warning: {
    solid: 'bg-warning-500/20 text-warning-400',
    outline: 'border-warning-500/50 text-warning-400',
  },
  error: {
    solid: 'bg-danger-500/20 text-danger-400',
    outline: 'border-danger-500/50 text-danger-400',
  },
  info: {
    solid: 'bg-accent-500/20 text-accent-400',
    outline: 'border-accent-500/50 text-accent-400',
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
