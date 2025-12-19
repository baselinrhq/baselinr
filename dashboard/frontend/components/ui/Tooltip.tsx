'use client'

import {
  useState,
  useRef,
  useEffect,
  useCallback,
  cloneElement,
  isValidElement,
} from 'react'
import { createPortal } from 'react-dom'
import { cn, generateId } from '@/lib/utils'

export interface TooltipProps {
  content: React.ReactNode
  children: React.ReactElement
  position?: 'top' | 'bottom' | 'left' | 'right'
  trigger?: 'hover' | 'click'
  delay?: number
  disabled?: boolean
  className?: string
}

interface TooltipPosition {
  top: number
  left: number
}

// const ARROW_SIZE = 6
const OFFSET = 8

export function Tooltip({
  content,
  children,
  position = 'top',
  trigger = 'hover',
  delay = 200,
  disabled = false,
  className,
}: TooltipProps) {
  const id = useRef(generateId('tooltip')).current
  const triggerRef = useRef<HTMLElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>()
  
  const [isVisible, setIsVisible] = useState(false)
  const [isExiting, setIsExiting] = useState(false)
  const [tooltipPosition, setTooltipPosition] = useState<TooltipPosition>({
    top: 0,
    left: 0,
  })
  const [mounted, setMounted] = useState(false)

  // Handle mounting for portal
  useEffect(() => {
    setMounted(true)
  }, [])

  // Calculate tooltip position
  const calculatePosition = useCallback(() => {
    if (!triggerRef.current || !tooltipRef.current) return

    const triggerRect = triggerRef.current.getBoundingClientRect()
    const tooltipRect = tooltipRef.current.getBoundingClientRect()
    const scrollY = window.scrollY
    const scrollX = window.scrollX

    let top = 0
    let left = 0

    switch (position) {
      case 'top':
        top = triggerRect.top + scrollY - tooltipRect.height - OFFSET
        left =
          triggerRect.left +
          scrollX +
          triggerRect.width / 2 -
          tooltipRect.width / 2
        break
      case 'bottom':
        top = triggerRect.bottom + scrollY + OFFSET
        left =
          triggerRect.left +
          scrollX +
          triggerRect.width / 2 -
          tooltipRect.width / 2
        break
      case 'left':
        top =
          triggerRect.top +
          scrollY +
          triggerRect.height / 2 -
          tooltipRect.height / 2
        left = triggerRect.left + scrollX - tooltipRect.width - OFFSET
        break
      case 'right':
        top =
          triggerRect.top +
          scrollY +
          triggerRect.height / 2 -
          tooltipRect.height / 2
        left = triggerRect.right + scrollX + OFFSET
        break
    }

    // Keep tooltip within viewport bounds
    const padding = 10
    const maxLeft = window.innerWidth - tooltipRect.width - padding
    const maxTop = window.innerHeight + scrollY - tooltipRect.height - padding

    left = Math.max(padding, Math.min(left, maxLeft))
    top = Math.max(padding + scrollY, Math.min(top, maxTop))

    setTooltipPosition({ top, left })
  }, [position])

  // Show tooltip
  const show = useCallback(() => {
    if (disabled) return
    
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
    
    if (delay > 0) {
      timeoutRef.current = setTimeout(() => {
        setIsVisible(true)
        setIsExiting(false)
      }, delay)
    } else {
      setIsVisible(true)
      setIsExiting(false)
    }
  }, [disabled, delay])

  // Hide tooltip
  const hide = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
    
    setIsExiting(true)
    setTimeout(() => {
      setIsVisible(false)
      setIsExiting(false)
    }, 75) // Match exit animation duration
  }, [])

  // Toggle for click trigger
  const toggle = useCallback(() => {
    if (isVisible) {
      hide()
    } else {
      show()
    }
  }, [isVisible, show, hide])

  // Update position when visible
  useEffect(() => {
    if (isVisible) {
      calculatePosition()
    }
  }, [isVisible, calculatePosition])

  // Handle window resize and scroll
  useEffect(() => {
    if (!isVisible) return

    const handleReposition = () => calculatePosition()
    
    window.addEventListener('resize', handleReposition)
    window.addEventListener('scroll', handleReposition, true)
    
    return () => {
      window.removeEventListener('resize', handleReposition)
      window.removeEventListener('scroll', handleReposition, true)
    }
  }, [isVisible, calculatePosition])

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  // Close on outside click for click trigger
  useEffect(() => {
    if (trigger !== 'click' || !isVisible) return

    const handleClickOutside = (event: MouseEvent) => {
      if (
        triggerRef.current &&
        !triggerRef.current.contains(event.target as Node) &&
        tooltipRef.current &&
        !tooltipRef.current.contains(event.target as Node)
      ) {
        hide()
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [trigger, isVisible, hide])

  // Clone children with event handlers and ref
  const triggerElement = isValidElement(children)
    ? (cloneElement(children as React.ReactElement, {
        ref: (node: HTMLElement) => {
          triggerRef.current = node
          // Handle existing ref
          // Handle existing ref if present
          const elementWithRef = children as React.ReactElement & { ref?: React.Ref<HTMLElement> }
          if (elementWithRef.ref) {
            if (typeof elementWithRef.ref === 'function') {
              elementWithRef.ref(node)
            } else if (typeof elementWithRef.ref === 'object' && elementWithRef.ref !== null && 'current' in elementWithRef.ref) {
              (elementWithRef.ref as React.MutableRefObject<HTMLElement | null>).current = node
            }
          }
        },
        'aria-describedby': isVisible ? id : undefined,
        ...(trigger === 'hover'
          ? {
              onMouseEnter: (e: React.MouseEvent<HTMLElement>) => {
                show()
                ;(children.props as React.HTMLAttributes<HTMLElement>)?.onMouseEnter?.(e as React.MouseEvent<HTMLElement>)
              },
              onMouseLeave: (e: React.MouseEvent<HTMLElement>) => {
                hide()
                ;(children.props as React.HTMLAttributes<HTMLElement>)?.onMouseLeave?.(e as React.MouseEvent<HTMLElement>)
              },
              onFocus: (e: React.FocusEvent<HTMLElement>) => {
                show()
                ;(children.props as React.HTMLAttributes<HTMLElement>)?.onFocus?.(e as React.FocusEvent<HTMLElement>)
              },
              onBlur: (e: React.FocusEvent<HTMLElement>) => {
                hide()
                ;(children.props as React.HTMLAttributes<HTMLElement>)?.onBlur?.(e as React.FocusEvent<HTMLElement>)
              },
            }
          : {
              onClick: (e: React.MouseEvent<HTMLElement>) => {
                toggle()
                ;(children.props as React.HTMLAttributes<HTMLElement>)?.onClick?.(e as React.MouseEvent<HTMLElement>)
              },
            }),
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } as any) as React.ReactElement)
    : children

  // Arrow class based on position
  const arrowClass = {
    top: 'tooltip-arrow tooltip-arrow-top',
    bottom: 'tooltip-arrow tooltip-arrow-bottom',
    left: 'tooltip-arrow tooltip-arrow-left',
    right: 'tooltip-arrow tooltip-arrow-right',
  }[position]

  // Render tooltip
  const tooltipElement = isVisible && mounted && (
    <>
      {createPortal(
        <div
          ref={tooltipRef}
          id={id}
          role="tooltip"
          className={cn(
            'tooltip',
            isExiting ? 'exiting' : 'entering',
            className
          )}
          style={{
            top: tooltipPosition.top,
            left: tooltipPosition.left,
          }}
        >
          {content}
          <div className={arrowClass} />
        </div>,
        document.body
      )}
    </>
  )

  return (
    <>
      {triggerElement}
      {tooltipElement}
    </>
  )
}

export default Tooltip
