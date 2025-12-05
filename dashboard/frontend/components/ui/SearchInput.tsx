'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Search, X, Loader2 } from 'lucide-react'
import { cn, generateId, debounce } from '@/lib/utils'

export interface SearchSuggestion {
  value: string
  label: string
}

export interface SearchInputProps {
  value?: string
  onChange: (value: string) => void
  onSearch?: (value: string) => void
  placeholder?: string
  suggestions?: SearchSuggestion[]
  loading?: boolean
  debounceMs?: number
  disabled?: boolean
  className?: string
}

export function SearchInput({
  value: controlledValue,
  onChange,
  onSearch,
  placeholder = 'Search...',
  suggestions = [],
  loading = false,
  debounceMs = 300,
  disabled = false,
  className,
}: SearchInputProps) {
  const id = useRef(generateId('search')).current
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  
  const [internalValue, setInternalValue] = useState(controlledValue || '')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  
  const value = controlledValue !== undefined ? controlledValue : internalValue

  // Debounced search callback
  const debouncedSearch = useCallback(
    debounce((query: string) => {
      onSearch?.(query)
    }, debounceMs),
    [onSearch, debounceMs]
  )

  // Handle value change
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.value
    
    if (controlledValue === undefined) {
      setInternalValue(newValue)
    }
    
    onChange(newValue)
    
    if (onSearch) {
      debouncedSearch(newValue)
    }
    
    // Show suggestions when typing
    if (suggestions.length > 0 && newValue) {
      setShowSuggestions(true)
    }
  }

  // Filter suggestions based on input
  const filteredSuggestions = suggestions.filter(
    suggestion =>
      suggestion.label.toLowerCase().includes(value.toLowerCase()) ||
      suggestion.value.toLowerCase().includes(value.toLowerCase())
  )

  // Close suggestions on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setShowSuggestions(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Reset highlighted index when suggestions change
  useEffect(() => {
    setHighlightedIndex(-1)
  }, [value])

  // Handle keyboard navigation
  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (!showSuggestions || filteredSuggestions.length === 0) {
      if (event.key === 'Enter') {
        event.preventDefault()
        onSearch?.(value)
      }
      return
    }

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault()
        setHighlightedIndex(prev =>
          prev < filteredSuggestions.length - 1 ? prev + 1 : 0
        )
        break
      case 'ArrowUp':
        event.preventDefault()
        setHighlightedIndex(prev =>
          prev > 0 ? prev - 1 : filteredSuggestions.length - 1
        )
        break
      case 'Enter':
        event.preventDefault()
        if (highlightedIndex >= 0) {
          handleSelectSuggestion(filteredSuggestions[highlightedIndex])
        } else {
          onSearch?.(value)
          setShowSuggestions(false)
        }
        break
      case 'Escape':
        setShowSuggestions(false)
        break
    }
  }

  // Handle suggestion selection
  const handleSelectSuggestion = (suggestion: SearchSuggestion) => {
    if (controlledValue === undefined) {
      setInternalValue(suggestion.value)
    }
    onChange(suggestion.value)
    onSearch?.(suggestion.value)
    setShowSuggestions(false)
    inputRef.current?.focus()
  }

  // Handle clear
  const handleClear = () => {
    if (controlledValue === undefined) {
      setInternalValue('')
    }
    onChange('')
    onSearch?.('')
    setShowSuggestions(false)
    inputRef.current?.focus()
  }

  return (
    <div ref={containerRef} className={cn('relative w-full', className)}>
      <div className="relative">
        {/* Search icon */}
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        
        {/* Input */}
        <input
          ref={inputRef}
          type="text"
          id={id}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (value && filteredSuggestions.length > 0) {
              setShowSuggestions(true)
            }
          }}
          placeholder={placeholder}
          disabled={disabled}
          className={cn(
            'w-full pl-10 pr-10 py-2 border border-gray-300 rounded-lg',
            'text-gray-900 placeholder-gray-500',
            'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
            'disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed',
            'transition-colors'
          )}
          autoComplete="off"
          aria-autocomplete="list"
          aria-controls={showSuggestions ? `${id}-suggestions` : undefined}
          aria-expanded={showSuggestions}
        />
        
        {/* Right side: loading spinner or clear button */}
        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center">
          {loading && (
            <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
          )}
          
          {!loading && value && (
            <button
              type="button"
              onClick={handleClear}
              className="p-0.5 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
              aria-label="Clear search"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Suggestions dropdown */}
      {showSuggestions && filteredSuggestions.length > 0 && (
        <ul
          id={`${id}-suggestions`}
          role="listbox"
          className="search-suggestions entering"
        >
          {filteredSuggestions.map((suggestion, index) => (
            <li
              key={suggestion.value}
              role="option"
              aria-selected={index === highlightedIndex}
              onClick={() => handleSelectSuggestion(suggestion)}
              className={cn(
                'search-suggestion-item',
                index === highlightedIndex && 'highlighted'
              )}
            >
              <div className="flex items-center gap-2">
                <Search className="w-4 h-4 text-gray-400 flex-shrink-0" />
                <span className="text-sm text-gray-900">{suggestion.label}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default SearchInput
