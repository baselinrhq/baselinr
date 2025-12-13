'use client'

import { useState } from 'react'
import { Card } from '@/components/ui/Card'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { Select, SelectOption } from '@/components/ui/Select'
import { Toggle } from '@/components/ui/Toggle'
import { DiscoveryOptionsConfig } from '@/types/config'

export interface TableDiscoveryProps {
  discoveryOptions: DiscoveryOptionsConfig
  onChange: (options: DiscoveryOptionsConfig) => void
  errors?: Record<string, string>
  isLoading?: boolean
}

const TAG_PROVIDER_OPTIONS: SelectOption[] = [
  { value: 'auto', label: 'Auto' },
  { value: 'snowflake', label: 'Snowflake' },
  { value: 'bigquery', label: 'BigQuery' },
  { value: 'postgres', label: 'PostgreSQL' },
  { value: 'mysql', label: 'MySQL' },
  { value: 'redshift', label: 'Redshift' },
  { value: 'sqlite', label: 'SQLite' },
  { value: 'dbt', label: 'dbt' },
]

const DISCOVERY_LIMIT_ACTION_OPTIONS: SelectOption[] = [
  { value: 'warn', label: 'Warn' },
  { value: 'error', label: 'Error' },
  { value: 'skip', label: 'Skip' },
]

/**
 * Helper to parse comma-separated string into array
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
 * Helper to format array as comma-separated string
 */
function formatArrayString(value: string[] | null | undefined): string {
  if (!value || value.length === 0) return ''
  return value.join(', ')
}

export function TableDiscovery({
  discoveryOptions,
  onChange,
  errors = {},
  isLoading = false,
}: TableDiscoveryProps) {
  const [includeSchemasText, setIncludeSchemasText] = useState(
    formatArrayString(discoveryOptions.include_schemas)
  )
  const [excludeSchemasText, setExcludeSchemasText] = useState(
    formatArrayString(discoveryOptions.exclude_schemas)
  )
  const [includeTableTypesText, setIncludeTableTypesText] = useState(
    formatArrayString(discoveryOptions.include_table_types)
  )
  const [excludeTableTypesText, setExcludeTableTypesText] = useState(
    formatArrayString(discoveryOptions.exclude_table_types)
  )

  const handleChange = (path: (string | number)[], value: unknown) => {
    const newOptions = { ...discoveryOptions }
    let current: Record<string, unknown> = newOptions
    
    for (let i = 0; i < path.length - 1; i++) {
      const key = path[i] as string
      if (current[key] === undefined || current[key] === null) {
        current[key] = {}
      }
      current = current[key] as Record<string, unknown>
    }
    
    const lastKey = path[path.length - 1] as string
    if (value === '' || value === null || value === undefined) {
      delete current[lastKey]
    } else {
      current[lastKey] = value
    }
    
    onChange(newOptions)
  }

  const handleArrayChange = (
    field: keyof DiscoveryOptionsConfig,
    textValue: string
  ) => {
    const arrayValue = parseArrayString(textValue)
    handleChange([field], arrayValue.length > 0 ? arrayValue : null)
  }

  return (
    <Card>
      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-semibold text-white mb-4">
            Discovery Settings
          </h3>
          <p className="text-sm text-slate-400 mb-6">
            Configure how tables are discovered and filtered during profiling.
          </p>
        </div>

        {/* Schema Filters */}
        <div className="space-y-4">
          <h4 className="text-sm font-medium text-slate-300">Schema Filters</h4>
          
          <FormField
            label="Include Schemas"
            helperText="Comma-separated list of schemas to include (leave empty for all)"
            error={errors.include_schemas}
          >
            <Input
              value={includeSchemasText}
              onChange={(e) => {
                setIncludeSchemasText(e.target.value)
                handleArrayChange('include_schemas', e.target.value)
              }}
              placeholder="public, sales, marketing"
              disabled={isLoading}
            />
          </FormField>

          <FormField
            label="Exclude Schemas"
            helperText="Comma-separated list of schemas to exclude"
            error={errors.exclude_schemas}
          >
            <Input
              value={excludeSchemasText}
              onChange={(e) => {
                setExcludeSchemasText(e.target.value)
                handleArrayChange('exclude_schemas', e.target.value)
              }}
              placeholder="temp, test, staging"
              disabled={isLoading}
            />
          </FormField>
        </div>

        {/* Table Type Filters */}
        <div className="space-y-4">
          <h4 className="text-sm font-medium text-slate-300">Table Type Filters</h4>
          
          <FormField
            label="Include Table Types"
            helperText="Comma-separated list: table, view, materialized_view"
            error={errors.include_table_types}
          >
            <Input
              value={includeTableTypesText}
              onChange={(e) => {
                setIncludeTableTypesText(e.target.value)
                handleArrayChange('include_table_types', e.target.value)
              }}
              placeholder="table, view"
              disabled={isLoading}
            />
          </FormField>

          <FormField
            label="Exclude Table Types"
            helperText="Comma-separated list: table, view, materialized_view"
            error={errors.exclude_table_types}
          >
            <Input
              value={excludeTableTypesText}
              onChange={(e) => {
                setExcludeTableTypesText(e.target.value)
                handleArrayChange('exclude_table_types', e.target.value)
              }}
              placeholder="view"
              disabled={isLoading}
            />
          </FormField>
        </div>

        {/* Caching */}
        <div className="space-y-4">
          <h4 className="text-sm font-medium text-slate-300">Caching</h4>
          
          <FormField
            label="Cache Discovery"
            helperText="Cache table discovery results to improve performance"
          >
            <Toggle
              checked={discoveryOptions.cache_discovery ?? true}
              onChange={(checked) => handleChange(['cache_discovery'], checked)}
              disabled={isLoading}
            />
          </FormField>

          <FormField
            label="Cache TTL (seconds)"
            helperText="Time to live for cached discovery results"
            error={errors.cache_ttl_seconds}
          >
            <Input
              type="number"
              value={discoveryOptions.cache_ttl_seconds ?? 300}
              onChange={(e) =>
                handleChange(
                  ['cache_ttl_seconds'],
                  e.target.value ? parseInt(e.target.value, 10) : null
                )
              }
              min={0}
              disabled={isLoading}
            />
          </FormField>
        </div>

        {/* Performance Limits */}
        <div className="space-y-4">
          <h4 className="text-sm font-medium text-slate-300">Performance Limits</h4>
          
          <FormField
            label="Max Tables Per Pattern"
            helperText="Maximum number of tables to process per pattern"
            error={errors.max_tables_per_pattern}
          >
            <Input
              type="number"
              value={discoveryOptions.max_tables_per_pattern ?? 1000}
              onChange={(e) =>
                handleChange(
                  ['max_tables_per_pattern'],
                  e.target.value ? parseInt(e.target.value, 10) : null
                )
              }
              min={1}
              disabled={isLoading}
            />
          </FormField>

          <FormField
            label="Max Schemas Per Database"
            helperText="Maximum number of schemas to process per database"
            error={errors.max_schemas_per_database}
          >
            <Input
              type="number"
              value={discoveryOptions.max_schemas_per_database ?? 100}
              onChange={(e) =>
                handleChange(
                  ['max_schemas_per_database'],
                  e.target.value ? parseInt(e.target.value, 10) : null
                )
              }
              min={1}
              disabled={isLoading}
            />
          </FormField>

          <FormField
            label="Discovery Limit Action"
            helperText="Action to take when limits are exceeded"
            error={errors.discovery_limit_action}
          >
            <Select
              options={DISCOVERY_LIMIT_ACTION_OPTIONS}
              value={discoveryOptions.discovery_limit_action ?? 'warn'}
              onChange={(value) =>
                handleChange(['discovery_limit_action'], value as 'warn' | 'error' | 'skip')
              }
              disabled={isLoading}
            />
          </FormField>
        </div>

        {/* Validation */}
        <div className="space-y-4">
          <h4 className="text-sm font-medium text-slate-300">Validation</h4>
          
          <FormField
            label="Validate Regex"
            helperText="Validate regex patterns before using them"
          >
            <Toggle
              checked={discoveryOptions.validate_regex ?? true}
              onChange={(checked) => handleChange(['validate_regex'], checked)}
              disabled={isLoading}
            />
          </FormField>
        </div>

        {/* Tag Provider */}
        <div className="space-y-4">
          <h4 className="text-sm font-medium text-slate-300">Tag Provider</h4>
          
          <FormField
            label="Tag Provider"
            helperText="Provider for table tags (auto-detect if not specified)"
            error={errors.tag_provider}
          >
            <Select
              options={TAG_PROVIDER_OPTIONS}
              value={discoveryOptions.tag_provider ?? 'auto'}
              onChange={(value) => handleChange(['tag_provider'], value || null)}
              clearable
              disabled={isLoading}
            />
          </FormField>

          {discoveryOptions.tag_provider === 'dbt' && (
            <FormField
              label="dbt Manifest Path"
              helperText="Path to dbt manifest.json file"
              error={errors.dbt_manifest_path}
            >
              <Input
                value={discoveryOptions.dbt_manifest_path ?? ''}
                onChange={(e) =>
                  handleChange(['dbt_manifest_path'], e.target.value || null)
                }
                placeholder="/path/to/manifest.json"
                disabled={isLoading}
              />
            </FormField>
          )}
        </div>
      </div>
    </Card>
  )
}

