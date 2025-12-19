'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { HookConfig } from '@/types/config'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Toggle } from '@/components/ui/Toggle'
import { Button } from '@/components/ui/Button'
import { ConnectionForm } from './ConnectionForm'
import { listConnections } from '@/lib/api/connections'
import { testConnection } from '@/lib/api/config'

export interface SQLHookFormProps {
  hook: HookConfig
  onChange: (hook: HookConfig) => void
  errors?: Record<string, string>
}

export function SQLHookForm({
  hook,
  onChange,
  errors = {},
}: SQLHookFormProps) {
  const [useSavedConnection, setUseSavedConnection] = useState(
    !!hook.connection && !hook.connection.host && !hook.connection.account
  )
  const [showConnectionForm, setShowConnectionForm] = useState(!hook.connection)

  const { data: connectionsData } = useQuery({
    queryKey: ['connections'],
    queryFn: listConnections,
    enabled: useSavedConnection,
  })

  const updateField = (field: keyof HookConfig, value: unknown) => {
    onChange({
      ...hook,
      [field]: value,
    })
  }

  const handleConnectionSelect = (connectionId: string) => {
    if (!connectionId) {
      updateField('connection', undefined)
      return
    }
    const selected = connectionsData?.connections.find((c) => c.id === connectionId)
    if (selected) {
      updateField('connection', selected.connection)
    }
  }

  // Find the connection ID that matches the current hook's connection
  const getSelectedConnectionId = (): string => {
    if (!hook.connection || !connectionsData?.connections) return ''
    // Try to find a matching connection by comparing key properties
    const match = connectionsData.connections.find((conn) => {
      const connConfig = conn.connection
      const hookConn = hook.connection
      // Compare by type and name (if available) or other identifying properties
      return (
        connConfig.type === hookConn.type &&
        connConfig.database === hookConn.database &&
        (connConfig.host === hookConn.host || (!connConfig.host && !hookConn.host))
      )
    })
    return match?.id || ''
  }

  const handleTestConnection = async () => {
    if (!hook.connection) return
    try {
      await testConnection(hook.connection)
      alert('Connection test successful!')
    } catch (err) {
      alert(`Connection test failed: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  return (
    <div className="space-y-4">
      <FormField label="Connection Source">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <input
              type="radio"
              id="saved-connection"
              checked={useSavedConnection}
              onChange={() => {
                setUseSavedConnection(true)
                setShowConnectionForm(false)
              }}
            />
            <label htmlFor="saved-connection" className="text-sm text-gray-700">
              Use saved connection
            </label>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="radio"
              id="new-connection"
              checked={!useSavedConnection}
              onChange={() => {
                setUseSavedConnection(false)
                setShowConnectionForm(true)
              }}
            />
            <label htmlFor="new-connection" className="text-sm text-gray-700">
              Configure new connection
            </label>
          </div>
        </div>
      </FormField>

      {useSavedConnection ? (
        <FormField label="Saved Connection" required error={errors.connection}>
          <Select
            options={[
              { value: '', label: 'Select a connection...' },
              ...(connectionsData?.connections.map((conn) => ({
                value: conn.id,
                label: `${conn.name} (${conn.connection.type})`,
              })) || []),
            ]}
            value={getSelectedConnectionId()}
            onChange={(value) => handleConnectionSelect(value)}
          />
        </FormField>
      ) : (
        <>
          {showConnectionForm && (
            <div className="border border-gray-200 rounded-lg p-4">
              <ConnectionForm
                connection={hook.connection || { type: 'postgres', database: '' }}
                onChange={(conn) => updateField('connection', conn)}
                errors={typeof errors.connection === 'object' && errors.connection !== null ? errors.connection as Record<string, string> : undefined}
              />
              <div className="mt-4">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleTestConnection}
                  disabled={!hook.connection}
                >
                  Test Connection
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      <FormField
        label="Table Name"
        error={errors.table_name}
        helperText="Table name for storing events"
      >
        <Input
          type="text"
          value={hook.table_name || 'baselinr_events'}
          onChange={(e) => updateField('table_name', e.target.value)}
          placeholder="baselinr_events"
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

export default SQLHookForm

