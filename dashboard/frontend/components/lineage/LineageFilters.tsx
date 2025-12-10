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

const filterPresets = [
  { id: 'high-confidence', label: 'High Confidence Only', filters: { confidence_min: 0.8 } },
  { id: 'drift-affected', label: 'Drift Affected', filters: { has_drift: true } },
  { id: 'dbt-only', label: 'dbt Only', filters: { providers: ['dbt_manifest'] } },
  { id: 'tables-only', label: 'Tables Only', filters: { node_type: 'table' } },
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
    })
    if (onPreset) {
      onPreset(preset.id)
    }
  }

  const activeFilterCount = Object.keys(filters).filter(
    (key) => filters[key as keyof LineageFiltersType] !== undefined && filters[key as keyof LineageFiltersType] !== null
  ).length

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200">
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-gray-500" />
          <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
          {activeFilterCount > 0 && (
            <span className="px-2 py-0.5 text-xs font-medium bg-primary-100 text-primary-800 rounded-full">
              {activeFilterCount} active
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {activeFilterCount > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleClear}
            >
              Clear all
            </Button>
          )}
          <Button
            variant="outline"
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
            <label className="block text-sm font-medium text-gray-700 mb-2">
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
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Provider
            </label>
            <Select
              value={filters.providers?.[0] || ''}
              onChange={(value) => handleFilterChange('providers', value ? [value] : undefined)}
              options={providerOptions}
            />
          </div>

          {/* Confidence Range */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
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
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Node Type
            </label>
            <Select
              value={filters.node_type || 'both'}
              onChange={(value) => handleFilterChange('node_type', value as 'table' | 'column' | 'both')}
              options={nodeTypeOptions}
            />
          </div>

          {/* Schema Filter */}
          {availableSchemas.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Schema
              </label>
              <Select
                value={filters.schemas?.[0] || ''}
                onChange={(value) => handleFilterChange('schemas', value ? [value] : undefined)}
                options={[
                  { value: '', label: 'All Schemas' },
                  ...availableSchemas.map(s => ({ value: s, label: s })),
                ]}
              />
            </div>
          )}

          {/* Database Filter */}
          {availableDatabases.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Database
              </label>
              <Select
                value={filters.databases?.[0] || ''}
                onChange={(value) => handleFilterChange('databases', value ? [value] : undefined)}
                options={[
                  { value: '', label: 'All Databases' },
                  ...availableDatabases.map(d => ({ value: d, label: d })),
                ]}
              />
            </div>
          )}

          {/* Drift Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Drift Status
            </label>
            <Select
              value={filters.has_drift === true ? 'true' : filters.has_drift === false ? 'false' : ''}
              onChange={(value) => handleFilterChange('has_drift', value === 'true' ? true : value === 'false' ? false : undefined)}
              options={[
                { value: '', label: 'All' },
                { value: 'true', label: 'With Drift' },
                { value: 'false', label: 'No Drift' },
              ]}
            />
          </div>

          {/* Drift Severity Filter */}
          {filters.has_drift && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Drift Severity
              </label>
              <Select
                value={filters.drift_severity || ''}
                onChange={(value) => handleFilterChange('drift_severity', value || undefined)}
                options={severityOptions}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

