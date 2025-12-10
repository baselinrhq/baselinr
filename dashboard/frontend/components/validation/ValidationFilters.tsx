'use client'

import { useState } from 'react'
import { Filter } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { SearchInput } from '@/components/ui/SearchInput'
import type { ValidationFilters as ValidationFiltersType } from '@/types/validation'

interface ValidationFiltersProps {
  filters: ValidationFiltersType
  onChange: (filters: ValidationFiltersType) => void
  onPreset?: (preset: string) => void
  warehouses?: string[]
  tables?: string[]
}

const ruleTypeOptions = [
  { value: '', label: 'All Rule Types' },
  { value: 'format', label: 'Format' },
  { value: 'range', label: 'Range' },
  { value: 'enum', label: 'Enum' },
  { value: 'not_null', label: 'Not Null' },
  { value: 'unique', label: 'Unique' },
  { value: 'referential', label: 'Referential' },
]

const severityOptions = [
  { value: '', label: 'All Severities' },
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
]

const statusOptions = [
  { value: '', label: 'All Status' },
  { value: 'passed', label: 'Passed' },
  { value: 'failed', label: 'Failed' },
]

const timePresets = [
  { value: '7', label: 'Last 7 days' },
  { value: '30', label: 'Last 30 days' },
  { value: '90', label: 'Last 90 days' },
  { value: '365', label: 'Last year' },
]

const filterPresets = [
  {
    name: 'Last 7 days - Failures only',
    filters: { days: 7, passed: false },
  },
  {
    name: 'Last 30 days - High severity',
    filters: { days: 30, severity: 'high' },
  },
  {
    name: 'Recent failures',
    filters: { days: 7, passed: false },
  },
]

export default function ValidationFilters({
  filters,
  onChange,
  onPreset,
  warehouses = [],
  tables = [],
}: ValidationFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const handleChange = (key: keyof ValidationFiltersType, value: string | number | boolean | undefined) => {
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
    (key) => filters[key as keyof ValidationFiltersType] !== undefined && filters[key as keyof ValidationFiltersType] !== ''
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

      {/* Filter Content */}
      {isExpanded && (
        <div className="p-4 flex flex-wrap gap-4">
          {/* Warehouse Filter */}
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Warehouse
            </label>
            <Select
              value={filters.warehouse || ''}
              onChange={(value) => handleChange('warehouse', value)}
              options={warehouseOptions}
            />
          </div>

          {/* Table Search */}
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Table
            </label>
            <SearchInput
              value={filters.table || ''}
              onChange={(value) => handleChange('table', value)}
              placeholder="Search tables..."
              suggestions={tables}
            />
          </div>

          {/* Schema Filter */}
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Schema
            </label>
            <Input
              type="text"
              value={filters.schema || ''}
              onChange={(e) => handleChange('schema', e.target.value)}
              placeholder="Schema name"
            />
          </div>

          {/* Rule Type Filter */}
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Rule Type
            </label>
            <Select
              value={filters.rule_type || ''}
              onChange={(value) => handleChange('rule_type', value)}
              options={ruleTypeOptions}
            />
          </div>

          {/* Severity Filter */}
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Severity
            </label>
            <Select
              value={filters.severity || ''}
              onChange={(value) => handleChange('severity', value)}
              options={severityOptions}
            />
          </div>

          {/* Status Filter */}
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Status
            </label>
            <Select
              value={filters.passed === true ? 'passed' : filters.passed === false ? 'failed' : ''}
              onChange={(value) => {
                if (value === 'passed') {
                  handleChange('passed', true)
                } else if (value === 'failed') {
                  handleChange('passed', false)
                } else {
                  handleChange('passed', undefined)
                }
              }}
              options={statusOptions}
            />
          </div>

          {/* Days Filter */}
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Time Range
            </label>
            <Select
              value={filters.days?.toString() || '30'}
              onChange={(value) => handleChange('days', value ? parseInt(value) : undefined)}
              options={timePresets}
            />
          </div>

          {/* Filter Presets */}
          {filterPresets.length > 0 && (
            <div className="w-full">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Quick Filters
              </label>
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
        </div>
      )}
    </div>
  )
}

