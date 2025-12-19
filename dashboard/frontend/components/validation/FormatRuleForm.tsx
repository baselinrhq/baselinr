'use client'

import { useState, useEffect } from 'react'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { Select, SelectOption } from '@/components/ui/Select'
import { ValidationRuleConfig } from '@/types/config'

export interface FormatRuleFormProps {
  rule: ValidationRuleConfig
  onChange: (rule: ValidationRuleConfig) => void
  errors?: Record<string, string>
}

const PREDEFINED_PATTERNS: SelectOption[] = [
  { value: 'email', label: 'Email' },
  { value: 'url', label: 'URL' },
  { value: 'phone', label: 'Phone' },
  { value: 'custom', label: 'Custom Regex' },
]

export function FormatRuleForm({ rule, onChange, errors }: FormatRuleFormProps) {
  const [patternType, setPatternType] = useState<'predefined' | 'custom'>('predefined')
  const [customPattern, setCustomPattern] = useState<string>(rule.pattern || '')
  const [patternError, setPatternError] = useState<string | null>(null)

  // Determine if pattern is predefined or custom
  useEffect(() => {
    if (rule.pattern) {
      const isPredefined = ['email', 'url', 'phone'].includes(rule.pattern)
      setPatternType(isPredefined ? 'predefined' : 'custom')
      if (!isPredefined) {
        setCustomPattern(rule.pattern)
      }
    }
  }, [rule.pattern])

  const handlePredefinedPatternChange = (value: string) => {
    if (value === 'custom') {
      setPatternType('custom')
      onChange({ ...rule, pattern: customPattern || '' })
    } else {
      setPatternType('predefined')
      onChange({ ...rule, pattern: value })
    }
  }

  const handleCustomPatternChange = (value: string) => {
    setCustomPattern(value)
    
    // Validate regex
    if (value) {
      try {
        new RegExp(value)
        setPatternError(null)
        onChange({ ...rule, pattern: value })
      } catch {
        setPatternError('Invalid regex pattern')
      }
    } else {
      setPatternError(null)
      onChange({ ...rule, pattern: '' })
    }
  }

  const selectedPredefined = patternType === 'predefined' && rule.pattern && ['email', 'url', 'phone'].includes(rule.pattern)
    ? rule.pattern
    : patternType === 'custom' ? 'custom' : 'email'

  return (
    <div className="space-y-4">
      <FormField
        label="Pattern Type"
        error={errors?.pattern}
        required
      >
        <Select
          value={selectedPredefined}
          onChange={handlePredefinedPatternChange}
          options={PREDEFINED_PATTERNS}
        />
      </FormField>

      {patternType === 'predefined' ? (
        <div className="text-sm text-gray-600">
          {rule.pattern === 'email' && (
            <p>Validates standard email format: user@example.com</p>
          )}
          {rule.pattern === 'url' && (
            <p>Validates HTTP/HTTPS URLs: https://example.com</p>
          )}
          {rule.pattern === 'phone' && (
            <p>Validates phone numbers with international format support</p>
          )}
        </div>
      ) : (
        <FormField
          label="Custom Regex Pattern"
          error={patternError || errors?.pattern}
          required
          helperText="Enter a valid regular expression pattern"
        >
          <Input
            value={customPattern}
            onChange={(e) => handleCustomPatternChange(e.target.value)}
            placeholder="^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
          />
          {customPattern && !patternError && (
            <p className="text-xs text-green-600 mt-1">✓ Valid regex pattern</p>
          )}
        </FormField>
      )}

      {patternType === 'custom' && (
        <div className="text-sm text-gray-600 space-y-1">
          <p className="font-medium">Examples:</p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li>Email: <code className="text-xs bg-gray-100 px-1 rounded">{'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'}</code></li>
            <li>UUID: <code className="text-xs bg-gray-100 px-1 rounded">{'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'}</code></li>
            <li>Date (YYYY-MM-DD): <code className="text-xs bg-gray-100 px-1 rounded">{'^\\d{4}-\\d{2}-\\d{2}$'}</code></li>
          </ul>
        </div>
      )}
    </div>
  )
}

