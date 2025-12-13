'use client'

import { useState } from 'react'
import { ChevronDown, X } from 'lucide-react'
import { Button } from '@/components/ui'
import { Input } from '@/components/ui'
import Checkbox from '@/components/ui/Checkbox'
import { TableListOptions } from '@/lib/api'

interface TableFiltersProps {
  filters: TableListOptions
  onChange: (filters: TableListOptions) => void
  availableWarehouses?: string[]
  availableSchemas?: string[]
}

export default function TableFilters({
  filters,
  onChange,
  availableWarehouses = ['postgres', 'snowflake', 'mysql', 'bigquery', 'redshift', 'sqlite'],
  availableSchemas = []
}: TableFiltersProps) {
  const [isOpen, setIsOpen] = useState(false)

  const handleChange = (key: keyof TableListOptions, value: string | boolean | number | undefined) => {
    onChange({ ...filters, [key]: value })
  }

  const clearFilters = () => {
    onChange({
      warehouse: undefined,
      schema: undefined,
      search: undefined,
      has_drift: undefined,
      has_failed_validations: undefined,
      sort_by: 'table_name',
      sort_order: 'asc',
      page: 1,
      page_size: 50
    })
  }

  const hasActiveFilters = 
    filters.warehouse ||
    filters.schema ||
    filters.search ||
    filters.has_drift !== undefined ||
    filters.has_failed_validations !== undefined

  return (
    <div className="glass-card overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-surface-700/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold text-white">Filters</h3>
          {hasActiveFilters && (
            <span className="px-2 py-0.5 text-xs font-medium bg-cyan-500/20 text-cyan-400 rounded-full">
              Active
            </span>
          )}
        </div>
        <ChevronDown
          className={`w-5 h-5 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {isOpen && (
        <div className="border-t border-surface-700/50 p-6 space-y-6">
          {/* Search */}
          <div>
            <Input
              label="Search"
              placeholder="Search by table name, schema, or warehouse..."
              value={filters.search || ''}
              onChange={(e) => handleChange('search', e.target.value || undefined)}
            />
          </div>

          {/* Warehouse and Schema */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Warehouse
              </label>
              <select
                value={filters.warehouse || ''}
                onChange={(e) => handleChange('warehouse', e.target.value || undefined)}
                className="w-full px-3 py-2 bg-surface-800/50 border border-surface-600 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              >
                <option value="">All Warehouses</option>
                {availableWarehouses.map((wh) => (
                  <option key={wh} value={wh}>
                    {wh.charAt(0).toUpperCase() + wh.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Schema
              </label>
              {availableSchemas.length > 0 ? (
                <select
                  value={filters.schema || ''}
                  onChange={(e) => handleChange('schema', e.target.value || undefined)}
                  className="w-full px-3 py-2 bg-surface-800/50 border border-surface-600 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                >
                  <option value="">All Schemas</option>
                  {availableSchemas.map((schema) => (
                    <option key={schema} value={schema}>
                      {schema}
                    </option>
                  ))}
                </select>
              ) : (
                <Input
                  placeholder="Enter schema name"
                  value={filters.schema || ''}
                  onChange={(e) => handleChange('schema', e.target.value || undefined)}
                />
              )}
            </div>
          </div>

          {/* Status Filters */}
          <div className="space-y-3">
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Status Filters
            </label>
            <div className="space-y-2">
              <Checkbox
                label="Has Drift"
                checked={filters.has_drift === true}
                onChange={(e) => handleChange('has_drift', e.target.checked ? true : undefined)}
              />
              <Checkbox
                label="Has Failed Validations"
                checked={filters.has_failed_validations === true}
                onChange={(e) => handleChange('has_failed_validations', e.target.checked ? true : undefined)}
              />
              <Checkbox
                label="Recently Profiled (Last 24 hours)"
                checked={false}
                onChange={() => {
                  // TODO: Implement recently profiled filter
                }}
                disabled
              />
            </div>
          </div>

          {/* Date Range (for last profiled) */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Last Profiled Date Range
            </label>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-500 mb-1">From</label>
                <input
                  type="date"
                  className="w-full px-3 py-2 bg-surface-800/50 border border-surface-600 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                  onChange={() => {
                    // TODO: Implement date range filter
                  }}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">To</label>
                <input
                  type="date"
                  className="w-full px-3 py-2 bg-surface-800/50 border border-surface-600 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                  onChange={() => {
                    // TODO: Implement date range filter
                  }}
                />
              </div>
            </div>
          </div>

          {/* Clear Filters */}
          <div className="flex justify-end pt-4 border-t border-surface-700/50">
            <Button
              variant="outline"
              onClick={clearFilters}
              disabled={!hasActiveFilters}
            >
              <X className="w-4 h-4 mr-2" />
              Clear Filters
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

