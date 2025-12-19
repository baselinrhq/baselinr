'use client'

import { HookConfig } from '@/types/config'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { Toggle } from '@/components/ui/Toggle'

export interface CustomHookFormProps {
  hook: HookConfig
  onChange: (hook: HookConfig) => void
  errors?: Record<string, string>
}

export function CustomHookForm({
  hook,
  onChange,
  errors = {},
}: CustomHookFormProps) {
  const updateField = (field: keyof HookConfig, value: unknown) => {
    onChange({
      ...hook,
      [field]: value,
    })
  }

  const handleParamsChange = (value: string) => {
    try {
      const parsed = JSON.parse(value || '{}')
      updateField('params', parsed)
    } catch {
      // Invalid JSON, store as string for now
      updateField('params', {})
    }
  }

  const paramsString = JSON.stringify(hook.params || {}, null, 2)

  return (
    <div className="space-y-4">
      <FormField
        label="Module Path"
        required
        error={errors.module}
        helperText="Python module path (e.g., mypackage.hooks)"
      >
        <Input
          type="text"
          value={hook.module || ''}
          onChange={(e) => updateField('module', e.target.value)}
          placeholder="mypackage.hooks"
        />
      </FormField>

      <FormField
        label="Class Name"
        required
        error={errors.class_name}
        helperText="Hook class name"
      >
        <Input
          type="text"
          value={hook.class_name || ''}
          onChange={(e) => updateField('class_name', e.target.value)}
          placeholder="MyCustomHook"
        />
      </FormField>

      <FormField
        label="Parameters (JSON)"
        error={errors.params}
        helperText="Additional parameters as JSON object"
      >
        <textarea
          className="w-full min-h-[120px] px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono"
          value={paramsString}
          onChange={(e) => handleParamsChange(e.target.value)}
          placeholder='{"key": "value"}'
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

export default CustomHookForm

