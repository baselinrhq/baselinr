'use client'

import { useState, useMemo } from 'react'
import { Card } from '@/components/ui/Card'
import { FormField } from '@/components/ui/FormField'
import { Select, SelectOption } from '@/components/ui/Select'
import { Checkbox } from '@/components/ui/Checkbox'
import { Badge } from '@/components/ui/Badge'
import { Tabs } from '@/components/ui/Tabs'
import { TablePattern } from '@/types/config'
import { PartitionConfig } from './PartitionConfig'
import { SamplingConfig } from './SamplingConfig'
import { ColumnConfig } from './ColumnConfig'

export interface TableProfilingConfigProps {
  tables: TablePattern[]
  onChange: (tables: TablePattern[]) => void
  errors?: Record<string, string>
  isLoading?: boolean
  onGetColumns?: (schema: string, table: string) => Promise<string[]>
}

const ALL_METRICS = [
  'count',
  'null_count',
  'null_ratio',
  'distinct_count',
  'unique_ratio',
  'approx_distinct_count',
  'min',
  'max',
  'mean',
  'stddev',
  'histogram',
  'data_type_inferred',
] as const

/**
 * Get a human-readable summary of a table pattern
 */
function getTableSummary(pattern: TablePattern): string {
  if (pattern.table) {
    return `${pattern.schema || '?'}.${pattern.table}`
  }
  if (pattern.pattern) {
    return `Pattern: ${pattern.pattern}`
  }
  if (pattern.select_schema && pattern.schema) {
    return `Schema: ${pattern.schema}`
  }
  return 'Unknown table'
}

export function TableProfilingConfig({
  tables,
  onChange,
  errors = {},
  isLoading = false,
  onGetColumns,
}: TableProfilingConfigProps) {
  const [selectedTableIndex, setSelectedTableIndex] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<string>('metrics')

  const tableOptions: SelectOption[] = useMemo(() => {
    return tables.map((table, index) => ({
      value: String(index),
      label: getTableSummary(table),
    }))
  }, [tables])

  const selectedTable = selectedTableIndex !== null ? tables[selectedTableIndex] : null

  const handleTableSelect = (value: string) => {
    setSelectedTableIndex(value ? parseInt(value, 10) : null)
    setActiveTab('metrics')
  }

  const handleTableChange = (updates: Partial<TablePattern>) => {
    if (selectedTableIndex === null) return
    
    const newTables = [...tables]
    newTables[selectedTableIndex] = { ...newTables[selectedTableIndex], ...updates }
    onChange(newTables)
  }

  const handleMetricToggle = (metric: string, checked: boolean) => {
    const currentMetrics = selectedTable?.metrics || []
    if (checked) {
      if (!currentMetrics.includes(metric)) {
        handleTableChange({ metrics: [...currentMetrics, metric] })
      }
    } else {
      handleTableChange({ metrics: currentMetrics.filter((m) => m !== metric) })
    }
  }

  const handlePartitionChange = (partition: typeof selectedTable.partition) => {
    handleTableChange({ partition })
  }

  const handleSamplingChange = (sampling: typeof selectedTable.sampling) => {
    handleTableChange({ sampling })
  }

  const handleColumnsChange = (columns: typeof selectedTable.columns) => {
    handleTableChange({ columns })
  }

  const hasOverrides = (table: TablePattern) => {
    return !!(
      table.metrics ||
      table.partition ||
      table.sampling ||
      (table.columns && table.columns.length > 0)
    )
  }

  return (
    <Card>
      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-semibold text-white mb-4">
            Per-Table Overrides
          </h3>
          <p className="text-sm text-slate-400 mb-6">
            Configure table-specific profiling settings. These override the global settings.
          </p>
        </div>

        {tables.length === 0 ? (
          <div className="py-12 text-center">
            <p className="text-sm text-slate-400 mb-4">
              No tables configured. Configure tables in the Table Selection page first.
            </p>
          </div>
        ) : (
          <>
            <FormField
              label="Select Table"
              helperText="Choose a table to configure overrides"
            >
              <Select
                options={tableOptions}
                value={selectedTableIndex !== null ? String(selectedTableIndex) : ''}
                onChange={handleTableSelect}
                placeholder="Select a table"
                disabled={isLoading}
              />
            </FormField>

            {selectedTable && (
              <div className="space-y-4 border-t border-surface-700/50 pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-medium text-white">
                      {getTableSummary(selectedTable)}
                    </h4>
                    {hasOverrides(selectedTable) && (
                      <Badge variant="info" size="sm" className="mt-1">
                        Has Overrides
                      </Badge>
                    )}
                  </div>
                </div>

                <Tabs
                  tabs={[
                    { id: 'metrics', label: 'Metrics' },
                    { id: 'partition', label: 'Partition' },
                    { id: 'sampling', label: 'Sampling' },
                    { id: 'columns', label: 'Columns' },
                  ]}
                  activeTab={activeTab}
                  onChange={setActiveTab}
                />

                {activeTab === 'metrics' && (
                  <div className="space-y-4 pt-4">
                    <div className="flex items-center justify-between">
                      <p className="text-sm text-slate-400">
                        Override global metrics for this table. Leave empty to inherit from global settings.
                      </p>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      {ALL_METRICS.map((metric) => (
                        <Checkbox
                          key={metric}
                          label={metric.replace(/_/g, ' ')}
                          checked={selectedTable.metrics?.includes(metric) || false}
                          onChange={(e) => handleMetricToggle(metric, e.target.checked)}
                          disabled={isLoading}
                        />
                      ))}
                    </div>
                    {selectedTable.metrics && selectedTable.metrics.length === 0 && (
                      <p className="text-sm text-slate-500 italic">
                        No metrics selected - will inherit from global settings
                      </p>
                    )}
                  </div>
                )}

                {activeTab === 'partition' && (
                  <div className="pt-4">
                    <PartitionConfig
                      partition={selectedTable.partition}
                      onChange={handlePartitionChange}
                      errors={errors}
                      isLoading={isLoading}
                    />
                  </div>
                )}

                {activeTab === 'sampling' && (
                  <div className="pt-4">
                    <SamplingConfig
                      sampling={selectedTable.sampling}
                      onChange={handleSamplingChange}
                      errors={errors}
                      isLoading={isLoading}
                    />
                  </div>
                )}

                {activeTab === 'columns' && (
                  <div className="pt-4">
                    <ColumnConfig
                      columns={selectedTable.columns || []}
                      onChange={handleColumnsChange}
                      errors={errors}
                      isLoading={isLoading}
                      onGetColumns={onGetColumns}
                    />
                  </div>
                )}
              </div>
            )}

            {selectedTableIndex === null && tables.length > 0 && (
              <div className="py-6 text-center text-sm text-slate-400">
                Select a table above to configure overrides
              </div>
            )}
          </>
        )}
      </div>
    </Card>
  )
}

