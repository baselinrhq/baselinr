'use client'

import { useState, useMemo } from 'react'
import Link from 'next/link'
import { Card } from '@/components/ui/Card'
import { FormField } from '@/components/ui/FormField'
import { Select, SelectOption } from '@/components/ui/Select'
import { Checkbox } from '@/components/ui/Checkbox'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { TablePattern } from '@/types/config'
import { ArrowRight, FileText } from 'lucide-react'

export interface TableProfilingConfigProps {
  tables: TablePattern[]
  onChange: (tables: TablePattern[]) => void
  isLoading?: boolean
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
  isLoading = false,
}: TableProfilingConfigProps) {
  const [selectedTableIndex, setSelectedTableIndex] = useState<number | null>(null)

  const tableOptions: SelectOption[] = useMemo(() => {
    return tables.map((table, index) => ({
      value: String(index),
      label: getTableSummary(table),
    }))
  }, [tables])

  const selectedTable = selectedTableIndex !== null ? tables[selectedTableIndex] : null

  const handleTableSelect = (value: string) => {
    setSelectedTableIndex(value ? parseInt(value, 10) : null)
  }

  const handleTableChange = (updates: Partial<TablePattern>) => {
    if (selectedTableIndex === null) return
    
    const newTables = [...tables]
    newTables[selectedTableIndex] = { ...newTables[selectedTableIndex], ...updates }
    onChange(newTables)
  }

  type TablePatternWithMetrics = TablePattern & {
    metrics?: string[]
  }

  const handleMetricToggle = (metric: string, checked: boolean) => {
    const table = selectedTable as TablePatternWithMetrics
    const currentMetrics = table?.metrics || []
    if (checked) {
      if (!currentMetrics.includes(metric)) {
        handleTableChange({ metrics: [...currentMetrics, metric] } as Partial<TablePattern>)
      }
    } else {
      handleTableChange({ metrics: currentMetrics.filter((m) => m !== metric) } as Partial<TablePattern>)
    }
  }

  const hasOverrides = (table: TablePattern) => {
    const tableWithMetrics = table as TablePatternWithMetrics
    return !!(tableWithMetrics.metrics && tableWithMetrics.metrics.length > 0)
  }

  return (
    <Card>
      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-semibold text-white mb-4">
            Per-Table Metrics Overrides
          </h3>
          <p className="text-sm text-slate-400 mb-6">
            Configure table-specific metrics. Partition, sampling, and column-level settings must be configured in ODCS contracts.
          </p>
        </div>

        {/* Banner linking to contracts */}
        <div className="glass-card border-cyan-500/30 bg-cyan-500/10 p-4 flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-cyan-400" />
            <div>
              <p className="text-sm font-medium text-cyan-300">
                Configure Partition, Sampling & Columns in ODCS Contracts
              </p>
              <p className="text-xs text-cyan-400/80 mt-1">
                Table-level partition, sampling, and column configurations are now managed via ODCS contracts
              </p>
            </div>
          </div>
          <Link href="/config/contracts">
            <Button variant="outline" icon={<ArrowRight className="w-4 h-4" />}>
              Manage Contracts
            </Button>
          </Link>
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
                        checked={((selectedTable as TablePatternWithMetrics).metrics?.includes(metric)) || false}
                        onChange={(e) => handleMetricToggle(metric, e.target.checked)}
                        disabled={isLoading}
                      />
                    ))}
                  </div>
                  {((selectedTable as TablePatternWithMetrics).metrics?.length ?? 0) === 0 && (
                    <p className="text-sm text-slate-500 italic">
                      No metrics selected - will inherit from global settings
                    </p>
                  )}
                </div>
              </div>
            )}

            {selectedTableIndex === null && tables.length > 0 && (
              <div className="py-6 text-center text-sm text-slate-400">
                Select a table above to configure metrics overrides
              </div>
            )}
          </>
        )}
      </div>
    </Card>
  )
}

