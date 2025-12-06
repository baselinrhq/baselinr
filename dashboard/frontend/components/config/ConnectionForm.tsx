'use client'

import { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { ConnectionConfig, DatabaseType } from '@/types/config'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'

export interface ConnectionFormProps {
  connection: ConnectionConfig
  onChange: (config: ConnectionConfig) => void
  errors?: Record<string, string>
  databaseType?: DatabaseType
}

const DATABASE_TYPES: Array<{ value: DatabaseType; label: string }> = [
  { value: 'postgres', label: 'PostgreSQL' },
  { value: 'mysql', label: 'MySQL' },
  { value: 'redshift', label: 'Amazon Redshift' },
  { value: 'snowflake', label: 'Snowflake' },
  { value: 'bigquery', label: 'Google BigQuery' },
  { value: 'sqlite', label: 'SQLite' },
]

export function ConnectionForm({
  connection,
  onChange,
  errors = {},
  databaseType,
}: ConnectionFormProps) {
  const [showPassword, setShowPassword] = useState(false)

  const handleChange = (field: keyof ConnectionConfig, value: string | number | null | undefined) => {
    onChange({
      ...connection,
      [field]: value,
    })
  }

  const handleExtraParamsChange = (key: string, value: string | number | null | undefined) => {
    onChange({
      ...connection,
      extra_params: {
        ...connection.extra_params,
        [key]: value,
      },
    })
  }

  const isTypeLocked = databaseType !== undefined
  const currentType = databaseType || connection.type

  // Common fields for PostgreSQL/MySQL/Redshift
  const renderStandardFields = () => (
    <>
      <FormField
        label="Host"
        required
        error={errors.host}
      >
        <Input
          value={connection.host || ''}
          onChange={(e) => handleChange('host', e.target.value)}
          placeholder="localhost"
          error={errors.host}
        />
      </FormField>

      <FormField
        label="Port"
        required
        error={errors.port}
        helperText={
          currentType === 'postgres' ? 'Default: 5432' :
          currentType === 'mysql' ? 'Default: 3306' :
          currentType === 'redshift' ? 'Default: 5439' : undefined
        }
      >
        <Input
          type="number"
          value={connection.port?.toString() || ''}
          onChange={(e) => handleChange('port', e.target.value ? parseInt(e.target.value, 10) : null)}
          placeholder={
            currentType === 'postgres' ? '5432' :
            currentType === 'mysql' ? '3306' :
            currentType === 'redshift' ? '5439' : ''
          }
          error={errors.port}
        />
      </FormField>

      <FormField
        label="Database"
        required
        error={errors.database}
      >
        <Input
          value={connection.database || ''}
          onChange={(e) => handleChange('database', e.target.value)}
          placeholder="database_name"
          error={errors.database}
        />
      </FormField>

      <FormField
        label="Username"
        error={errors.username}
      >
        <Input
          value={connection.username || ''}
          onChange={(e) => handleChange('username', e.target.value)}
          placeholder="username"
          error={errors.username}
        />
      </FormField>

      <FormField
        label="Password"
        error={errors.password}
      >
        <Input
          type={showPassword ? 'text' : 'password'}
          value={connection.password || ''}
          onChange={(e) => handleChange('password', e.target.value)}
          placeholder="password"
          error={errors.password}
          rightIcon={
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="text-gray-400 hover:text-gray-600"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          }
        />
      </FormField>

      <FormField
        label="Schema"
        error={errors.schema}
        helperText={currentType === 'postgres' ? 'Default: public' : undefined}
      >
        <Input
          value={connection.schema || ''}
          onChange={(e) => handleChange('schema', e.target.value)}
          placeholder={currentType === 'postgres' ? 'public' : 'schema_name'}
          error={errors.schema}
        />
      </FormField>
    </>
  )

  // Snowflake-specific fields
  const renderSnowflakeFields = () => (
    <>
      <FormField
        label="Account"
        required
        error={errors.account}
      >
        <Input
          value={connection.account || ''}
          onChange={(e) => handleChange('account', e.target.value)}
          placeholder="account.region.cloud"
          error={errors.account}
        />
      </FormField>

      <FormField
        label="Warehouse"
        error={errors.warehouse}
      >
        <Input
          value={connection.warehouse || ''}
          onChange={(e) => handleChange('warehouse', e.target.value)}
          placeholder="warehouse_name"
          error={errors.warehouse}
        />
      </FormField>

      <FormField
        label="Database"
        required
        error={errors.database}
      >
        <Input
          value={connection.database || ''}
          onChange={(e) => handleChange('database', e.target.value)}
          placeholder="database_name"
          error={errors.database}
        />
      </FormField>

      <FormField
        label="Username"
        required
        error={errors.username}
      >
        <Input
          value={connection.username || ''}
          onChange={(e) => handleChange('username', e.target.value)}
          placeholder="username"
          error={errors.username}
        />
      </FormField>

      <FormField
        label="Password"
        required
        error={errors.password}
      >
        <Input
          type={showPassword ? 'text' : 'password'}
          value={connection.password || ''}
          onChange={(e) => handleChange('password', e.target.value)}
          placeholder="password"
          error={errors.password}
          rightIcon={
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="text-gray-400 hover:text-gray-600"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          }
        />
      </FormField>

      <FormField
        label="Role"
        error={errors.role}
      >
        <Input
          value={connection.role || ''}
          onChange={(e) => handleChange('role', e.target.value)}
          placeholder="role_name"
          error={errors.role}
        />
      </FormField>

      <FormField
        label="Schema"
        error={errors.schema}
      >
        <Input
          value={connection.schema || ''}
          onChange={(e) => handleChange('schema', e.target.value)}
          placeholder="schema_name"
          error={errors.schema}
        />
      </FormField>
    </>
  )

  // BigQuery-specific fields
  const renderBigQueryFields = () => (
    <>
      <FormField
        label="Project"
        required
        error={errors.database}
        helperText="Project ID (stored as database)"
      >
        <Input
          value={connection.database || ''}
          onChange={(e) => handleChange('database', e.target.value)}
          placeholder="project-id"
          error={errors.database}
        />
      </FormField>

      <FormField
        label="Credentials Path"
        required
        error={errors.credentials_path}
        helperText="Path to service account JSON file"
      >
        <Input
          value={connection.extra_params?.credentials_path || ''}
          onChange={(e) => handleExtraParamsChange('credentials_path', e.target.value)}
          placeholder="/path/to/credentials.json"
          error={errors.credentials_path}
        />
      </FormField>

      <FormField
        label="Dataset"
        error={errors.schema}
        helperText="Dataset name (stored as schema)"
      >
        <Input
          value={connection.schema || ''}
          onChange={(e) => handleChange('schema', e.target.value)}
          placeholder="dataset_name"
          error={errors.schema}
        />
      </FormField>
    </>
  )

  // SQLite-specific fields
  const renderSQLiteFields = () => (
    <>
      <FormField
        label="File Path"
        required
        error={errors.filepath}
      >
        <Input
          value={connection.filepath || ''}
          onChange={(e) => handleChange('filepath', e.target.value)}
          placeholder="/path/to/database.db"
          error={errors.filepath}
        />
      </FormField>
    </>
  )

  return (
    <div className="space-y-4">
      {!isTypeLocked && (
        <FormField
          label="Database Type"
          required
          error={errors.type}
        >
          <Select
            options={DATABASE_TYPES}
            value={connection.type}
            onChange={(value) => {
              // Reset connection when type changes
              const newConnection: ConnectionConfig = {
                type: value as DatabaseType,
                database: '',
              }
              onChange(newConnection)
            }}
            error={errors.type}
          />
        </FormField>
      )}

      {currentType === 'postgres' || currentType === 'mysql' || currentType === 'redshift' ? (
        renderStandardFields()
      ) : currentType === 'snowflake' ? (
        renderSnowflakeFields()
      ) : currentType === 'bigquery' ? (
        renderBigQueryFields()
      ) : currentType === 'sqlite' ? (
        renderSQLiteFields()
      ) : null}
    </div>
  )
}

export default ConnectionForm

