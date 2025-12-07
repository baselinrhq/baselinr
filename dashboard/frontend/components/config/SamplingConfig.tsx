'use client'

import { Card } from '@/components/ui/Card'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { Select, SelectOption } from '@/components/ui/Select'
import { Toggle } from '@/components/ui/Toggle'
import { Slider } from '@/components/ui/Slider'
import { Button } from '@/components/ui/Button'
import { SamplingConfig as SamplingConfigType } from '@/types/config'

export interface SamplingConfigProps {
  sampling?: SamplingConfigType | null
  onChange: (sampling: SamplingConfigType | null) => void
  errors?: Record<string, string>
  isLoading?: boolean
}

const SAMPLING_METHOD_OPTIONS: SelectOption[] = [
  { value: 'random', label: 'Random Sampling' },
  { value: 'stratified', label: 'Stratified Sampling' },
  { value: 'topk', label: 'Top K Rows' },
]

export function SamplingConfig({
  sampling,
  onChange,
  errors = {},
  isLoading = false,
}: SamplingConfigProps) {
  const handleChange = (field: keyof SamplingConfigType, value: unknown) => {
    if (!sampling) {
      onChange({
        enabled: true,
        method: 'random',
        fraction: 0.1,
        [field]: value,
      } as SamplingConfigType)
    } else {
      onChange({ ...sampling, [field]: value })
    }
  }

  if (!sampling) {
    return (
      <Card>
        <div className="py-6 text-center">
          <p className="text-sm text-gray-600 mb-4">No sampling configuration</p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onChange({ enabled: true, method: 'random', fraction: 0.1 })}
            disabled={isLoading}
          >
            Add Sampling Config
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <Card>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium text-gray-900">Sampling Configuration</h4>
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
          label="Enable Sampling"
          helperText="Enable data sampling for this table"
        >
          <Toggle
            checked={sampling.enabled}
            onChange={(checked) => {
              if (!checked) {
                onChange(null)
              } else {
                handleChange('enabled', true)
              }
            }}
            disabled={isLoading}
          />
        </FormField>

        {sampling.enabled && (
          <>
            <FormField
              label="Sampling Method"
              required
              error={errors.method}
            >
              <Select
                options={SAMPLING_METHOD_OPTIONS}
                value={sampling.method}
                onChange={(value) => handleChange('method', value as SamplingConfigType['method'])}
                disabled={isLoading}
              />
            </FormField>

            <FormField
              label="Sample Fraction"
              required
              helperText="Fraction of data to sample (0.0-1.0)"
              error={errors.fraction}
            >
              <div className="space-y-2">
                <Slider
                  value={sampling.fraction}
                  onChange={(value) =>
                    handleChange('fraction', typeof value === 'number' ? value : value[0])
                  }
                  min={0}
                  max={1}
                  step={0.01}
                  showValue
                  disabled={isLoading}
                />
                <Input
                  type="number"
                  value={sampling.fraction}
                  onChange={(e) =>
                    handleChange('fraction', e.target.value ? parseFloat(e.target.value) : 0)
                  }
                  min={0}
                  max={1}
                  step={0.01}
                  disabled={isLoading}
                  className="w-32"
                />
              </div>
            </FormField>

            <FormField
              label="Max Rows"
              helperText="Maximum number of rows to sample (optional)"
              error={errors.max_rows}
            >
              <Input
                type="number"
                value={sampling.max_rows ?? ''}
                onChange={(e) =>
                  handleChange('max_rows', e.target.value ? parseInt(e.target.value, 10) : null)
                }
                min={1}
                disabled={isLoading}
              />
            </FormField>
          </>
        )}
      </div>
    </Card>
  )
}

