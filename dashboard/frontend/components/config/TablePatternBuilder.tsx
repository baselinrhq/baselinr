'use client'

import { useState, useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { TablePattern } from '@/types/config'
import { TableInfo, previewTablePattern } from '@/lib/api/tables'
import { listConnections } from '@/lib/api/connections'
import { ConnectionsListResponse } from '@/types/connection'
import { Modal } from '@/components/ui/Modal'
import { Tabs } from '@/components/ui/Tabs'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { Select, SelectOption } from '@/components/ui/Select'
import { Button } from '@/components/ui/Button'
import { TablePreview } from './TablePreview'
import { Eye } from 'lucide-react'

export interface TablePatternBuilderProps {
  pattern?: TablePattern
  onSave: (pattern: TablePattern) => void
  onCancel: () => void
  onPreview?: (pattern: TablePattern) => Promise<TableInfo[]>
}

type SelectionMethod = 'explicit' | 'pattern' | 'schema' | 'database' | 'tag' | 'dbt'

const SELECTION_METHODS = [
  { id: 'explicit', label: 'Explicit Table' },
  { id: 'pattern', label: 'Pattern-Based' },
  { id: 'schema', label: 'Schema-Based' },
  { id: 'database', label: 'Database-Level' },
  { id: 'tag', label: 'Tag-Based' },
  { id: 'dbt', label: 'dbt-Based' },
] as const

const PATTERN_TYPE_OPTIONS: SelectOption[] = [
  { value: 'wildcard', label: 'Wildcard' },
  { value: 'regex', label: 'Regex' },
]

/**
 * Determine selection method from pattern
 */
function getSelectionMethod(pattern?: TablePattern): SelectionMethod {
  if (!pattern) return 'explicit'
  
  if (pattern.dbt_ref || pattern.dbt_selector) return 'dbt'
  if (pattern.tags || pattern.tags_any) return 'tag'
  if (pattern.select_all_schemas || (pattern.select_schema && !pattern.table && !pattern.pattern)) return 'database'
  if (pattern.select_schema && !pattern.table && !pattern.pattern) return 'schema'
  if (pattern.pattern) return 'pattern'
  if (pattern.table) return 'explicit'
  
  return 'explicit'
}

/**
 * Parse comma-separated string into array
 */
function parseArrayString(value: string | null | undefined): string[] {
  if (!value) return []
  if (Array.isArray(value)) return value
  return value
    .split(',')
    .map(s => s.trim())
    .filter(s => s.length > 0)
}

/**
 * Format array as comma-separated string
 */
function formatArrayString(value: string[] | null | undefined): string {
  if (!value || value.length === 0) return ''
  return value.join(', ')
}

export function TablePatternBuilder({
  pattern: initialPattern,
  onSave,
  onCancel,
  onPreview: externalPreview,
}: TablePatternBuilderProps) {
  const [selectionMethod, setSelectionMethod] = useState<SelectionMethod>(
    getSelectionMethod(initialPattern)
  )
  const [pattern, setPattern] = useState<TablePattern>(() => {
    if (initialPattern) {
      return { ...initialPattern }
    }
    return {}
  })
  const [previewTables, setPreviewTables] = useState<TableInfo[]>([])
  const [isPreviewing, setIsPreviewing] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [showPreview, setShowPreview] = useState(false)

  // Fetch saved connections for database selector
  const { data: connectionsData } = useQuery<ConnectionsListResponse>({
    queryKey: ['connections'],
    queryFn: listConnections,
    retry: false,
  })

  const databaseOptions: SelectOption[] = useMemo(() => {
    const options: SelectOption[] = [
      { value: '', label: 'Use Source Connection' },
    ]
    const savedConnections = connectionsData?.connections || []
    savedConnections.forEach((conn) => {
      options.push({
        value: conn.id,
        label: `${conn.name} (${conn.connection.type})`,
      })
    })
    return options
  }, [connectionsData?.connections])

  // Update pattern when selection method changes
  useEffect(() => {
    if (selectionMethod === 'explicit') {
      setPattern((p) => ({
        ...p,
        pattern: null,
        pattern_type: null,
        schema_pattern: null,
        select_all_schemas: null,
        select_schema: null,
        tags: null,
        tags_any: null,
        dbt_ref: null,
        dbt_selector: null,
        dbt_project_path: null,
        dbt_manifest_path: null,
      }))
    } else if (selectionMethod === 'pattern') {
      setPattern((p) => ({
        ...p,
        table: null,
        select_all_schemas: null,
        select_schema: null,
        tags: null,
        tags_any: null,
        dbt_ref: null,
        dbt_selector: null,
        dbt_project_path: null,
        dbt_manifest_path: null,
      }))
    } else if (selectionMethod === 'schema') {
      setPattern((p) => ({
        ...p,
        table: null,
        pattern: null,
        pattern_type: null,
        schema_pattern: null,
        select_all_schemas: null,
        tags: null,
        tags_any: null,
        dbt_ref: null,
        dbt_selector: null,
        dbt_project_path: null,
        dbt_manifest_path: null,
      }))
    } else if (selectionMethod === 'database') {
      setPattern((p) => ({
        ...p,
        table: null,
        pattern: null,
        pattern_type: null,
        schema_pattern: null,
        schema: null,
        select_schema: null,
        tags: null,
        tags_any: null,
        dbt_ref: null,
        dbt_selector: null,
        dbt_project_path: null,
        dbt_manifest_path: null,
      }))
    } else if (selectionMethod === 'tag') {
      setPattern((p) => ({
        ...p,
        table: null,
        pattern: null,
        pattern_type: null,
        schema_pattern: null,
        select_all_schemas: null,
        select_schema: null,
        dbt_ref: null,
        dbt_selector: null,
        dbt_project_path: null,
        dbt_manifest_path: null,
      }))
    } else if (selectionMethod === 'dbt') {
      setPattern((p) => ({
        ...p,
        table: null,
        pattern: null,
        pattern_type: null,
        schema_pattern: null,
        select_all_schemas: null,
        select_schema: null,
        tags: null,
        tags_any: null,
      }))
    }
  }, [selectionMethod])

  const handlePreview = async () => {
    if (!externalPreview) {
      setIsPreviewing(true)
      setPreviewError(null)
      setShowPreview(true)
      
      try {
        const result = await previewTablePattern(pattern)
        setPreviewTables(result.tables)
      } catch (error) {
        setPreviewError(
          error instanceof Error ? error.message : 'Failed to preview pattern'
        )
        setPreviewTables([])
      } finally {
        setIsPreviewing(false)
      }
    } else {
      setIsPreviewing(true)
      setPreviewError(null)
      setShowPreview(true)
      
      try {
        const tables = await externalPreview(pattern)
        setPreviewTables(tables)
      } catch (error) {
        setPreviewError(
          error instanceof Error ? error.message : 'Failed to preview pattern'
        )
        setPreviewTables([])
      } finally {
        setIsPreviewing(false)
      }
    }
  }

  const handleSave = () => {
    // Clean up null/empty values
    const cleanedPattern: TablePattern = {}
    
    if (pattern.database) cleanedPattern.database = pattern.database
    if (pattern.schema) cleanedPattern.schema = pattern.schema
    if (pattern.table) cleanedPattern.table = pattern.table
    if (pattern.pattern) cleanedPattern.pattern = pattern.pattern
    if (pattern.pattern_type) cleanedPattern.pattern_type = pattern.pattern_type
    if (pattern.schema_pattern) cleanedPattern.schema_pattern = pattern.schema_pattern
    if (pattern.select_all_schemas !== null && pattern.select_all_schemas !== undefined) {
      cleanedPattern.select_all_schemas = pattern.select_all_schemas
    }
    if (pattern.select_schema !== null && pattern.select_schema !== undefined) {
      cleanedPattern.select_schema = pattern.select_schema
    }
    if (pattern.tags && pattern.tags.length > 0) cleanedPattern.tags = pattern.tags
    if (pattern.tags_any && pattern.tags_any.length > 0) cleanedPattern.tags_any = pattern.tags_any
    if (pattern.dbt_ref) cleanedPattern.dbt_ref = pattern.dbt_ref
    if (pattern.dbt_selector) cleanedPattern.dbt_selector = pattern.dbt_selector
    if (pattern.dbt_project_path) cleanedPattern.dbt_project_path = pattern.dbt_project_path
    if (pattern.dbt_manifest_path) cleanedPattern.dbt_manifest_path = pattern.dbt_manifest_path
    if (pattern.exclude_patterns && pattern.exclude_patterns.length > 0) {
      cleanedPattern.exclude_patterns = pattern.exclude_patterns
    }
    if (pattern.table_types && pattern.table_types.length > 0) {
      cleanedPattern.table_types = pattern.table_types
    }
    if (pattern.min_rows !== null && pattern.min_rows !== undefined) {
      cleanedPattern.min_rows = pattern.min_rows
    }
    if (pattern.max_rows !== null && pattern.max_rows !== undefined) {
      cleanedPattern.max_rows = pattern.max_rows
    }
    if (pattern.required_columns && pattern.required_columns.length > 0) {
      cleanedPattern.required_columns = pattern.required_columns
    }
    if (pattern.modified_since_days !== null && pattern.modified_since_days !== undefined) {
      cleanedPattern.modified_since_days = pattern.modified_since_days
    }
    if (pattern.override_priority !== null && pattern.override_priority !== undefined) {
      cleanedPattern.override_priority = pattern.override_priority
    }
    // Note: partition, sampling, and columns are no longer supported in table patterns
    // These must be configured in ODCS contracts instead
    
    onSave(cleanedPattern)
  }

  const updatePattern = (updates: Partial<TablePattern>) => {
    setPattern((p) => ({ ...p, ...updates }))
  }

  const renderExplicitForm = () => (
    <div className="space-y-4">
      <FormField label="Database" helperText="Optional: Select a saved connection or leave empty to use source">
        <Select
          options={databaseOptions}
          value={pattern.database || ''}
          onChange={(value) => updatePattern({ database: value || null })}
        />
      </FormField>
      
      <FormField label="Schema" required>
        <Input
          value={pattern.schema || ''}
          onChange={(e) => updatePattern({ schema: e.target.value || null })}
          placeholder="public"
        />
      </FormField>
      
      <FormField label="Table Name" required>
        <Input
          value={pattern.table || ''}
          onChange={(e) => updatePattern({ table: e.target.value || null })}
          placeholder="users"
        />
      </FormField>
    </div>
  )

  const renderPatternForm = () => (
    <div className="space-y-4">
      <FormField label="Database" helperText="Optional: Select a saved connection or leave empty to use source">
        <Select
          options={databaseOptions}
          value={pattern.database || ''}
          onChange={(value) => updatePattern({ database: value || null })}
        />
      </FormField>
      
      <FormField label="Schema" helperText="Optional: Filter by specific schema">
        <Input
          value={pattern.schema || ''}
          onChange={(e) => updatePattern({ schema: e.target.value || null })}
          placeholder="public"
        />
      </FormField>
      
      <FormField label="Pattern" required>
        <Input
          value={pattern.pattern || ''}
          onChange={(e) => updatePattern({ pattern: e.target.value || null })}
          placeholder="user_*"
        />
      </FormField>
      
      <FormField label="Pattern Type" required>
        <Select
          options={PATTERN_TYPE_OPTIONS}
          value={pattern.pattern_type || 'wildcard'}
          onChange={(value) => updatePattern({ pattern_type: value as 'wildcard' | 'regex' || null })}
        />
      </FormField>
      
      <FormField label="Schema Pattern" helperText="Optional: Pattern for schema names">
        <Input
          value={pattern.schema_pattern || ''}
          onChange={(e) => updatePattern({ schema_pattern: e.target.value || null })}
          placeholder="public_*"
        />
      </FormField>
      
      <FormField label="Exclude Patterns" helperText="Comma-separated patterns to exclude">
        <Input
          value={formatArrayString(pattern.exclude_patterns)}
          onChange={(e) => updatePattern({ exclude_patterns: parseArrayString(e.target.value) })}
          placeholder="temp_*, test_*"
        />
      </FormField>
    </div>
  )

  const renderSchemaForm = () => (
    <div className="space-y-4">
      <FormField label="Database" helperText="Optional: Select a saved connection or leave empty to use source">
        <Select
          options={databaseOptions}
          value={pattern.database || ''}
          onChange={(value) => updatePattern({ database: value || null })}
        />
      </FormField>
      
      <FormField label="Schemas" required helperText="Comma-separated list of schemas">
        <Input
          value={formatArrayString(pattern.select_schema ? [pattern.schema || ''] : [])}
          onChange={(e) => {
            const schemas = parseArrayString(e.target.value)
            updatePattern({
              schema: schemas[0] || null,
              select_schema: schemas.length > 0,
            })
          }}
          placeholder="public, sales, marketing"
        />
      </FormField>
      
      <FormField label="Exclude Patterns" helperText="Comma-separated patterns to exclude">
        <Input
          value={formatArrayString(pattern.exclude_patterns)}
          onChange={(e) => updatePattern({ exclude_patterns: parseArrayString(e.target.value) })}
          placeholder="temp_*, test_*"
        />
      </FormField>
    </div>
  )

  const renderDatabaseForm = () => (
    <div className="space-y-4">
      <FormField label="Database" required>
        <Select
          options={databaseOptions}
          value={pattern.database || ''}
          onChange={(value) => updatePattern({ database: value || null })}
        />
      </FormField>
      
      <FormField label="Exclude Schemas" helperText="Comma-separated schemas to exclude">
        <Input
          value={formatArrayString(pattern.exclude_patterns)}
          onChange={(e) => updatePattern({ exclude_patterns: parseArrayString(e.target.value) })}
          placeholder="temp, test, staging"
        />
      </FormField>
    </div>
  )

  const renderTagForm = () => (
    <div className="space-y-4">
      <FormField label="Database" helperText="Optional: Select a saved connection or leave empty to use source">
        <Select
          options={databaseOptions}
          value={pattern.database || ''}
          onChange={(value) => updatePattern({ database: value || null })}
        />
      </FormField>
      
      <FormField label="Schema" helperText="Optional: Filter by specific schema">
        <Input
          value={pattern.schema || ''}
          onChange={(e) => updatePattern({ schema: e.target.value || null })}
          placeholder="public"
        />
      </FormField>
      
      <FormField label="Tags (AND)" helperText="Comma-separated tags - all must match">
        <Input
          value={formatArrayString(pattern.tags)}
          onChange={(e) => updatePattern({ tags: parseArrayString(e.target.value) })}
          placeholder="production, important"
        />
      </FormField>
      
      <FormField label="Tags (OR)" helperText="Comma-separated tags - any can match">
        <Input
          value={formatArrayString(pattern.tags_any)}
          onChange={(e) => updatePattern({ tags_any: parseArrayString(e.target.value) })}
          placeholder="staging, dev"
        />
      </FormField>
    </div>
  )

  const renderDbtForm = () => (
    <div className="space-y-4">
      <FormField label="dbt Ref" helperText="dbt ref() reference">
        <Input
          value={pattern.dbt_ref || ''}
          onChange={(e) => updatePattern({ dbt_ref: e.target.value || null })}
          placeholder="ref('my_model')"
        />
      </FormField>
      
      <FormField label="dbt Selector" helperText="dbt selector expression">
        <Input
          value={pattern.dbt_selector || ''}
          onChange={(e) => updatePattern({ dbt_selector: e.target.value || null })}
          placeholder="tag:production"
        />
      </FormField>
      
      <FormField label="dbt Project Path" helperText="Path to dbt project">
        <Input
          value={pattern.dbt_project_path || ''}
          onChange={(e) => updatePattern({ dbt_project_path: e.target.value || null })}
          placeholder="/path/to/dbt/project"
        />
      </FormField>
      
      <FormField label="dbt Manifest Path" helperText="Path to dbt manifest.json">
        <Input
          value={pattern.dbt_manifest_path || ''}
          onChange={(e) => updatePattern({ dbt_manifest_path: e.target.value || null })}
          placeholder="/path/to/manifest.json"
        />
      </FormField>
    </div>
  )

  const renderCommonFields = () => (
    <div className="space-y-4 border-t pt-4 mt-4">
      <h4 className="text-sm font-medium text-gray-900">Common Filters</h4>
      
      <FormField label="Table Types" helperText="Comma-separated: table, view, materialized_view">
        <Input
          value={formatArrayString(pattern.table_types)}
          onChange={(e) => updatePattern({ table_types: parseArrayString(e.target.value) })}
          placeholder="table, view"
        />
      </FormField>
      
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Min Rows">
          <Input
            type="number"
            value={pattern.min_rows ?? ''}
            onChange={(e) => updatePattern({ min_rows: e.target.value ? parseInt(e.target.value, 10) : null })}
            min={0}
          />
        </FormField>
        
        <FormField label="Max Rows">
          <Input
            type="number"
            value={pattern.max_rows ?? ''}
            onChange={(e) => updatePattern({ max_rows: e.target.value ? parseInt(e.target.value, 10) : null })}
            min={0}
          />
        </FormField>
      </div>
      
      <FormField label="Required Columns" helperText="Comma-separated column names">
        <Input
          value={formatArrayString(pattern.required_columns)}
          onChange={(e) => updatePattern({ required_columns: parseArrayString(e.target.value) })}
          placeholder="id, created_at"
        />
      </FormField>
      
      <FormField label="Modified Since (days)" helperText="Only include tables modified within this many days">
        <Input
          type="number"
          value={pattern.modified_since_days ?? ''}
          onChange={(e) => updatePattern({ modified_since_days: e.target.value ? parseInt(e.target.value, 10) : null })}
          min={0}
        />
      </FormField>
      
      <FormField label="Override Priority" helperText="Higher priority patterns are processed first">
        <Input
          type="number"
          value={pattern.override_priority ?? ''}
          onChange={(e) => updatePattern({ override_priority: e.target.value ? parseInt(e.target.value, 10) : null })}
        />
      </FormField>
    </div>
  )

  const renderMethodForm = () => {
    switch (selectionMethod) {
      case 'explicit':
        return renderExplicitForm()
      case 'pattern':
        return renderPatternForm()
      case 'schema':
        return renderSchemaForm()
      case 'database':
        return renderDatabaseForm()
      case 'tag':
        return renderTagForm()
      case 'dbt':
        return renderDbtForm()
      default:
        return null
    }
  }

  const canSave = () => {
    switch (selectionMethod) {
      case 'explicit':
        return !!(pattern.schema && pattern.table)
      case 'pattern':
        return !!pattern.pattern
      case 'schema':
        return !!(pattern.select_schema && pattern.schema)
      case 'database':
        return !!pattern.database
      case 'tag':
        return !!(pattern.tags && pattern.tags.length > 0) || !!(pattern.tags_any && pattern.tags_any.length > 0)
      case 'dbt':
        return !!(pattern.dbt_ref || pattern.dbt_selector)
      default:
        return false
    }
  }

  return (
    <Modal
      isOpen={true}
      onClose={onCancel}
      title={initialPattern ? 'Edit Table Pattern' : 'Add Table Pattern'}
      size="xl"
      footer={
        <div className="flex justify-between items-center">
          <Button
            variant="outline"
            onClick={handlePreview}
            disabled={!canSave() || isPreviewing}
            icon={<Eye className="w-4 h-4" />}
          >
            {isPreviewing ? 'Previewing...' : 'Preview'}
          </Button>
          <div className="flex gap-2">
            <Button variant="outline" onClick={onCancel}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={!canSave()}>
              Save Pattern
            </Button>
          </div>
        </div>
      }
    >
      <div className="space-y-6">
        <Tabs
          tabs={SELECTION_METHODS.map(m => ({ id: m.id, label: m.label }))}
          activeTab={selectionMethod}
          onChange={(tabId) => setSelectionMethod(tabId as SelectionMethod)}
        />
        
        <div>
          {renderMethodForm()}
          {renderCommonFields()}
        </div>
        
        {showPreview && (
          <div className="mt-6">
            <TablePreview
              tables={previewTables}
              isLoading={isPreviewing}
              error={previewError}
              onRefresh={handlePreview}
            />
          </div>
        )}
      </div>
    </Modal>
  )
}

