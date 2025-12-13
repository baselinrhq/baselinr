'use client'

import { useState } from 'react'
import { Filter, ChevronDown, ChevronUp } from 'lucide-react'
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
    <div className="glass-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-surface-700/50">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-surface-700/50">
            <Filter className="w-4 h-4 text-slate-400" />
          </div>
          <h3 className="text-base font-semibold text-white">Filters</h3>
          {activeFilterCount > 0 && (
            <span className="px-2 py-0.5 text-xs font-medium bg-accent-500/20 text-accent-400 rounded-full">
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
            onClick={() => setIsExpanded(!isExpanded)}
            icon={isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            iconPosition="right"
          >
            {isExpanded ? 'Collapse' : 'Expand'}
          </Button>
        </div>
      </div>

      {/* Filter Content */}
      {isExpanded && (
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Warehouse Filter */}
            <Select
              label="Warehouse"
              value={filters.warehouse || ''}
              onChange={(value) => handleChange('warehouse', value)}
              options={warehouseOptions}
            />

            {/* Table Search */}
            <SearchInput
              label="Table"
              value={filters.table || ''}
              onChange={(value) => handleChange('table', value)}
              placeholder="Search tables..."
              suggestions={tables}
            />

            {/* Schema Filter */}
            <Input
              label="Schema"
              type="text"
              value={filters.schema || ''}
              onChange={(e) => handleChange('schema', e.target.value)}
              placeholder="Schema name"
            />

            {/* Rule Type Filter */}
            <Select
              label="Rule Type"
              value={filters.rule_type || ''}
              onChange={(value) => handleChange('rule_type', value)}
              options={ruleTypeOptions}
            />

            {/* Severity Filter */}
            <Select
              label="Severity"
              value={filters.severity || ''}
              onChange={(value) => handleChange('severity', value)}
              options={severityOptions}
            />

            {/* Status Filter */}
            <Select
              label="Status"
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

            {/* Days Filter */}
            <Select
              label="Time Range"
              value={filters.days?.toString() || '30'}
              onChange={(value) => handleChange('days', value ? parseInt(value) : undefined)}
              options={timePresets}
            />
          </div>

          {/* Filter Presets */}
          {filterPresets.length > 0 && (
            <div className="pt-4 border-t border-surface-700/50">
              <p className="text-sm font-medium text-slate-300 mb-3">Quick Filters</p>
              <div className="flex flex-wrap gap-2">
                {filterPresets.map((preset) => (
                  <Button
                    key={preset.name}
                    variant="outline"
                    size="sm"
                    onClick={() => handlePreset(preset)}
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
