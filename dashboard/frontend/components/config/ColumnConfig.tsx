'use client'

import { Plus, Trash2 } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { Select, SelectOption } from '@/components/ui/Select'
import { Toggle } from '@/components/ui/Toggle'
import { Checkbox } from '@/components/ui/Checkbox'
import { Button } from '@/components/ui/Button'
import { ColumnConfig as ColumnConfigType } from '@/types/config'

export interface ColumnConfigProps {
  columns: ColumnConfigType[]
  onChange: (columns: ColumnConfigType[]) => void
  availableColumns?: string[]
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

const PATTERN_TYPE_OPTIONS: SelectOption[] = [
  { value: 'wildcard', label: 'Wildcard' },
  { value: 'regex', label: 'Regex' },
]

export function ColumnConfig({
  columns,
  onChange,
  availableColumns,
  errors = {},
  isLoading = false,
}: ColumnConfigProps) {
  const handleAddColumn = () => {
    onChange([...columns, { name: '' }])
  }

  const handleRemoveColumn = (index: number) => {
    const newColumns = columns.filter((_, i) => i !== index)
    onChange(newColumns)
  }

  const handleColumnChange = (index: number, updates: Partial<ColumnConfigType>) => {
    const newColumns = [...columns]
    newColumns[index] = { ...newColumns[index], ...updates }
    onChange(newColumns)
  }

  const handleMetricToggle = (index: number, metric: string, checked: boolean) => {
    const column = columns[index]
    const currentMetrics = column.metrics || []
    if (checked) {
      if (!currentMetrics.includes(metric)) {
        handleColumnChange(index, { metrics: [...currentMetrics, metric] })
      }
    } else {
      handleColumnChange(index, { metrics: currentMetrics.filter((m) => m !== metric) })
    }
  }

  return (
    <Card>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium text-gray-900">Column Configuration</h4>
          <Button
            variant="outline"
            size="sm"
            onClick={handleAddColumn}
            disabled={isLoading}
            icon={<Plus className="w-4 h-4" />}
          >
            Add Column
          </Button>
        </div>

        {columns.length === 0 ? (
          <div className="py-6 text-center text-sm text-gray-600">
            No columns configured. Add a column to configure column-level overrides.
          </div>
        ) : (
          <div className="space-y-6">
            {columns.map((column, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <h5 className="text-sm font-medium text-gray-900">
                    Column {index + 1}
                  </h5>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRemoveColumn(index)}
                    disabled={isLoading}
                    icon={<Trash2 className="w-4 h-4" />}
                  >
                    Remove
                  </Button>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  {availableColumns ? (
                    <FormField
                      label="Column Name"
                      required
                      error={errors[`columns.${index}.name`]}
                    >
                      <Select
                        options={availableColumns.map((col) => ({ value: col, label: col }))}
                        value={column.name}
                        onChange={(value) => handleColumnChange(index, { name: value })}
                        placeholder="Select column"
                        disabled={isLoading}
                      />
                    </FormField>
                  ) : (
                    <FormField
                      label="Column Name/Pattern"
                      required
                      helperText="Column name or pattern (use * for wildcard)"
                      error={errors[`columns.${index}.name`]}
                    >
                      <Input
                        value={column.name}
                        onChange={(e) => handleColumnChange(index, { name: e.target.value })}
                        placeholder="column_name or column_*"
                        disabled={isLoading}
                      />
                    </FormField>
                  )}

                  {column.name && column.name.includes('*') && (
                    <FormField
                      label="Pattern Type"
                      helperText="Type of pattern matching"
                    >
                      <Select
                        options={PATTERN_TYPE_OPTIONS}
                        value={column.pattern_type || 'wildcard'}
                        onChange={(value) =>
                          handleColumnChange(index, { pattern_type: value as 'wildcard' | 'regex' || null })
                        }
                        disabled={isLoading}
                      />
                    </FormField>
                  )}
                </div>

                {column.name && (
                  <>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-sm font-medium text-gray-700">
                          Metrics Override
                        </label>
                        <span className="text-xs text-gray-500">
                          Leave empty to inherit from table/global
                        </span>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                        {ALL_METRICS.map((metric) => (
                          <Checkbox
                            key={metric}
                            label={metric.replace(/_/g, ' ')}
                            checked={column.metrics?.includes(metric) || false}
                            onChange={(e) => handleMetricToggle(index, metric, e.target.checked)}
                            disabled={isLoading}
                          />
                        ))}
                      </div>
                    </div>

                    <FormField
                      label="Enable Profiling"
                      helperText="Enable profiling for this column (default: true)"
                    >
                      <Toggle
                        checked={column.profiling?.enabled !== false}
                        onChange={(checked) =>
                          handleColumnChange(index, {
                            profiling: { enabled: checked },
                          })
                        }
                        disabled={isLoading}
                      />
                    </FormField>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  )
}

