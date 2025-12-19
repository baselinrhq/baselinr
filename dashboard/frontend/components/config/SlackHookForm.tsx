'use client'

import { HookConfig } from '@/types/config'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Toggle } from '@/components/ui/Toggle'
import { Checkbox } from '@/components/ui/Checkbox'

export interface SlackHookFormProps {
  hook: HookConfig
  onChange: (hook: HookConfig) => void
  errors?: Record<string, string>
}

export function SlackHookForm({
  hook,
  onChange,
  errors = {},
}: SlackHookFormProps) {
  const updateField = (field: keyof HookConfig, value: unknown) => {
    onChange({
      ...hook,
      [field]: value,
    })
  }

  return (
    <div className="space-y-4">
      <FormField
        label="Webhook URL"
        required
        error={errors.webhook_url}
        helperText="Slack webhook URL (supports ${ENV_VAR} syntax)"
      >
        <Input
          type="text"
          value={hook.webhook_url || ''}
          onChange={(e) => updateField('webhook_url', e.target.value)}
          placeholder="https://hooks.slack.com/services/..."
        />
      </FormField>

      <FormField
        label="Channel"
        error={errors.channel}
        helperText="Optional: Override default channel (e.g., #alerts, @username)"
      >
        <Input
          type="text"
          value={hook.channel || ''}
          onChange={(e) => updateField('channel', e.target.value)}
          placeholder="#data-alerts"
        />
      </FormField>

      <FormField
        label="Username"
        error={errors.username}
        helperText="Display name for the bot"
      >
        <Input
          type="text"
          value={hook.username || 'Baselinr'}
          onChange={(e) => updateField('username', e.target.value)}
          placeholder="Baselinr"
        />
      </FormField>

      <FormField
        label="Minimum Severity"
        error={errors.min_severity}
        helperText="Minimum drift severity to alert"
      >
        <Select
          options={[
            { value: 'low', label: 'Low' },
            { value: 'medium', label: 'Medium' },
            { value: 'high', label: 'High' },
          ]}
          value={hook.min_severity || 'low'}
          onChange={(value) => updateField('min_severity', value)}
        />
      </FormField>

      <FormField label="Alert Settings">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Checkbox
              checked={hook.alert_on_drift !== false}
              onChange={(e) => updateField('alert_on_drift', e.target.checked)}
            />
            <label className="text-sm text-gray-700">Alert on drift events</label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              checked={hook.alert_on_schema_change !== false}
              onChange={(e) => updateField('alert_on_schema_change', e.target.checked)}
            />
            <label className="text-sm text-gray-700">Alert on schema changes</label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              checked={hook.alert_on_profiling_failure !== false}
              onChange={(e) => updateField('alert_on_profiling_failure', e.target.checked)}
            />
            <label className="text-sm text-gray-700">Alert on profiling failures</label>
          </div>
        </div>
      </FormField>

      <FormField
        label="Timeout (seconds)"
        error={errors.timeout}
        helperText="HTTP request timeout"
      >
        <Input
          type="number"
          value={hook.timeout || 10}
          onChange={(e) => updateField('timeout', parseInt(e.target.value) || 10)}
          min={1}
          max={60}
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

export default SlackHookForm

