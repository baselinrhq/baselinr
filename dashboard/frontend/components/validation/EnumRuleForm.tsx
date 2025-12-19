'use client'

import { useState, useEffect } from 'react'
import { Plus, X } from 'lucide-react'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { ValidationRuleConfig } from '@/types/config'

export interface EnumRuleFormProps {
  rule: ValidationRuleConfig
  onChange: (rule: ValidationRuleConfig) => void
  errors?: Record<string, string>
}

export function EnumRuleForm({ rule, onChange, errors }: EnumRuleFormProps) {
  const [values, setValues] = useState<string[]>(() => {
    if (rule.allowed_values && Array.isArray(rule.allowed_values)) {
      return rule.allowed_values.map(v => String(v))
    }
    return ['']
  })

  useEffect(() => {
    if (rule.allowed_values && Array.isArray(rule.allowed_values)) {
      const newValues = rule.allowed_values.map(v => String(v))
      if (JSON.stringify(newValues) !== JSON.stringify(values)) {
        setValues(newValues.length > 0 ? newValues : [''])
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rule.allowed_values])

  const handleValueChange = (index: number, value: string) => {
    const newValues = [...values]
    newValues[index] = value
    setValues(newValues)
    
    // Filter out empty values and update rule
    const nonEmptyValues = newValues.filter(v => v.trim() !== '')
    onChange({
      ...rule,
      allowed_values: nonEmptyValues.length > 0 ? nonEmptyValues : null,
    })
  }

  const handleAddValue = () => {
    setValues([...values, ''])
  }

  const handleRemoveValue = (index: number) => {
    if (values.length === 1) {
      // Keep at least one empty field
      setValues([''])
      onChange({
        ...rule,
        allowed_values: null,
      })
    } else {
      const newValues = values.filter((_, i) => i !== index)
      setValues(newValues)
      
      const nonEmptyValues = newValues.filter(v => v.trim() !== '')
      onChange({
        ...rule,
        allowed_values: nonEmptyValues.length > 0 ? nonEmptyValues : null,
      })
    }
  }

  const hasDuplicates = values.some((v, i) => 
    v.trim() !== '' && values.findIndex(val => val.trim() === v.trim()) !== i
  )

  return (
    <div className="space-y-4">
      <FormField
        label="Allowed Values"
        error={hasDuplicates ? 'Duplicate values are not allowed' : errors?.allowed_values}
        required
        helperText="Enter the list of allowed values for this column"
      >
        <div className="space-y-2">
          {values.map((value, index) => (
            <div key={index} className="flex items-center gap-2">
              <Input
                value={value}
                onChange={(e) => handleValueChange(index, e.target.value)}
                placeholder={`Value ${index + 1}`}
                className="flex-1"
              />
              {values.length > 1 && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => handleRemoveValue(index)}
                  icon={<X className="w-4 h-4" />}
                />
              )}
            </div>
          ))}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleAddValue}
            icon={<Plus className="w-4 h-4" />}
          >
            Add Value
          </Button>
        </div>
      </FormField>

      {hasDuplicates && (
        <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
          Duplicate values are not allowed. Please remove duplicates.
        </div>
      )}

      <div className="text-sm text-gray-600">
        <p className="font-medium mb-1">Note:</p>
        <ul className="list-disc list-inside space-y-1 ml-2">
          <li>Column values must match one of the allowed values exactly</li>
          <li>Values are case-sensitive</li>
          <li>At least one value must be specified</li>
        </ul>
      </div>
    </div>
  )
}

