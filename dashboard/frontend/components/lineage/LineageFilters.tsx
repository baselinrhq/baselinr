'use client'

import { useState } from 'react'
import { Filter } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Select'
import { Input } from '@/components/ui/Input'
import type { LineageFilters as LineageFiltersType } from '@/types/lineage'

interface LineageFiltersProps {
  filters: LineageFiltersType
  onChange: (filters: LineageFiltersType) => void
  onPreset?: (preset: string) => void
  availableProviders?: string[]
  availableSchemas?: string[]
  availableDatabases?: string[]
}

const providerOptions = [
  { value: '', label: 'All Providers' },
  { value: 'dbt_manifest', label: 'dbt Manifest' },
  { value: 'sql_parser', label: 'SQL Parser' },
  { value: 'query_history', label: 'Query History' },
  { value: 'dagster', label: 'Dagster' },
]

const nodeTypeOptions = [
  { value: 'both', label: 'Both' },
  { value: 'table', label: 'Tables Only' },
  { value: 'column', label: 'Columns Only' },
]

const severityOptions = [
  { value: '', label: 'All Severities' },
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
]

const filterPresets: Array<{ id: string; label: string; filters: Partial<LineageFiltersType> }> = [
  { id: 'high-confidence', label: 'High Confidence Only', filters: { confidence_min: 0.8 } },
  { id: 'drift-affected', label: 'Drift Affected', filters: { has_drift: true } },
  { id: 'dbt-only', label: 'dbt Only', filters: { providers: ['dbt_manifest'] } },
  { id: 'tables-only', label: 'Tables Only', filters: { node_type: 'table' as const } },
]

export default function LineageFilters({
  filters,
  onChange,
  onPreset,
  availableSchemas = [],
  availableDatabases = [],
}: LineageFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const toggleExpanded = () => {
    setIsExpanded(prev => !prev)
  }

  const handleFilterChange = (key: keyof LineageFiltersType, value: string | number | string[] | boolean | undefined) => {
    onChange({
      ...filters,
      [key]: value,
    })
  }

  const handleClear = () => {
    onChange({})
  }

  const handlePreset = (preset: typeof filterPresets[0]) => {
    onChange({
      ...filters,
      ...preset.filters,
    } as LineageFiltersType)
    if (onPreset) {
      onPreset(preset.id)
    }
  }

  const activeFilterCount = Object.keys(filters).filter(
    (key) => filters[key as keyof LineageFiltersType] !== undefined && filters[key as keyof LineageFiltersType] !== null
  ).length

  return (
    <div className="glass-card overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b border-surface-700/50">
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-slate-400" />
          <h3 className="text-base font-semibold text-white">Filters</h3>
          {activeFilterCount > 0 && (
            <span className="px-2 py-0.5 text-xs font-medium bg-cyan-500/20 text-cyan-400 rounded-full">
              {activeFilterCount} active
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {activeFilterCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClear}
            >
              Clear all
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            type="button"
            onClick={toggleExpanded}
          >
            {isExpanded ? 'Collapse' : 'Expand'}
          </Button>
        </div>
      </div>

      {isExpanded && (
        <div className="p-4 space-y-4">
          {/* Filter Presets */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Quick Filters
            </label>
            <div className="flex flex-wrap gap-2">
              {filterPresets.map((preset) => (
                <Button
                  key={preset.id}
                  variant="outline"
                  size="sm"
                  onClick={() => handlePreset(preset)}
                >
                  {preset.label}
                </Button>
              ))}
            </div>
          </div>

          {/* Provider Filter */}
          <Select
            label="Provider"
            value={filters.providers?.[0] || ''}
            onChange={(value) => handleFilterChange('providers', value ? [value] : undefined)}
            options={providerOptions}
          />

          {/* Confidence Range */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Confidence Range
            </label>
            <div className="grid grid-cols-2 gap-2">
              <Input
                type="number"
                min="0"
                max="1"
                step="0.1"
                placeholder="Min"
                value={filters.confidence_min?.toString() || ''}
                onChange={(e) => handleFilterChange('confidence_min', e.target.value ? parseFloat(e.target.value) : undefined)}
              />
              <Input
                type="number"
                min="0"
                max="1"
                step="0.1"
                placeholder="Max"
                value={filters.confidence_max?.toString() || ''}
                onChange={(e) => handleFilterChange('confidence_max', e.target.value ? parseFloat(e.target.value) : undefined)}
              />
            </div>
          </div>

          {/* Node Type Filter */}
          <Select
            label="Node Type"
            value={filters.node_type || 'both'}
            onChange={(value) => handleFilterChange('node_type', value as 'table' | 'column' | 'both')}
            options={nodeTypeOptions}
          />

          {/* Schema Filter */}
          {availableSchemas.length > 0 && (
            <Select
              label="Schema"
              value={filters.schemas?.[0] || ''}
              onChange={(value) => handleFilterChange('schemas', value ? [value] : undefined)}
              options={[
                { value: '', label: 'All Schemas' },
                ...availableSchemas.map(s => ({ value: s, label: s })),
              ]}
            />
          )}

          {/* Database Filter */}
          {availableDatabases.length > 0 && (
            <Select
              label="Database"
              value={filters.databases?.[0] || ''}
              onChange={(value) => handleFilterChange('databases', value ? [value] : undefined)}
              options={[
                { value: '', label: 'All Databases' },
                ...availableDatabases.map(d => ({ value: d, label: d })),
              ]}
            />
          )}

          {/* Drift Filter */}
          <Select
            label="Drift Status"
            value={filters.has_drift === true ? 'true' : filters.has_drift === false ? 'false' : ''}
            onChange={(value) => handleFilterChange('has_drift', value === 'true' ? true : value === 'false' ? false : undefined)}
            options={[
              { value: '', label: 'All' },
              { value: 'true', label: 'With Drift' },
              { value: 'false', label: 'No Drift' },
            ]}
          />

          {/* Drift Severity Filter */}
          {filters.has_drift && (
            <Select
              label="Drift Severity"
              value={filters.drift_severity || ''}
              onChange={(value) => handleFilterChange('drift_severity', value || undefined)}
              options={severityOptions}
            />
          )}
        </div>
      )}
    </div>
  )
}

