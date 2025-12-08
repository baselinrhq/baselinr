'use client'

import { HookConfig } from '@/types/config'
import { FormField } from '@/components/ui/FormField'
import { Select } from '@/components/ui/Select'
import { Toggle } from '@/components/ui/Toggle'

export interface LoggingHookFormProps {
  hook: HookConfig
  onChange: (hook: HookConfig) => void
  errors?: Record<string, string>
}

export function LoggingHookForm({
  hook,
  onChange,
  errors = {},
}: LoggingHookFormProps) {
  const updateField = (field: keyof HookConfig, value: unknown) => {
    onChange({
      ...hook,
      [field]: value,
    })
  }

  return (
    <div className="space-y-4">
      <FormField label="Log Level" error={errors.log_level}>
        <Select
          options={[
            { value: 'DEBUG', label: 'DEBUG' },
            { value: 'INFO', label: 'INFO' },
            { value: 'WARNING', label: 'WARNING' },
            { value: 'ERROR', label: 'ERROR' },
          ]}
          value={hook.log_level || 'INFO'}
          onChange={(value) => updateField('log_level', value)}
        />
      </FormField>

      <FormField label="Enabled">
        <div className="flex items-center gap-2">
          <Toggle
            checked={hook.enabled !== false}
            onChange={(checked) => updateField('enabled', checked)}
          />
          <span className="text-sm text-gray-600">
            {hook.enabled !== false ? 'Enabled' : 'Disabled'}
          </span>
        </div>
      </FormField>
    </div>
  )
}

export default LoggingHookForm

