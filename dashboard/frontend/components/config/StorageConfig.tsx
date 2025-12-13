'use client'

import { useState, useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { StorageConfig as StorageConfigType, ConnectionConfig } from '@/types/config'
import { ConnectionsListResponse } from '@/types/connection'
import { listConnections } from '@/lib/api/connections'
import { testConnection, ConnectionTestError } from '@/lib/api/config'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { Select, SelectOption } from '@/components/ui/Select'
import { Toggle } from '@/components/ui/Toggle'
import { Button } from '@/components/ui/Button'
import { ConnectionForm } from './ConnectionForm'
import { Loader2, TestTube } from 'lucide-react'

export interface StorageConfigProps {
  storage: StorageConfigType
  onChange: (storage: StorageConfigType) => void
  errors?: Record<string, string>
  isLoading?: boolean
  onTestConnection?: () => Promise<void>
}

const CUSTOM_CONNECTION_VALUE = '__custom__'

/**
 * Validate table name
 */
function validateTableName(name: string): string | undefined {
  if (!name) {
    return 'Table name is required'
  }

  // Must start with letter or underscore
  if (!/^[a-zA-Z_]/.test(name)) {
    return 'Table name must start with a letter or underscore'
  }

  // Only alphanumeric and underscores
  if (!/^[a-zA-Z0-9_]+$/.test(name)) {
    return 'Table name can only contain letters, numbers, and underscores'
  }

  // Length validation (max 63 chars for PostgreSQL, but we'll be more lenient)
  if (name.length > 63) {
    return 'Table name must be 63 characters or less'
  }

  return undefined
}

export function StorageConfig({
  storage,
  onChange,
  errors = {},
  isLoading = false,
  onTestConnection,
}: StorageConfigProps) {
  const [selectedConnectionId, setSelectedConnectionId] = useState<string | null>(null)
  const [isTestingConnection, setIsTestingConnection] = useState(false)
  const [testError, setTestError] = useState<string | null>(null)
  const [testSuccess, setTestSuccess] = useState(false)

  // Fetch saved connections
  const {
    data: connectionsData,
    isLoading: isLoadingConnections,
  } = useQuery<ConnectionsListResponse>({
    queryKey: ['connections'],
    queryFn: listConnections,
    retry: false,
  })

  // Determine if we're using a saved connection or custom
  const savedConnections = useMemo(() => connectionsData?.connections || [], [connectionsData?.connections])
  const isUsingCustomConnection = selectedConnectionId === CUSTOM_CONNECTION_VALUE || selectedConnectionId === null

  // Build connection selector options
  const connectionOptions: SelectOption[] = useMemo(() => {
    const options: SelectOption[] = [
      { value: CUSTOM_CONNECTION_VALUE, label: 'Custom Connection' },
    ]

    savedConnections.forEach((conn) => {
      options.push({
        value: conn.id,
        label: `${conn.name} (${conn.connection.type})`,
      })
    })

    return options
  }, [savedConnections])

  // Initialize selected connection based on current storage connection
  useEffect(() => {
    if (selectedConnectionId === null && storage.connection) {
      // Try to find a matching saved connection
      const matchingConnection = savedConnections.find(
        (conn) => JSON.stringify(conn.connection) === JSON.stringify(storage.connection)
      )

      if (matchingConnection) {
        setSelectedConnectionId(matchingConnection.id)
      } else {
        setSelectedConnectionId(CUSTOM_CONNECTION_VALUE)
      }
    }
  }, [storage.connection, savedConnections, selectedConnectionId])

  // Handle connection selection change
  const handleConnectionSelect = (value: string) => {
    setSelectedConnectionId(value)
    setTestError(null)
    setTestSuccess(false)

    if (value === CUSTOM_CONNECTION_VALUE) {
      // Keep current connection if it exists, otherwise create a new one
      if (!storage.connection || !storage.connection.type) {
        onChange({
          ...storage,
          connection: {
            type: 'postgres',
            database: '',
          },
        })
      }
    } else {
      // Use saved connection
      const selectedConnection = savedConnections.find((conn) => conn.id === value)
      if (selectedConnection) {
        onChange({
          ...storage,
          connection: selectedConnection.connection,
        })
      }
    }
  }

  // Handle custom connection change
  const handleConnectionChange = (connection: ConnectionConfig) => {
    onChange({
      ...storage,
      connection,
    })
    setTestError(null)
    setTestSuccess(false)
  }

  // Handle table name changes
  const handleResultsTableChange = (value: string) => {
    onChange({
      ...storage,
      results_table: value || undefined,
    })
  }

  const handleRunsTableChange = (value: string) => {
    onChange({
      ...storage,
      runs_table: value || undefined,
    })
  }

  // Handle create_tables toggle
  const handleCreateTablesChange = (checked: boolean) => {
    onChange({
      ...storage,
      create_tables: checked,
    })
  }

  // Handle connection test
  const handleTestConnection = async () => {
    if (!storage.connection) {
      setTestError('Connection configuration is required')
      return
    }

    setIsTestingConnection(true)
    setTestError(null)
    setTestSuccess(false)

    try {
      await testConnection(storage.connection)
      setTestSuccess(true)
      setTestError(null)
      
      if (onTestConnection) {
        await onTestConnection()
      }
    } catch (error) {
      if (error instanceof ConnectionTestError) {
        setTestError(error.connectionError || error.message)
      } else if (error instanceof Error) {
        setTestError(error.message)
      } else {
        setTestError('Failed to test connection')
      }
      setTestSuccess(false)
    } finally {
      setIsTestingConnection(false)
    }
  }

  // Validate table names
  const resultsTableError = storage.results_table
    ? validateTableName(storage.results_table)
    : undefined
  const runsTableError = storage.runs_table
    ? validateTableName(storage.runs_table)
    : undefined

  return (
    <div className="space-y-6">
      {/* Connection Selector */}
      <FormField
        label="Storage Database Connection"
        required
        error={errors.connection || (testError ? undefined : errors['storage.connection'])}
        helperText="Select a saved connection or configure a custom connection"
      >
        <Select
          options={connectionOptions}
          value={selectedConnectionId || CUSTOM_CONNECTION_VALUE}
          onChange={handleConnectionSelect}
          disabled={isLoading || isLoadingConnections}
          loading={isLoadingConnections}
          placeholder="Select connection..."
        />
      </FormField>

      {/* Custom Connection Form */}
      {isUsingCustomConnection && (
        <div className="pl-4 border-l-2 border-surface-700/50">
          <ConnectionForm
            connection={storage.connection || { type: 'postgres', database: '' }}
            onChange={handleConnectionChange}
            errors={errors}
          />
        </div>
      )}

      {/* Connection Test */}
      <div className="flex items-start gap-4">
        <Button
          type="button"
          variant="secondary"
          onClick={handleTestConnection}
          disabled={isLoading || isTestingConnection || !storage.connection}
        >
          {isTestingConnection ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Testing...
            </>
          ) : (
            <>
              <TestTube className="w-4 h-4 mr-2" />
              Test Connection
            </>
          )}
        </Button>

        {testSuccess && (
          <div className="flex items-center gap-2 text-sm text-emerald-400">
            <span className="font-medium">Connection successful!</span>
          </div>
        )}

        {testError && (
          <div className="flex-1">
            <p className="text-sm text-rose-400 font-medium">Connection test failed</p>
            <p className="text-sm text-rose-300 mt-1">{testError}</p>
          </div>
        )}
      </div>

      {/* Table Names */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <FormField
          label="Results Table Name"
          required
          error={errors.results_table || resultsTableError}
          helperText="Table name for storing profiling results (default: baselinr_results)"
        >
          <Input
            value={storage.results_table || ''}
            onChange={(e) => handleResultsTableChange(e.target.value)}
            placeholder="baselinr_results"
            error={errors.results_table || resultsTableError}
            disabled={isLoading}
          />
        </FormField>

        <FormField
          label="Runs Table Name"
          required
          error={errors.runs_table || runsTableError}
          helperText="Table name for storing run metadata (default: baselinr_runs)"
        >
          <Input
            value={storage.runs_table || ''}
            onChange={(e) => handleRunsTableChange(e.target.value)}
            placeholder="baselinr_runs"
            error={errors.runs_table || runsTableError}
            disabled={isLoading}
          />
        </FormField>
      </div>

      {/* Create Tables Toggle */}
      <FormField
        label="Auto-create Tables"
        helperText="Automatically create tables if they don't exist"
      >
        <Toggle
          checked={storage.create_tables ?? true}
          onChange={handleCreateTablesChange}
          disabled={isLoading}
          label="Create tables automatically if they don't exist"
        />
      </FormField>
    </div>
  )
}

export default StorageConfig

