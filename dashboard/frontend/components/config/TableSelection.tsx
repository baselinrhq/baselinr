'use client'

import { useState } from 'react'
import { Plus, Edit, Trash2, Eye, Database } from 'lucide-react'
import { TablePattern } from '@/types/config'
import { TableInfo, previewTablePattern } from '@/lib/api/tables'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { TablePatternBuilder } from './TablePatternBuilder'
import { TablePreview } from './TablePreview'
import { Modal } from '@/components/ui/Modal'

export interface TableSelectionProps {
  tables: TablePattern[]
  onChange: (tables: TablePattern[]) => void
  errors?: Record<string, string>
  isLoading?: boolean
  onPreview?: (pattern: TablePattern) => Promise<TableInfo[]>
}

/**
 * Get a human-readable summary of a table pattern
 */
function getPatternSummary(pattern: TablePattern): string {
  if (pattern.table) {
    return `${pattern.schema || '?'}.${pattern.table}`
  }
  if (pattern.pattern) {
    return `Pattern: ${pattern.pattern} (${pattern.pattern_type || 'wildcard'})`
  }
  if (pattern.select_schema && pattern.schema) {
    return `Schema: ${pattern.schema}`
  }
  if (pattern.select_all_schemas) {
    return 'All Schemas'
  }
  if (pattern.tags && pattern.tags.length > 0) {
    return `Tags: ${pattern.tags.join(', ')}`
  }
  if (pattern.tags_any && pattern.tags_any.length > 0) {
    return `Tags (any): ${pattern.tags_any.join(', ')}`
  }
  if (pattern.dbt_ref) {
    return `dbt: ${pattern.dbt_ref}`
  }
  if (pattern.dbt_selector) {
    return `dbt: ${pattern.dbt_selector}`
  }
  return 'Unknown pattern'
}

/**
 * Get pattern type badge
 */
function getPatternType(pattern: TablePattern): string {
  if (pattern.table) return 'Explicit'
  if (pattern.pattern) return 'Pattern'
  if (pattern.select_schema || pattern.select_all_schemas) return 'Schema'
  if (pattern.tags || pattern.tags_any) return 'Tag'
  if (pattern.dbt_ref || pattern.dbt_selector) return 'dbt'
  return 'Unknown'
}

export function TableSelection({
  tables,
  onChange,
  isLoading = false,
  onPreview: externalPreview,
}: TableSelectionProps) {
  const [builderOpen, setBuilderOpen] = useState(false)
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [previewPattern, setPreviewPattern] = useState<TablePattern | null>(null)
  const [previewTables, setPreviewTables] = useState<TableInfo[]>([])
  const [isPreviewing, setIsPreviewing] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)

  const handleAddPattern = () => {
    setEditingIndex(null)
    setBuilderOpen(true)
  }

  const handleEditPattern = (index: number) => {
    setEditingIndex(index)
    setBuilderOpen(true)
  }

  const handleDeletePattern = (index: number) => {
    const newTables = [...tables]
    newTables.splice(index, 1)
    onChange(newTables)
  }

  const handleSavePattern = (pattern: TablePattern) => {
    const newTables = [...tables]
    if (editingIndex !== null) {
      newTables[editingIndex] = pattern
    } else {
      newTables.push(pattern)
    }
    onChange(newTables)
    setBuilderOpen(false)
    setEditingIndex(null)
  }

  const handlePreviewPattern = async (pattern: TablePattern) => {
    setPreviewPattern(pattern)
    setIsPreviewing(true)
    setPreviewError(null)
    
    try {
      if (externalPreview) {
        const tables = await externalPreview(pattern)
        setPreviewTables(tables)
      } else {
        const result = await previewTablePattern(pattern)
        setPreviewTables(result.tables)
      }
    } catch (error) {
      setPreviewError(
        error instanceof Error ? error.message : 'Failed to preview pattern'
      )
      setPreviewTables([])
    } finally {
      setIsPreviewing(false)
    }
  }

  const handleClosePreview = () => {
    setPreviewPattern(null)
    setPreviewTables([])
    setPreviewError(null)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">Table Patterns</h3>
          <p className="text-sm text-slate-400 mt-1">
            Configure which tables to profile using patterns or explicit selection
          </p>
        </div>
        <Button
          onClick={handleAddPattern}
          icon={<Plus className="w-4 h-4" />}
          disabled={isLoading}
        >
          Add Pattern
        </Button>
      </div>

      {tables.length === 0 ? (
        <Card>
          <div className="py-12 text-center">
            <div className="text-slate-500 mb-4">
              <Database className="w-12 h-12 mx-auto" />
            </div>
            <h4 className="text-sm font-medium text-white mb-2">
              No table patterns configured
            </h4>
            <p className="text-sm text-slate-400 mb-4">
              Add a pattern to start profiling tables
            </p>
            <Button
              variant="outline"
              onClick={handleAddPattern}
              icon={<Plus className="w-4 h-4" />}
            >
              Add Your First Pattern
            </Button>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {tables.map((pattern, index) => (
            <Card key={index} hover>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="info" size="sm">
                      {getPatternType(pattern)}
                    </Badge>
                    {pattern.override_priority !== null && pattern.override_priority !== undefined && (
                      <Badge variant="default" size="sm">
                        Priority: {pattern.override_priority}
                      </Badge>
                    )}
                    {pattern.database && (
                      <Badge variant="default" size="sm">
                        DB: {pattern.database}
                      </Badge>
                    )}
                  </div>
                  <h4 className="text-sm font-medium text-white mb-1">
                    {getPatternSummary(pattern)}
                  </h4>
                  <div className="text-xs text-slate-400 space-y-1">
                    {pattern.schema && (
                      <div>Schema: {pattern.schema}</div>
                    )}
                    {pattern.table_types && pattern.table_types.length > 0 && (
                      <div>Types: {pattern.table_types.join(', ')}</div>
                    )}
                    {pattern.min_rows !== null && pattern.min_rows !== undefined && (
                      <div>Min rows: {pattern.min_rows.toLocaleString()}</div>
                    )}
                    {pattern.max_rows !== null && pattern.max_rows !== undefined && (
                      <div>Max rows: {pattern.max_rows.toLocaleString()}</div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handlePreviewPattern(pattern)}
                    icon={<Eye className="w-4 h-4" />}
                    disabled={isLoading}
                  >
                    Preview
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleEditPattern(index)}
                    icon={<Edit className="w-4 h-4" />}
                    disabled={isLoading}
                  >
                    Edit
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDeletePattern(index)}
                    icon={<Trash2 className="w-4 h-4" />}
                    disabled={isLoading}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Pattern Builder Modal */}
      {builderOpen && (
        <TablePatternBuilder
          pattern={editingIndex !== null ? tables[editingIndex] : undefined}
          onSave={handleSavePattern}
          onCancel={() => {
            setBuilderOpen(false)
            setEditingIndex(null)
          }}
          onPreview={externalPreview}
        />
      )}

      {/* Preview Modal */}
      {previewPattern && (
        <Modal
          isOpen={true}
          onClose={handleClosePreview}
          title={`Preview: ${getPatternSummary(previewPattern)}`}
          size="xl"
        >
          <TablePreview
            tables={previewTables}
            isLoading={isPreviewing}
            error={previewError}
            onRefresh={() => handlePreviewPattern(previewPattern)}
          />
        </Modal>
      )}
    </div>
  )
}

