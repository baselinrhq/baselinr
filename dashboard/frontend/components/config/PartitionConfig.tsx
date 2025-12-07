'use client'

import { useState } from 'react'
import { Card } from '@/components/ui/Card'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { Select, SelectOption } from '@/components/ui/Select'
import { Toggle } from '@/components/ui/Toggle'
import { Button } from '@/components/ui/Button'
import { PartitionConfig as PartitionConfigType } from '@/types/config'
import { X } from 'lucide-react'

export interface PartitionConfigProps {
  partition?: PartitionConfigType | null
  onChange: (partition: PartitionConfigType | null) => void
  errors?: Record<string, string>
  isLoading?: boolean
}

const PARTITION_STRATEGY_OPTIONS: SelectOption[] = [
  { value: 'latest', label: 'Latest Partition Only' },
  { value: 'recent_n', label: 'Recent N Partitions' },
  { value: 'sample', label: 'Sample Partitions' },
  { value: 'all', label: 'All Partitions' },
  { value: 'specific_values', label: 'Specific Partition Values' },
]

export function PartitionConfig({
  partition,
  onChange,
  errors = {},
  isLoading = false,
}: PartitionConfigProps) {
  const [specificValue, setSpecificValue] = useState('')

  const handleChange = (field: keyof PartitionConfigType, value: unknown) => {
    if (!partition) {
      onChange({
        strategy: 'latest',
        [field]: value,
      } as PartitionConfigType)
    } else {
      onChange({ ...partition, [field]: value })
    }
  }

  const handleAddSpecificValue = () => {
    if (!specificValue.trim()) return
    
    const currentValues = partition?.values || []
    const newValues = [...currentValues, specificValue.trim()]
    handleChange('values', newValues)
    setSpecificValue('')
  }

  const handleRemoveSpecificValue = (index: number) => {
    const currentValues = partition?.values || []
    const newValues = currentValues.filter((_, i) => i !== index)
    handleChange('values', newValues.length > 0 ? newValues : null)
  }

  if (!partition) {
    return (
      <Card>
        <div className="py-6 text-center">
          <p className="text-sm text-gray-600 mb-4">No partition configuration</p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onChange({ strategy: 'latest' })}
            disabled={isLoading}
          >
            Add Partition Config
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <Card>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium text-gray-900">Partition Configuration</h4>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onChange(null)}
            disabled={isLoading}
          >
            Remove
          </Button>
        </div>

        <FormField
          label="Partition Key"
          helperText="Column name used for partitioning"
          error={errors.key}
        >
          <Input
            value={partition.key || ''}
            onChange={(e) => handleChange('key', e.target.value || null)}
            placeholder="order_date"
            disabled={isLoading}
          />
        </FormField>

        <FormField
          label="Strategy"
          required
          error={errors.strategy}
        >
          <Select
            options={PARTITION_STRATEGY_OPTIONS}
            value={partition.strategy}
            onChange={(value) => handleChange('strategy', value as PartitionConfigType['strategy'])}
            disabled={isLoading}
          />
        </FormField>

        {partition.strategy === 'recent_n' && (
          <FormField
            label="Recent N"
            required
            helperText="Number of recent partitions to process"
            error={errors.recent_n}
          >
            <Input
              type="number"
              value={partition.recent_n ?? ''}
              onChange={(e) =>
                handleChange('recent_n', e.target.value ? parseInt(e.target.value, 10) : null)
              }
              min={1}
              disabled={isLoading}
            />
          </FormField>
        )}

        {partition.strategy === 'specific_values' && (
          <FormField
            label="Specific Values"
            required
            helperText="Partition values to process"
            error={errors.values}
          >
            <div className="space-y-2">
              <div className="flex gap-2">
                <Input
                  value={specificValue}
                  onChange={(e) => setSpecificValue(e.target.value)}
                  placeholder="Enter partition value"
                  disabled={isLoading}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      handleAddSpecificValue()
                    }
                  }}
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleAddSpecificValue}
                  disabled={isLoading || !specificValue.trim()}
                >
                  Add
                </Button>
              </div>
              {partition.values && partition.values.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {partition.values.map((value, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 rounded text-sm"
                    >
                      {String(value)}
                      <button
                        type="button"
                        onClick={() => handleRemoveSpecificValue(index)}
                        disabled={isLoading}
                        className="text-gray-500 hover:text-gray-700"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </FormField>
        )}

        <FormField
          label="Metadata Fallback"
          helperText="Use metadata for partition information if available"
        >
          <Toggle
            checked={partition.metadata_fallback ?? false}
            onChange={(checked) => handleChange('metadata_fallback', checked)}
            disabled={isLoading}
          />
        </FormField>
      </div>
    </Card>
  )
}

