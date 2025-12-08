'use client'

import { SQLHookForm } from './SQLHookForm'
import { HookConfig } from '@/types/config'

export interface SnowflakeHookFormProps {
  hook: HookConfig
  onChange: (hook: HookConfig) => void
  errors?: Record<string, string>
}

export function SnowflakeHookForm(props: SnowflakeHookFormProps) {
  // Snowflake hook form is similar to SQL hook form
  // Just ensure connection type is snowflake
  const hookWithType = {
    ...props.hook,
    connection: props.hook.connection
      ? { ...props.hook.connection, type: 'snowflake' as const }
      : { type: 'snowflake' as const, database: '' },
  }

  return <SQLHookForm {...props} hook={hookWithType} />
}

export default SnowflakeHookForm

