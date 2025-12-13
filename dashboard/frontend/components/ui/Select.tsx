'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { ChevronDown, X, Check, Search } from 'lucide-react'
import { cn, generateId } from '@/lib/utils'

export interface SelectOption {
  value: string
  label: string
  group?: string
}

export interface SelectProps {
  options: SelectOption[]
  value?: string
  onChange: (value: string) => void
  placeholder?: string
  searchable?: boolean
  disabled?: boolean
  label?: string
  error?: string
  helperText?: string
  clearable?: boolean
  loading?: boolean
  className?: string
}

export function Select({
  options,
  value,
  onChange,
  placeholder = 'Select an option',
  searchable = false,
  disabled = false,
  label,
  error,
  helperText,
  clearable = false,
  loading = false,
  className,
}: SelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const id = useRef(generateId('select')).current

  // Ensure options is always an array
  const safeOptions = options || []

  // Filter options based on search query
  const filteredOptions = searchable && searchQuery
    ? safeOptions.filter(option =>
        option.label.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : safeOptions

  // Group options if they have group property
  const groupedOptions = filteredOptions.reduce<Record<string, SelectOption[]>>(
    (acc, option) => {
      const group = option.group || ''
      if (!acc[group]) acc[group] = []
      acc[group].push(option)
      return acc
    },
    {}
  )

  const selectedOption = safeOptions.find(o => o.value === value)

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false)
        setSearchQuery('')
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Reset highlighted index when options change
  useEffect(() => {
    setHighlightedIndex(-1)
  }, [searchQuery])

  // Scroll highlighted option into view
  useEffect(() => {
    if (highlightedIndex >= 0 && listRef.current) {
      const items = listRef.current.querySelectorAll('[role="option"]')
      items[highlightedIndex]?.scrollIntoView({ block: 'nearest' })
    }
  }, [highlightedIndex])

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (disabled) return

      switch (event.key) {
        case 'Enter':
          event.preventDefault()
          if (isOpen && highlightedIndex >= 0) {
            const option = filteredOptions[highlightedIndex]
            if (option) {
              onChange(option.value)
              setIsOpen(false)
              setSearchQuery('')
            }
          } else if (!isOpen) {
            setIsOpen(true)
          }
          break
        case 'Escape':
          setIsOpen(false)
          setSearchQuery('')
          break
        case 'ArrowDown':
          event.preventDefault()
          if (!isOpen) {
            setIsOpen(true)
          } else {
            setHighlightedIndex(prev =>
              prev < filteredOptions.length - 1 ? prev + 1 : 0
            )
          }
          break
        case 'ArrowUp':
          event.preventDefault()
          if (!isOpen) {
            setIsOpen(true)
          } else {
            setHighlightedIndex(prev =>
              prev > 0 ? prev - 1 : filteredOptions.length - 1
            )
          }
          break
      }
    },
    [disabled, isOpen, highlightedIndex, filteredOptions, onChange]
  )

  const handleSelectOption = (option: SelectOption) => {
    onChange(option.value)
    setIsOpen(false)
    setSearchQuery('')
  }

  const handleClear = (event: React.MouseEvent) => {
    event.stopPropagation()
    onChange('')
  }

  return (
    <div className={cn('w-full', className)} ref={containerRef}>
      {label && (
        <label
          htmlFor={id}
          className="block text-sm font-medium text-slate-300 mb-2"
        >
          {label}
        </label>
      )}

      <div className="relative">
        <button
          type="button"
          id={id}
          onClick={() => {
            if (!disabled) {
              setIsOpen(!isOpen)
              if (!isOpen && searchable) {
                setTimeout(() => inputRef.current?.focus(), 0)
              }
            }
          }}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          className={cn(
            'w-full flex items-center justify-between gap-2 px-3 py-2 border rounded-lg',
            'text-left transition-all bg-surface-800/50',
            'focus:outline-none focus:ring-2',
            disabled
              ? 'bg-surface-900 text-slate-600 cursor-not-allowed border-surface-700'
              : error
              ? 'border-danger-500 focus:border-danger-500 focus:ring-danger-500'
              : 'border-surface-600 focus:border-accent-500 focus:ring-accent-500',
            isOpen && 'ring-2 ring-accent-500 border-accent-500'
          )}
          aria-haspopup="listbox"
          aria-expanded={isOpen}
          aria-labelledby={label ? id : undefined}
        >
          <span
            className={cn(
              'flex-1 truncate',
              selectedOption ? 'text-slate-200' : 'text-slate-500'
            )}
          >
            {selectedOption ? selectedOption.label : placeholder}
          </span>

          <div className="flex items-center gap-1">
            {loading && (
              <svg
                className="w-4 h-4 animate-spin text-slate-500"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
            )}
            
            {clearable && selectedOption && !disabled && (
              <button
                type="button"
                onClick={handleClear}
                className="p-0.5 rounded hover:bg-surface-700 text-slate-500 hover:text-slate-300 transition-colors"
                aria-label="Clear selection"
              >
                <X className="w-4 h-4" />
              </button>
            )}
            
            <ChevronDown
              className={cn(
                'w-4 h-4 text-slate-500 transition-transform',
                isOpen && 'rotate-180'
              )}
            />
          </div>
        </button>

        {isOpen && (
          <div className="absolute z-50 w-full mt-1 bg-surface-800 border border-surface-700 rounded-lg shadow-xl shadow-black/20 overflow-hidden animate-fade-in">
            {searchable && (
              <div className="p-2 border-b border-surface-700">
                <div className="relative">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    ref={inputRef}
                    type="text"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Search..."
                    className="w-full pl-8 pr-3 py-1.5 text-sm bg-surface-900 border border-surface-600 rounded-md text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-accent-500 focus:border-accent-500"
                  />
                </div>
              </div>
            )}

            <ul
              ref={listRef}
              role="listbox"
              aria-labelledby={label ? id : undefined}
              className="py-1 max-h-60 overflow-auto"
            >
              {filteredOptions.length === 0 ? (
                <li className="px-3 py-2 text-sm text-slate-500">
                  No options found
                </li>
              ) : Object.keys(groupedOptions).length === 1 &&
                !Object.keys(groupedOptions)[0] ? (
                // No groups
                filteredOptions.map((option, index) => (
                  <li
                    key={option.value}
                    role="option"
                    aria-selected={option.value === value}
                    onClick={() => handleSelectOption(option)}
                    className={cn(
                      'flex items-center justify-between px-3 py-2 text-sm cursor-pointer transition-colors',
                      option.value === value
                        ? 'bg-accent-500/20 text-accent-300'
                        : index === highlightedIndex
                        ? 'bg-surface-700 text-slate-200'
                        : 'text-slate-300 hover:bg-surface-700/50'
                    )}
                  >
                    <span>{option.label}</span>
                    {option.value === value && (
                      <Check className="w-4 h-4 text-accent-400" />
                    )}
                  </li>
                ))
              ) : (
                // With groups
                Object.entries(groupedOptions).map(([group, groupOptions]) => (
                  <li key={group || 'default'}>
                    {group && (
                      <div className="px-3 py-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                        {group}
                      </div>
                    )}
                    <ul>
                      {groupOptions.map((option) => {
                        const flatIndex = filteredOptions.indexOf(option)
                        return (
                          <li
                            key={option.value}
                            role="option"
                            aria-selected={option.value === value}
                            onClick={() => handleSelectOption(option)}
                            className={cn(
                              'flex items-center justify-between px-3 py-2 text-sm cursor-pointer transition-colors',
                              option.value === value
                                ? 'bg-accent-500/20 text-accent-300'
                                : flatIndex === highlightedIndex
                                ? 'bg-surface-700 text-slate-200'
                                : 'text-slate-300 hover:bg-surface-700/50'
                            )}
                          >
                            <span>{option.label}</span>
                            {option.value === value && (
                              <Check className="w-4 h-4 text-accent-400" />
                            )}
                          </li>
                        )
                      })}
                    </ul>
                  </li>
                ))
              )}
            </ul>
          </div>
        )}
      </div>

      {error && (
        <p className="mt-1.5 text-sm text-danger-400">{error}</p>
      )}

      {helperText && !error && (
        <p className="mt-1.5 text-sm text-slate-500">{helperText}</p>
      )}
    </div>
  )
}

export default Select
