'use client'

import { cn } from '@/lib/utils'

export interface CardProps {
  children: React.ReactNode
  header?: React.ReactNode
  footer?: React.ReactNode
  padding?: 'none' | 'sm' | 'md' | 'lg'
  hover?: boolean
  variant?: 'default' | 'glass' | 'outline'
  className?: string
}

const paddingStyles = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
}

const variantStyles = {
  default: 'bg-surface-800/40 border-surface-700/50',
  glass: 'bg-surface-800/40 backdrop-blur-md border-surface-700/30',
  outline: 'bg-transparent border-surface-700',
}

export function Card({
  children,
  header,
  footer,
  padding = 'md',
  hover = false,
  variant = 'default',
  className,
}: CardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border transition-all duration-200',
        variantStyles[variant],
        hover && 'hover:border-surface-600 hover:shadow-lg hover:shadow-black/20 cursor-pointer',
        className
      )}
    >
      {header && (
        <div className="px-6 py-4 border-b border-surface-700/50">
          {typeof header === 'string' ? (
            <h3 className="text-lg font-semibold text-white">{header}</h3>
          ) : (
            header
          )}
        </div>
      )}
      
      <div className={cn(paddingStyles[padding])}>
        {children}
      </div>
      
      {footer && (
        <div className="px-6 py-4 border-t border-surface-700/50 bg-surface-900/30 rounded-b-xl">
          {footer}
        </div>
      )}
    </div>
  )
}

// Card subcomponents for more flexibility
export interface CardHeaderProps {
  children: React.ReactNode
  className?: string
}

export function CardHeader({ children, className }: CardHeaderProps) {
  return (
    <div className={cn('px-6 py-4 border-b border-surface-700/50', className)}>
      {children}
    </div>
  )
}

export interface CardBodyProps {
  children: React.ReactNode
  className?: string
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

const bodyPaddingStyles = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
}

export function CardBody({ children, className, padding = 'md' }: CardBodyProps) {
  return <div className={cn(bodyPaddingStyles[padding], className)}>{children}</div>
}

export interface CardFooterProps {
  children: React.ReactNode
  className?: string
}

export function CardFooter({ children, className }: CardFooterProps) {
  return (
    <div
      className={cn(
        'px-6 py-4 border-t border-surface-700/50 bg-surface-900/30 rounded-b-xl',
        className
      )}
    >
      {children}
    </div>
  )
}

export interface CardTitleProps {
  children: React.ReactNode
  className?: string
}

export function CardTitle({ children, className }: CardTitleProps) {
  return (
    <h3 className={cn('text-lg font-semibold text-white', className)}>
      {children}
    </h3>
  )
}

export interface CardDescriptionProps {
  children: React.ReactNode
  className?: string
}

export function CardDescription({ children, className }: CardDescriptionProps) {
  return <p className={cn('text-sm text-slate-400 mt-1', className)}>{children}</p>
}

export default Card
