'use client'

import { useState } from 'react'
import { X, Filter } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { SearchInput } from '@/components/ui/SearchInput'
import type { DriftFilters as DriftFiltersType } from '@/types/drift'

interface DriftFiltersProps {
  filters: DriftFiltersType
  onChange: (filters: DriftFiltersType) => void
  onPreset?: (preset: string) => void
  warehouses?: string[]
  tables?: string[]
}

const severityOptions = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
]

const timePresets = [
  { value: '7', label: 'Last 7 days' },
  { value: '30', label: 'Last 30 days' },
  { value: '90', label: 'Last 90 days' },
  { value: '365', label: 'Last year' },
]

const filterPresets = [
  {
    name: 'Last 7 days - High severity',
    filters: { days: 7, severity: 'high' },
  },
  {
    name: 'Last 30 days - All',
    filters: { days: 30 },
  },
  {
    name: 'Recent activity',
    filters: { days: 7 },
  },
]

export default function DriftFilters({
  filters,
  onChange,
  onPreset,
  warehouses = [],
  tables = [],
}: DriftFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const handleChange = (key: keyof DriftFiltersType, value: string | number | string[] | undefined) => {
    onChange({ ...filters, [key]: value })
  }

  const handleClear = () => {
    onChange({})
  }

  const handlePreset = (preset: typeof filterPresets[0]) => {
    onChange(preset.filters)
    if (onPreset) {
      onPreset(preset.name)
    }
  }

  const activeFilterCount = Object.keys(filters).filter(
    (key) => filters[key as keyof DriftFiltersType] !== undefined && filters[key as keyof DriftFiltersType] !== ''
  ).length

  const warehouseOptions = [
    { value: '', label: 'All Warehouses' },
    ...warehouses.map((w) => ({ value: w, label: w })),
  ]

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200">
      {/* Header */}
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
              variant="ghost"
              size="sm"
              onClick={handleClear}
              className="text-sm"
            >
              Clear all
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-sm"
          >
            {isExpanded ? 'Collapse' : 'Expand'}
          </Button>
        </div>
      </div>

      {/* Quick Presets */}
      {isExpanded && (
        <div className="p-4 border-b border-gray-200 bg-gray-50">
          <p className="text-sm font-medium text-gray-700 mb-2">Quick Presets</p>
          <div className="flex flex-wrap gap-2">
            {filterPresets.map((preset) => (
              <Button
                key={preset.name}
                variant="outline"
                size="sm"
                onClick={() => handlePreset(preset)}
                className="text-xs"
              >
                {preset.name}
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* Filter Controls */}
      <div className={`p-4 ${isExpanded ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4' : 'flex flex-wrap gap-4'}`}>
        {/* Warehouse Filter */}
        <div className="flex-1 min-w-[200px]">
          <Select
            label="Warehouse"
            options={warehouseOptions}
            value={filters.warehouse || ''}
            onChange={(value) => handleChange('warehouse', value)}
            placeholder="All Warehouses"
            clearable
          />
        </div>

        {/* Table Search */}
        <div className="flex-1 min-w-[200px]">
          <SearchInput
            label="Table"
            value={filters.table || ''}
            onChange={(value) => handleChange('table', value)}
            placeholder="Search table name..."
            suggestions={tables.filter((t) =>
              t.toLowerCase().includes((filters.table || '').toLowerCase())
            ).slice(0, 5)}
            onSuggestionSelect={(value) => handleChange('table', value)}
          />
        </div>

        {/* Severity Filter */}
        <div className="flex-1 min-w-[200px]">
          <Select
            label="Severity"
            options={[
              { value: '', label: 'All Severities' },
              ...severityOptions,
            ]}
            value={Array.isArray(filters.severity) ? filters.severity[0] : (filters.severity || '')}
            onChange={(value) => handleChange('severity', value)}
            placeholder="All Severities"
            clearable
          />
        </div>

        {/* Time Range */}
        <div className="flex-1 min-w-[200px]">
          <Select
            label="Time Range"
            options={timePresets}
            value={filters.days?.toString() || '30'}
            onChange={(value) => handleChange('days', parseInt(value) || 30)}
          />
        </div>

        {/* Expanded Filters */}
        {isExpanded && (
          <>
            {/* Date Range */}
            <div className="flex-1 min-w-[200px]">
              <Input
                label="Start Date"
                type="date"
                value={filters.start_date || ''}
                onChange={(e) => handleChange('start_date', e.target.value)}
              />
            </div>

            <div className="flex-1 min-w-[200px]">
              <Input
                label="End Date"
                type="date"
                value={filters.end_date || ''}
                onChange={(e) => handleChange('end_date', e.target.value)}
              />
            </div>

            {/* Metric Name */}
            <div className="flex-1 min-w-[200px]">
              <Input
                label="Metric Name"
                value={filters.metric_name || ''}
                onChange={(e) => handleChange('metric_name', e.target.value)}
                placeholder="e.g., row_count, null_percent"
              />
            </div>

            {/* Column Name */}
            <div className="flex-1 min-w-[200px]">
              <Input
                label="Column Name"
                value={filters.column_name || ''}
                onChange={(e) => handleChange('column_name', e.target.value)}
                placeholder="Filter by column"
              />
            </div>
          </>
        )}
      </div>

      {/* Active Filters Display */}
      {activeFilterCount > 0 && (
        <div className="p-4 border-t border-gray-200 bg-gray-50">
          <div className="flex flex-wrap gap-2">
            {Object.entries(filters).map(([key, value]) => {
              if (!value || value === '') return null
              
              let displayValue = value
              if (key === 'days') {
                displayValue = `Last ${value} days`
              } else if (key === 'severity') {
                displayValue = String(value).charAt(0).toUpperCase() + String(value).slice(1)
              }
              
              return (
                <span
                  key={key}
                  className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-white border border-gray-300 rounded-md text-gray-700"
                >
                  <span className="text-gray-500">{key}:</span>
                  {displayValue}
                  <button
                    onClick={() => handleChange(key as keyof DriftFiltersType, undefined)}
                    className="ml-1 text-gray-400 hover:text-gray-600"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

