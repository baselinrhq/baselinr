'use client'

import { useState, useEffect, useRef } from 'react'
import { Clock, Database } from 'lucide-react'
import { searchTables } from '@/lib/api/lineage'
import type { TableInfoResponse, LineageSearchResult } from '@/types/lineage'

interface LineageSearchProps {
  onTableSelect: (table: TableInfoResponse) => void
  selectedTable?: TableInfoResponse | null
  placeholder?: string
}

export default function LineageSearch({
  onTableSelect,
  selectedTable,
  placeholder = 'Search tables...',
}: LineageSearchProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<LineageSearchResult[]>([])
  const [recentSearches, setRecentSearches] = useState<TableInfoResponse[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const searchRef = useRef<HTMLDivElement>(null)

  // Load recent searches from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem('lineage_recent_searches')
      if (stored) {
        setRecentSearches(JSON.parse(stored))
      }
    } catch {
      // Ignore parse errors
    }
  }, [])

  // Handle search
  useEffect(() => {
    console.log('Search query changed:', searchQuery, 'length:', searchQuery.length)
    
    if (searchQuery.length < 2) {
      console.log('Query too short, clearing results')
      setSearchResults([])
      setShowResults(false)
      return
    }

    const doSearch = async () => {
      console.log('Starting search for:', searchQuery)
      setIsLoading(true)
      try {
        const results = await searchTables(searchQuery, 20)
        console.log('Search results received:', results, 'count:', results.length)
        setSearchResults(results as LineageSearchResult[])
        setShowResults(true)
        console.log('Results set, showResults:', true)
      } catch (err) {
        console.error('Search failed:', err)
        setSearchResults([])
        // Still show results dropdown even on error to show "no results" message
        setShowResults(true)
      } finally {
        setIsLoading(false)
        console.log('Search completed, isLoading:', false)
      }
    }

    const timer = setTimeout(doSearch, 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  // Close results when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowResults(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleTableSelect = (table: TableInfoResponse) => {
    onTableSelect(table)
    setSearchQuery('')
    setShowResults(false)

    // Add to recent searches
    const updated = [table, ...recentSearches.filter(t => 
      !(t.table === table.table && t.schema === table.schema)
    )].slice(0, 5)
    setRecentSearches(updated)
    try {
      localStorage.setItem('lineage_recent_searches', JSON.stringify(updated))
    } catch {
      // Ignore storage errors
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      // TODO: Implement keyboard navigation
    } else if (e.key === 'Enter' && searchResults.length > 0) {
      e.preventDefault()
      handleTableSelect(searchResults[0])
    } else if (e.key === 'Escape') {
      setShowResults(false)
    }
  }

  console.log('LineageSearch render:', { searchQuery, searchResults: searchResults.length, showResults, isLoading })

  return (
    <div ref={searchRef} className="relative">
      <div className="relative">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => {
            const value = e.target.value
            console.log('Input onChange called with:', value)
            setSearchQuery(value)
          }}
          onFocus={() => {
            console.log('Input onFocus, searchQuery:', searchQuery, 'recentSearches:', recentSearches.length)
            if (searchQuery.length >= 2 || recentSearches.length > 0) {
              setShowResults(true)
            }
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full px-4 py-2 bg-surface-800/50 border border-surface-600 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
        />
        {isLoading && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-cyan-400"></div>
          </div>
        )}
      </div>

      {/* Search Results Dropdown */}
      {showResults && (
        <div className="absolute z-50 w-full mt-1 bg-surface-800 border border-surface-700 rounded-lg shadow-xl shadow-black/20 max-h-96 overflow-y-auto">
          {searchQuery.length >= 2 && searchResults.length > 0 && (
            <div className="p-2">
              <div className="text-xs font-medium text-slate-400 px-2 py-1">Search Results</div>
              {searchResults.map((table) => (
                <button
                  key={`${table.schema}.${table.table}`}
                  onClick={() => handleTableSelect(table)}
                  className="w-full px-3 py-2 text-left hover:bg-surface-700/50 focus:bg-surface-700/50 rounded-lg transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Database className="w-4 h-4 text-slate-500" />
                    <div className="flex-1">
                      <div className="font-medium text-white">{table.table}</div>
                      <div className="text-xs text-slate-400">{table.schema}</div>
                      {table.provider && (
                        <div className="text-xs text-slate-500 mt-1">Provider: {table.provider}</div>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}

          {searchQuery.length < 2 && recentSearches.length > 0 && (
            <div className="p-2">
              <div className="text-xs font-medium text-slate-400 px-2 py-1 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                Recent Searches
              </div>
              {recentSearches.map((table) => (
                <button
                  key={`${table.schema}.${table.table}`}
                  onClick={() => handleTableSelect(table)}
                  className="w-full px-3 py-2 text-left hover:bg-surface-700/50 focus:bg-surface-700/50 rounded-lg transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Database className="w-4 h-4 text-slate-500" />
                    <div className="flex-1">
                      <div className="font-medium text-white">{table.table}</div>
                      <div className="text-xs text-slate-400">{table.schema}</div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}

          {searchQuery.length >= 2 && searchResults.length === 0 && !isLoading && (
            <div className="p-4 text-center text-sm text-slate-400">
              No tables found matching &quot;{searchQuery}&quot;
            </div>
          )}
        </div>
      )}

      {/* Selected Table Display */}
      {selectedTable && !searchQuery && (
        <div className="mt-2 p-3 bg-cyan-500/10 rounded-lg text-sm border border-cyan-500/30">
          <div className="font-medium text-cyan-300">{selectedTable.table}</div>
          {selectedTable.schema && (
            <div className="text-xs text-cyan-400/70">{selectedTable.schema}</div>
          )}
        </div>
      )}
    </div>
  )
}

