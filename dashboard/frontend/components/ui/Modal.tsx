'use client'

import { useEffect, useCallback, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import { cn, generateId } from '@/lib/utils'

export interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
  footer?: React.ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full'
  closeOnBackdropClick?: boolean
  closeOnEsc?: boolean
  showCloseButton?: boolean
  className?: string
}

const sizeClasses = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
  full: 'max-w-[90vw]',
}

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  footer,
  size = 'md',
  closeOnBackdropClick = true,
  closeOnEsc = true,
  showCloseButton = true,
  className,
}: ModalProps) {
  const id = useRef(generateId('modal')).current
  const modalRef = useRef<HTMLDivElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)
  const isMountedRef = useRef(true)
  const [isExiting, setIsExiting] = useState(false)
  const [mounted, setMounted] = useState(false)

  // Handle mounting for portal
  useEffect(() => {
    setMounted(true)
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  // Cleanup timeout on unmount only
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
      isMountedRef.current = false
    }
  }, [])

  // Handle close with exit animation
  const handleClose = useCallback(() => {
    // Clear any existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
    
    setIsExiting(true)
    timeoutRef.current = setTimeout(() => {
      timeoutRef.current = null
      // Only update state if component is still mounted
      if (isMountedRef.current) {
      setIsExiting(false)
      onClose()
      }
    }, 150)
  }, [onClose])

  // Handle Escape key
  useEffect(() => {
    if (!isOpen || !closeOnEsc) return

    const handleEsc = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        handleClose()
      }
    }

    document.addEventListener('keydown', handleEsc)
    return () => document.removeEventListener('keydown', handleEsc)
  }, [isOpen, closeOnEsc, handleClose])

  // Focus management
  useEffect(() => {
    if (isOpen) {
      previousFocusRef.current = document.activeElement as HTMLElement
      const focusTimeout = setTimeout(() => {
        modalRef.current?.focus()
      }, 0)
      return () => clearTimeout(focusTimeout)
    } else {
      previousFocusRef.current?.focus()
    }
  }, [isOpen])

  // Lock body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      const originalOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      return () => {
        document.body.style.overflow = originalOverflow
      }
    }
  }, [isOpen])

  // Focus trap
  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if (event.key !== 'Tab') return

    const modal = modalRef.current
    if (!modal) return

    const focusableElements = modal.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )
    const firstElement = focusableElements[0]
    const lastElement = focusableElements[focusableElements.length - 1]

    if (event.shiftKey) {
      if (document.activeElement === firstElement) {
        event.preventDefault()
        lastElement?.focus()
      }
    } else {
      if (document.activeElement === lastElement) {
        event.preventDefault()
        firstElement?.focus()
      }
    }
  }, [])

  // Handle backdrop click
  const handleBackdropClick = (event: React.MouseEvent) => {
    if (closeOnBackdropClick && event.target === event.currentTarget) {
      handleClose()
    }
  }

  if (!mounted || (!isOpen && !isExiting)) return null

  const modalContent = (
    <>
      {/* Backdrop */}
      <div
        className={cn(
          'fixed inset-0 z-50 bg-black/60 backdrop-blur-sm transition-opacity duration-150',
          isExiting ? 'opacity-0' : 'opacity-100'
        )}
        aria-hidden="true"
      />

      {/* Modal container */}
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        onClick={handleBackdropClick}
        role="presentation"
      >
        {/* Modal content */}
        <div
          ref={modalRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby={title ? `${id}-title` : undefined}
          tabIndex={-1}
          onKeyDown={handleKeyDown}
          className={cn(
            'w-full bg-surface-800 border border-surface-700 rounded-xl shadow-2xl shadow-black/40',
            'transition-all duration-150',
            isExiting ? 'opacity-0 scale-95' : 'opacity-100 scale-100',
            sizeClasses[size],
            className
          )}
        >
          {/* Header */}
          {(title || showCloseButton) && (
            <div className="flex items-center justify-between px-6 py-4 border-b border-surface-700">
              {title && (
                <h2
                  id={`${id}-title`}
                  className="text-lg font-semibold text-white"
                >
                  {title}
                </h2>
              )}
              
              {showCloseButton && (
                <button
                  type="button"
                  onClick={handleClose}
                  className={cn(
                    'p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-surface-700',
                    'transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500',
                    !title && 'ml-auto'
                  )}
                  aria-label="Close modal"
                >
                  <X className="w-5 h-5" />
                </button>
              )}
            </div>
          )}

          {/* Body */}
          <div className="px-6 py-4 overflow-y-auto max-h-[calc(100vh-16rem)]">
            {children}
          </div>

          {/* Footer */}
          {footer && (
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-surface-700 bg-surface-900/50 rounded-b-xl">
              {footer}
            </div>
          )}
        </div>
      </div>
    </>
  )

  return createPortal(modalContent, document.body)
}

// Convenience components for common footer patterns
export interface ModalFooterProps {
  children: React.ReactNode
  className?: string
}

export function ModalFooter({ children, className }: ModalFooterProps) {
  return (
    <div className={cn('flex items-center justify-end gap-3', className)}>
      {children}
    </div>
  )
}

export default Modal
