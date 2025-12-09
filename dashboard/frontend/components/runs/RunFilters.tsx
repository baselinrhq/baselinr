'use client'

import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Button } from '@/components/ui/Button'

export interface RunFilters {
  warehouse?: string
  schema?: string
  table?: string
  status?: string
  start_date?: string
  end_date?: string
  min_duration?: number
  max_duration?: number
  sort_by?: string
  sort_order?: string
}

interface RunFiltersProps {
  filters: RunFilters
  onChange: (filters: RunFilters) => void
}

export default function RunFilters({ filters, onChange }: RunFiltersProps) {
  const handleChange = (key: keyof RunFilters, value: string | number | undefined) => {
    onChange({ ...filters, [key]: value })
  }

  const clearFilters = () => {
    onChange({
      warehouse: '',
      schema: '',
      table: '',
      status: '',
      start_date: '',
      end_date: '',
      min_duration: undefined,
      max_duration: undefined,
      sort_by: 'profiled_at',
      sort_order: 'desc',
    })
  }

  const warehouseOptions = [
    { value: '', label: 'All Warehouses' },
    { value: 'postgres', label: 'PostgreSQL' },
    { value: 'snowflake', label: 'Snowflake' },
    { value: 'mysql', label: 'MySQL' },
    { value: 'bigquery', label: 'BigQuery' },
    { value: 'redshift', label: 'Redshift' },
    { value: 'sqlite', label: 'SQLite' },
  ]

  const statusOptions = [
    { value: '', label: 'All Statuses' },
    { value: 'success', label: 'Success' },
    { value: 'completed', label: 'Completed' },
    { value: 'failed', label: 'Failed' },
    { value: 'drift_detected', label: 'Drift Detected' },
  ]

  const sortByOptions = [
    { value: 'profiled_at', label: 'Profiled At' },
    { value: 'row_count', label: 'Row Count' },
    { value: 'column_count', label: 'Column Count' },
    { value: 'status', label: 'Status' },
  ]

  const sortOrderOptions = [
    { value: 'desc', label: 'Descending' },
    { value: 'asc', label: 'Ascending' },
  ]

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Filters</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Warehouse */}
        <div>
          <Select
            label="Warehouse"
            options={warehouseOptions}
            value={filters.warehouse || ''}
            onChange={(value) => handleChange('warehouse', value)}
            placeholder="All Warehouses"
          />
        </div>

        {/* Schema */}
        <div>
          <Input
            label="Schema"
            type="text"
            value={filters.schema || ''}
            onChange={(e) => handleChange('schema', e.target.value)}
            placeholder="Enter schema name"
          />
        </div>

        {/* Table */}
        <div>
          <Input
            label="Table"
            type="text"
            value={filters.table || ''}
            onChange={(e) => handleChange('table', e.target.value)}
            placeholder="Enter table name"
          />
        </div>

        {/* Status */}
        <div>
          <Select
            label="Status"
            options={statusOptions}
            value={filters.status || ''}
            onChange={(value) => handleChange('status', value)}
            placeholder="All Statuses"
          />
        </div>

        {/* Start Date */}
        <div>
          <Input
            label="Start Date"
            type="date"
            value={filters.start_date || ''}
            onChange={(e) => handleChange('start_date', e.target.value)}
          />
        </div>

        {/* End Date */}
        <div>
          <Input
            label="End Date"
            type="date"
            value={filters.end_date || ''}
            onChange={(e) => handleChange('end_date', e.target.value)}
          />
        </div>

        {/* Min Duration (seconds) */}
        <div>
          <Input
            label="Min Duration (seconds)"
            type="number"
            value={filters.min_duration?.toString() || ''}
            onChange={(e) => handleChange('min_duration', e.target.value ? parseFloat(e.target.value) : undefined)}
            placeholder="0"
            min={0}
          />
        </div>

        {/* Max Duration (seconds) */}
        <div>
          <Input
            label="Max Duration (seconds)"
            type="number"
            value={filters.max_duration?.toString() || ''}
            onChange={(e) => handleChange('max_duration', e.target.value ? parseFloat(e.target.value) : undefined)}
            placeholder="∞"
            min={0}
          />
        </div>

        {/* Sort By */}
        <div>
          <Select
            label="Sort By"
            options={sortByOptions}
            value={filters.sort_by || 'profiled_at'}
            onChange={(value) => handleChange('sort_by', value)}
          />
        </div>

        {/* Sort Order */}
        <div>
          <Select
            label="Sort Order"
            options={sortOrderOptions}
            value={filters.sort_order || 'desc'}
            onChange={(value) => handleChange('sort_order', value)}
          />
        </div>
      </div>

      <div className="mt-4 flex justify-end gap-2">
        <Button
          variant="secondary"
          onClick={clearFilters}
        >
          Clear Filters
        </Button>
      </div>
    </div>
  )
}

