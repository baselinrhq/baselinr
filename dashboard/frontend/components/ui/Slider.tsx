'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { cn, generateId, clamp } from '@/lib/utils'

export interface SliderProps {
  value?: number | [number, number]
  defaultValue?: number | [number, number]
  onChange?: (value: number | [number, number]) => void
  min?: number
  max?: number
  step?: number
  showValue?: boolean
  disabled?: boolean
  label?: string
  className?: string
}

export function Slider({
  value: controlledValue,
  defaultValue = 0,
  onChange,
  min = 0,
  max = 100,
  step = 1,
  showValue = false,
  disabled = false,
  label,
  className,
}: SliderProps) {
  const id = useRef(generateId('slider')).current
  const trackRef = useRef<HTMLDivElement>(null)
  const [dragging, setDragging] = useState<'single' | 'min' | 'max' | null>(null)
  
  // Determine if this is a range slider
  const isRange = Array.isArray(controlledValue ?? defaultValue)
  
  // Support controlled and uncontrolled modes
  const isControlled = controlledValue !== undefined
  const [internalValue, setInternalValue] = useState(defaultValue)
  const value = isControlled ? controlledValue : internalValue

  // Get normalized values
  const normalizedValue = isRange
    ? (value as [number, number])
    : [min, value as number]
  
  const [minVal, maxVal] = normalizedValue

  // Convert value to percentage
  const valueToPercent = (val: number) => ((val - min) / (max - min)) * 100

  // Convert percentage to value
  const percentToValue = (percent: number) => {
    const rawValue = (percent / 100) * (max - min) + min
    // Snap to step
    const stepped = Math.round(rawValue / step) * step
    return clamp(stepped, min, max)
  }

  // Get position from mouse/touch event
  const getPositionFromEvent = useCallback(
    (event: MouseEvent | TouchEvent) => {
      if (!trackRef.current) return 0
      
      const rect = trackRef.current.getBoundingClientRect()
      const clientX =
        'touches' in event
          ? event.touches[0]?.clientX ?? 0
          : event.clientX
      
      const percent = ((clientX - rect.left) / rect.width) * 100
      return clamp(percent, 0, 100)
    },
    []
  )

  // Update value based on position and which thumb is being dragged
  const updateValue = useCallback(
    (percent: number) => {
      const newVal = percentToValue(percent)
      
      if (isRange) {
        const [currentMin, currentMax] = normalizedValue
        
        if (dragging === 'min') {
          const newMin = Math.min(newVal, currentMax)
          const newValue: [number, number] = [newMin, currentMax]
          
          if (!isControlled) setInternalValue(newValue)
          onChange?.(newValue)
        } else if (dragging === 'max') {
          const newMax = Math.max(newVal, currentMin)
          const newValue: [number, number] = [currentMin, newMax]
          
          if (!isControlled) setInternalValue(newValue)
          onChange?.(newValue)
        }
      } else {
        if (!isControlled) setInternalValue(newVal)
        onChange?.(newVal)
      }
    },
    [dragging, isControlled, isRange, normalizedValue, onChange]
  )

  // Handle mouse move
  useEffect(() => {
    if (!dragging) return

    const handleMove = (event: MouseEvent | TouchEvent) => {
      const percent = getPositionFromEvent(event)
      updateValue(percent)
    }

    const handleEnd = () => {
      setDragging(null)
    }

    document.addEventListener('mousemove', handleMove)
    document.addEventListener('mouseup', handleEnd)
    document.addEventListener('touchmove', handleMove)
    document.addEventListener('touchend', handleEnd)

    return () => {
      document.removeEventListener('mousemove', handleMove)
      document.removeEventListener('mouseup', handleEnd)
      document.removeEventListener('touchmove', handleMove)
      document.removeEventListener('touchend', handleEnd)
    }
  }, [dragging, getPositionFromEvent, updateValue])

  // Handle track click
  const handleTrackClick = (event: React.MouseEvent) => {
    if (disabled) return
    
    const rect = trackRef.current?.getBoundingClientRect()
    if (!rect) return
    
    const percent = ((event.clientX - rect.left) / rect.width) * 100
    const newVal = percentToValue(clamp(percent, 0, 100))
    
    if (isRange) {
      const [currentMin, currentMax] = normalizedValue
      // Determine which thumb to move based on proximity
      const distToMin = Math.abs(newVal - currentMin)
      const distToMax = Math.abs(newVal - currentMax)
      
      if (distToMin <= distToMax) {
        const newValue: [number, number] = [newVal, currentMax]
        if (!isControlled) setInternalValue(newValue)
        onChange?.(newValue)
      } else {
        const newValue: [number, number] = [currentMin, newVal]
        if (!isControlled) setInternalValue(newValue)
        onChange?.(newValue)
      }
    } else {
      if (!isControlled) setInternalValue(newVal)
      onChange?.(newVal)
    }
  }

  // Handle keyboard navigation
  const handleKeyDown = (
    event: React.KeyboardEvent,
    thumbType: 'single' | 'min' | 'max'
  ) => {
    if (disabled) return
    
    let delta = 0
    switch (event.key) {
      case 'ArrowLeft':
      case 'ArrowDown':
        delta = -step
        break
      case 'ArrowRight':
      case 'ArrowUp':
        delta = step
        break
      case 'Home':
        delta = min - (thumbType === 'min' || thumbType === 'single' ? minVal : maxVal)
        break
      case 'End':
        delta = max - (thumbType === 'max' || thumbType === 'single' ? maxVal : minVal)
        break
      default:
        return
    }
    
    event.preventDefault()
    
    if (isRange) {
      const [currentMin, currentMax] = normalizedValue
      if (thumbType === 'min') {
        const newMin = clamp(currentMin + delta, min, currentMax)
        const newValue: [number, number] = [newMin, currentMax]
        if (!isControlled) setInternalValue(newValue)
        onChange?.(newValue)
      } else {
        const newMax = clamp(currentMax + delta, currentMin, max)
        const newValue: [number, number] = [currentMin, newMax]
        if (!isControlled) setInternalValue(newValue)
        onChange?.(newValue)
      }
    } else {
      const currentVal = value as number
      const newVal = clamp(currentVal + delta, min, max)
      if (!isControlled) setInternalValue(newVal)
      onChange?.(newVal)
    }
  }

  return (
    <div className={cn(disabled && 'slider-disabled', className)}>
      {(label || showValue) && (
        <div className="flex items-center justify-between mb-2">
          {label && (
            <label
              htmlFor={id}
              className={cn(
                'text-sm font-medium',
                disabled ? 'text-gray-400' : 'text-gray-700'
              )}
            >
              {label}
            </label>
          )}
          
          {showValue && (
            <span className="text-sm text-gray-600">
              {isRange
                ? `${normalizedValue[0]} - ${normalizedValue[1]}`
                : value as number}
            </span>
          )}
        </div>
      )}
      
      <div
        ref={trackRef}
        className="slider-track relative h-1.5 cursor-pointer"
        onClick={handleTrackClick}
        role="presentation"
      >
        {/* Fill */}
        <div
          className="slider-fill"
          style={{
            left: isRange ? `${valueToPercent(minVal)}%` : '0%',
            right: `${100 - valueToPercent(maxVal)}%`,
          }}
        />
        
        {/* Range min thumb */}
        {isRange && (
          <button
            type="button"
            role="slider"
            id={id}
            aria-valuemin={min}
            aria-valuemax={maxVal}
            aria-valuenow={minVal}
            aria-label={label ? `${label} minimum` : 'Minimum value'}
            disabled={disabled}
            className="slider-thumb"
            style={{ left: `${valueToPercent(minVal)}%` }}
            onMouseDown={() => !disabled && setDragging('min')}
            onTouchStart={() => !disabled && setDragging('min')}
            onKeyDown={e => handleKeyDown(e, 'min')}
          />
        )}
        
        {/* Single or range max thumb */}
        <button
          type="button"
          role="slider"
          id={isRange ? `${id}-max` : id}
          aria-valuemin={isRange ? minVal : min}
          aria-valuemax={max}
          aria-valuenow={isRange ? maxVal : (value as number)}
          aria-label={
            isRange
              ? label
                ? `${label} maximum`
                : 'Maximum value'
              : label || 'Value'
          }
          disabled={disabled}
          className="slider-thumb"
          style={{ left: `${valueToPercent(maxVal)}%` }}
          onMouseDown={() => !disabled && setDragging(isRange ? 'max' : 'single')}
          onTouchStart={() => !disabled && setDragging(isRange ? 'max' : 'single')}
          onKeyDown={e => handleKeyDown(e, isRange ? 'max' : 'single')}
        />
      </div>
    </div>
  )
}

export default Slider
