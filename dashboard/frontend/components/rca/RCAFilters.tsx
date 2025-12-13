'use client'

import { useState } from 'react'
import { X, Filter, ChevronDown, ChevronUp } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { SearchInput } from '@/components/ui/SearchInput'
import type { RCAFilters as RCAFiltersType } from '@/types/rca'

interface RCAFiltersProps {
  filters: RCAFiltersType
  onChange: (filters: RCAFiltersType) => void
  onPreset?: (preset: string) => void
  tables?: string[]
  schemas?: string[]
}

const statusOptions = [
  { value: 'analyzed', label: 'Analyzed' },
  { value: 'pending', label: 'Pending' },
  { value: 'dismissed', label: 'Dismissed' },
]

const timePresets = [
  { value: '7', label: 'Last 7 days' },
  { value: '30', label: 'Last 30 days' },
  { value: '90', label: 'Last 90 days' },
  { value: '365', label: 'Last year' },
]

const filterPresets = [
  {
    name: 'Last 7 days - Analyzed',
    filters: { days: 7, status: 'analyzed' as const },
  },
  {
    name: 'Last 30 days - All',
    filters: { days: 30 },
  },
  {
    name: 'Pending analyses',
    filters: { status: 'pending' as const },
  },
]

export default function RCAFilters({
  filters,
  onChange,
  onPreset,
  tables = [],
  schemas = [],
}: RCAFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const handleChange = (key: keyof RCAFiltersType, value: string | number | undefined) => {
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
    (key) => filters[key as keyof RCAFiltersType] !== undefined && filters[key as keyof RCAFiltersType] !== ''
  ).length

  const schemaOptions = [
    { value: '', label: 'All Schemas' },
    ...schemas.map((s) => ({ value: s, label: s })),
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

      {/* Quick Presets */}
      {isExpanded && (
        <div className="p-4 border-b border-surface-700/50 bg-surface-900/30">
          <p className="text-sm font-medium text-slate-300 mb-3">Quick Presets</p>
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

      {/* Filter Controls */}
      <div className={`p-4 ${isExpanded ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4' : 'flex flex-wrap gap-4'}`}>
        {/* Status Filter */}
        <div className="flex-1 min-w-[200px]">
          <Select
            label="Status"
            options={[
              { value: '', label: 'All Statuses' },
              ...statusOptions,
            ]}
            value={filters.status || ''}
            onChange={(value) => handleChange('status', value as 'analyzed' | 'pending' | 'dismissed' | undefined)}
            placeholder="All Statuses"
            clearable
          />
        </div>

        {/* Schema Filter */}
        <div className="flex-1 min-w-[200px]">
          <Select
            label="Schema"
            options={schemaOptions}
            value={filters.schema || ''}
            onChange={(value) => handleChange('schema', value)}
            placeholder="All Schemas"
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
            suggestions={tables
              .filter((t) =>
                t.toLowerCase().includes((filters.table || '').toLowerCase())
              )
              .slice(0, 5)
              .map((t) => ({ value: t, label: t }))}
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
          </>
        )}
      </div>

      {/* Active Filters Display */}
      {activeFilterCount > 0 && (
        <div className="p-4 border-t border-surface-700/50 bg-surface-900/30">
          <div className="flex flex-wrap gap-2">
            {Object.entries(filters).map(([key, value]) => {
              if (!value || value === '') return null
              
              let displayValue = value
              if (key === 'days') {
                displayValue = `Last ${value} days`
              } else if (key === 'status') {
                displayValue = String(value).charAt(0).toUpperCase() + String(value).slice(1)
              }
              
              return (
                <span
                  key={key}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium bg-surface-700/50 border border-surface-600/50 rounded-lg text-slate-300"
                >
                  <span className="text-slate-500">{key}:</span>
                  {displayValue}
                  <button
                    onClick={() => handleChange(key as keyof RCAFiltersType, undefined)}
                    className="ml-1 text-slate-500 hover:text-slate-300 transition-colors"
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
