'use client'

import { useState, useEffect } from 'react'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { ValidationRuleConfig } from '@/types/config'

export interface RangeRuleFormProps {
  rule: ValidationRuleConfig
  onChange: (rule: ValidationRuleConfig) => void
  errors?: Record<string, string>
}

export function RangeRuleForm({ rule, onChange, errors }: RangeRuleFormProps) {
  const [minValue, setMinValue] = useState<string>(
    rule.min_value !== null && rule.min_value !== undefined ? String(rule.min_value) : ''
  )
  const [maxValue, setMaxValue] = useState<string>(
    rule.max_value !== null && rule.max_value !== undefined ? String(rule.max_value) : ''
  )
  const [rangeError, setRangeError] = useState<string | null>(null)

  useEffect(() => {
    const min = rule.min_value !== null && rule.min_value !== undefined ? String(rule.min_value) : ''
    const max = rule.max_value !== null && rule.max_value !== undefined ? String(rule.max_value) : ''
    setMinValue(min)
    setMaxValue(max)
  }, [rule.min_value, rule.max_value])

  const handleMinChange = (value: string) => {
    setMinValue(value)
    const min = value === '' ? null : Number(value)
    
    if (value !== '' && isNaN(Number(value))) {
      setRangeError('Minimum value must be a number')
      return
    }

    setRangeError(null)
    
    const max = rule.max_value
    if (min !== null && max !== null && max !== undefined && min > max) {
      setRangeError('Minimum value must be less than or equal to maximum value')
    } else {
      setRangeError(null)
    }

    onChange({
      ...rule,
      min_value: min,
    })
  }

  const handleMaxChange = (value: string) => {
    setMaxValue(value)
    const max = value === '' ? null : Number(value)
    
    if (value !== '' && isNaN(Number(value))) {
      setRangeError('Maximum value must be a number')
      return
    }

    setRangeError(null)
    
    const min = rule.min_value
    if (min !== null && min !== undefined && max !== null && min > max) {
      setRangeError('Minimum value must be less than or equal to maximum value')
    } else {
      setRangeError(null)
    }

    onChange({
      ...rule,
      max_value: max,
    })
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <FormField
          label="Minimum Value"
          error={rangeError || errors?.min_value}
          helperText="Leave empty for no minimum"
        >
          <Input
            type="number"
            value={minValue}
            onChange={(e) => handleMinChange(e.target.value)}
            placeholder="0"
          />
        </FormField>

        <FormField
          label="Maximum Value"
          error={rangeError || errors?.max_value}
          helperText="Leave empty for no maximum"
        >
          <Input
            type="number"
            value={maxValue}
            onChange={(e) => handleMaxChange(e.target.value)}
            placeholder="1000000"
          />
        </FormField>
      </div>

      {rangeError && (
        <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
          {rangeError}
        </div>
      )}

      <div className="text-sm text-gray-600">
        <p className="font-medium mb-1">Note:</p>
        <ul className="list-disc list-inside space-y-1 ml-2">
          <li>For numeric columns, validates value is within the specified range</li>
          <li>For string columns, validates string length is within the range</li>
          <li>At least one bound (min or max) should be specified</li>
        </ul>
      </div>
    </div>
  )
}

