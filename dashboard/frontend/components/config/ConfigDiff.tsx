'use client'

import { useState } from 'react'
import { X, ChevronDown, ChevronRight, Plus, Minus, Edit } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { ConfigDiffResponse } from '@/types/config'

export interface ConfigDiffProps {
  diff: ConfigDiffResponse
  viewMode?: 'side-by-side' | 'unified' | 'tree'
  onClose?: () => void
}

export function ConfigDiff({ diff, viewMode = 'tree', onClose }: ConfigDiffProps) {
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set())
  const [selectedViewMode, setSelectedViewMode] = useState<'side-by-side' | 'unified' | 'tree'>(viewMode)

  const togglePath = (path: string) => {
    const newExpanded = new Set(expandedPaths)
    if (newExpanded.has(path)) {
      newExpanded.delete(path)
    } else {
      newExpanded.add(path)
    }
    setExpandedPaths(newExpanded)
  }

  const renderValue = (value: unknown): string => {
    if (value === null || value === undefined) {
      return 'null'
    }
    if (typeof value === 'string') {
      return `"${value}"`
    }
    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2)
    }
    return String(value)
  }

  const renderTreeDiff = () => {
    const allPaths = new Set<string>()
    
    // Collect all paths
    Object.keys(diff.added).forEach(path => allPaths.add(path))
    Object.keys(diff.removed).forEach(path => allPaths.add(path))
    Object.keys(diff.changed).forEach(path => allPaths.add(path))

    // Group by top-level key
    const grouped: Record<string, string[]> = {}
    allPaths.forEach(path => {
      const parts = path.split('.')
      const topLevel = parts[0]
      if (!grouped[topLevel]) {
        grouped[topLevel] = []
      }
      grouped[topLevel].push(path)
    })

    return (
      <div className="space-y-2">
        {Object.entries(grouped).map(([topLevel, paths]) => {
          const isExpanded = expandedPaths.has(topLevel)
          const hasChanges = paths.some(
            p => diff.added[p] !== undefined || diff.removed[p] !== undefined || diff.changed[p] !== undefined
          )

          return (
            <div key={topLevel} className="border border-gray-200 rounded-lg">
              <button
                onClick={() => togglePath(topLevel)}
                className="w-full px-4 py-2 flex items-center justify-between text-left hover:bg-gray-50 rounded-t-lg"
              >
                <div className="flex items-center gap-2">
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-gray-500" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-gray-500" />
                  )}
                  <span className="font-medium text-gray-900">{topLevel}</span>
                  {hasChanges && (
                    <Badge variant="warning" className="text-xs">
                      {paths.length} change{paths.length !== 1 ? 's' : ''}
                    </Badge>
                  )}
                </div>
              </button>

              {isExpanded && (
                <div className="px-4 pb-4 border-t border-gray-200 bg-gray-50 space-y-2">
                  {paths.map((path) => {
                    const added = diff.added[path]
                    const removed = diff.removed[path]
                    const changed = diff.changed[path]

                    return (
                      <div key={path} className="bg-white rounded border border-gray-200 p-3">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-sm font-mono text-gray-700">{path}</span>
                          {added !== undefined && (
                            <Badge variant="success" className="text-xs">
                              <Plus className="w-3 h-3 mr-1" />
                              Added
                            </Badge>
                          )}
                          {removed !== undefined && (
                            <Badge variant="error" className="text-xs">
                              <Minus className="w-3 h-3 mr-1" />
                              Removed
                            </Badge>
                          )}
                          {changed !== undefined && (
                            <Badge variant="warning" className="text-xs">
                              <Edit className="w-3 h-3 mr-1" />
                              Changed
                            </Badge>
                          )}
                        </div>

                        {added !== undefined && (
                          <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded text-sm">
                            <div className="text-green-800 font-medium mb-1">New value:</div>
                            <pre className="text-green-700 whitespace-pre-wrap font-mono text-xs">
                              {renderValue(added)}
                            </pre>
                          </div>
                        )}

                        {removed !== undefined && (
                          <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm">
                            <div className="text-red-800 font-medium mb-1">Old value:</div>
                            <pre className="text-red-700 whitespace-pre-wrap font-mono text-xs">
                              {renderValue(removed)}
                            </pre>
                          </div>
                        )}

                        {changed !== undefined && (
                          <div className="mt-2 space-y-2">
                            <div className="p-2 bg-red-50 border border-red-200 rounded text-sm">
                              <div className="text-red-800 font-medium mb-1">Old:</div>
                              <pre className="text-red-700 whitespace-pre-wrap font-mono text-xs">
                                {renderValue(changed.old)}
                              </pre>
                            </div>
                            <div className="p-2 bg-green-50 border border-green-200 rounded text-sm">
                              <div className="text-green-800 font-medium mb-1">New:</div>
                              <pre className="text-green-700 whitespace-pre-wrap font-mono text-xs">
                                {renderValue(changed.new)}
                              </pre>
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>
    )
  }

  const renderSideBySide = () => {
    // For side-by-side, show added/removed/changed in columns
    return (
      <div className="grid grid-cols-2 gap-4">
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-2">Removed / Old Values</h4>
          <div className="space-y-2">
            {Object.entries(diff.removed).map(([path, value]) => (
              <div key={path} className="p-3 bg-red-50 border border-red-200 rounded">
                <div className="text-xs font-mono text-red-800 mb-1">{path}</div>
                <pre className="text-xs text-red-700 whitespace-pre-wrap font-mono">
                  {renderValue(value)}
                </pre>
              </div>
            ))}
            {Object.entries(diff.changed).map(([path, change]) => (
              <div key={path} className="p-3 bg-yellow-50 border border-yellow-200 rounded">
                <div className="text-xs font-mono text-yellow-800 mb-1">{path}</div>
                <pre className="text-xs text-yellow-700 whitespace-pre-wrap font-mono">
                  {renderValue(change.old)}
                </pre>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-2">Added / New Values</h4>
          <div className="space-y-2">
            {Object.entries(diff.added).map(([path, value]) => (
              <div key={path} className="p-3 bg-green-50 border border-green-200 rounded">
                <div className="text-xs font-mono text-green-800 mb-1">{path}</div>
                <pre className="text-xs text-green-700 whitespace-pre-wrap font-mono">
                  {renderValue(value)}
                </pre>
              </div>
            ))}
            {Object.entries(diff.changed).map(([path, change]) => (
              <div key={path} className="p-3 bg-yellow-50 border border-yellow-200 rounded">
                <div className="text-xs font-mono text-yellow-800 mb-1">{path}</div>
                <pre className="text-xs text-yellow-700 whitespace-pre-wrap font-mono">
                  {renderValue(change.new)}
                </pre>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  const totalChanges = Object.keys(diff.added).length + 
                       Object.keys(diff.removed).length + 
                       Object.keys(diff.changed).length

  return (
    <div className="bg-white rounded-lg shadow-lg max-w-6xl w-full max-h-[90vh] flex flex-col">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Configuration Diff</h2>
          <p className="text-sm text-gray-600 mt-1">
            Comparing version <code className="bg-gray-100 px-1 rounded">{diff.version_id.substring(0, 8)}...</code> with{' '}
            {diff.compare_with === 'current' ? 'current' : <code className="bg-gray-100 px-1 rounded">{diff.compare_with.substring(0, 8)}...</code>}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setSelectedViewMode('tree')}
              className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                selectedViewMode === 'tree'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Tree
            </button>
            <button
              onClick={() => setSelectedViewMode('side-by-side')}
              className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                selectedViewMode === 'side-by-side'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Side-by-Side
            </button>
          </div>
          {onClose && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              icon={<X className="w-4 h-4" />}
            >
              Close
            </Button>
          )}
        </div>
      </div>

      {/* Summary */}
      <div className="px-6 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <Badge variant="success">
              +{Object.keys(diff.added).length} added
            </Badge>
            <Badge variant="error">
              -{Object.keys(diff.removed).length} removed
            </Badge>
            <Badge variant="warning">
              ~{Object.keys(diff.changed).length} changed
            </Badge>
          </div>
          <span className="text-gray-600">
            {totalChanges} total change{totalChanges !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      {/* Diff Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {totalChanges === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-600">No differences found between versions.</p>
          </div>
        ) : selectedViewMode === 'tree' ? (
          renderTreeDiff()
        ) : (
          renderSideBySide()
        )}
      </div>
    </div>
  )
}

export default ConfigDiff

