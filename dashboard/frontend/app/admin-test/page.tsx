'use client'

import {
  Button,
  Card,
  CardHeader,
  CardBody,
  CardTitle,
  CardDescription,
  Input,
  FormField,
  Badge,
  LoadingSpinner,
  Tabs,
} from '@/components/ui'
import { useState } from 'react'
import { CheckCircle, XCircle, AlertCircle, ExternalLink } from 'lucide-react'
import Link from 'next/link'
import {
  fetchConfig,
  saveConfig,
  validateConfig,
  testConnection,
  getConfigHistory,
  loadConfigVersion,
  ConfigError,
  ValidationError,
  ConnectionTestError,
} from '@/lib/api/config'
import type {
  BaselinrConfig,
  ConnectionConfig,
  ConfigResponse,
  ConfigValidationResponse,
  ConnectionTestResponse,
  ConfigHistoryResponse,
  ConfigVersionResponse,
} from '@/types/config'

export default function AdminTestPage() {
  const [activeTab, setActiveTab] = useState('config-api')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Config API states
  const [currentConfig, setCurrentConfig] = useState<ConfigResponse | null>(null)
  const [configJson, setConfigJson] = useState('')
  const [validationResult, setValidationResult] = useState<ConfigValidationResponse | null>(null)
  const [connectionTestResult, setConnectionTestResult] = useState<ConnectionTestResponse | null>(null)
  const [configHistory, setConfigHistory] = useState<ConfigHistoryResponse | null>(null)
  const [selectedVersionId, setSelectedVersionId] = useState('')
  const [loadedVersion, setLoadedVersion] = useState<ConfigVersionResponse | null>(null)

  // Connection test form state
  const [connectionForm, setConnectionForm] = useState<ConnectionConfig>({
    type: 'postgres',
    host: 'localhost',
    port: 5432,
    database: '',
    username: '',
    password: '',
    schema: 'public',
  })

  const clearMessages = () => {
    setError(null)
    setSuccess(null)
  }

  const handleFetchConfig = async () => {
    clearMessages()
    setLoading(true)
    setCurrentConfig(null)
    try {
      const result = await fetchConfig()
      setCurrentConfig(result)
      setConfigJson(JSON.stringify(result.config, null, 2))
      setSuccess('Configuration fetched successfully')
    } catch (err) {
      const message = err instanceof ConfigError ? err.message : 'Failed to fetch configuration'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveConfig = async () => {
    clearMessages()
    if (!configJson.trim()) {
      setError('Please enter a configuration JSON')
      return
    }

    setLoading(true)
    try {
      const config: BaselinrConfig = JSON.parse(configJson)
      const result = await saveConfig(config)
      setCurrentConfig(result)
      setConfigJson(JSON.stringify(result.config, null, 2))
      setSuccess('Configuration saved successfully')
    } catch (err) {
      if (err instanceof ValidationError) {
        setError(`Validation failed: ${err.message}${err.validationErrors ? '\n' + err.validationErrors.join('\n') : ''}`)
      } else if (err instanceof ConfigError) {
        setError(err.message)
      } else if (err instanceof SyntaxError) {
        setError(`Invalid JSON: ${err.message}`)
      } else {
        setError('Failed to save configuration')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleValidateConfig = async () => {
    clearMessages()
    if (!configJson.trim()) {
      setError('Please enter a configuration JSON')
      return
    }

    setLoading(true)
    setValidationResult(null)
    try {
      const config: Partial<BaselinrConfig> = JSON.parse(configJson)
      const result = await validateConfig(config)
      setValidationResult(result)
      if (result.valid) {
        setSuccess('Configuration is valid')
      } else {
        setError(`Validation failed: ${result.errors?.join(', ') || 'Unknown errors'}`)
      }
    } catch (err) {
      if (err instanceof ConfigError) {
        setError(err.message)
      } else if (err instanceof SyntaxError) {
        setError(`Invalid JSON: ${err.message}`)
      } else {
        setError('Failed to validate configuration')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleTestConnection = async () => {
    clearMessages()
    setLoading(true)
    setConnectionTestResult(null)
    try {
      const result = await testConnection(connectionForm)
      setConnectionTestResult(result)
      setSuccess('Connection test successful')
    } catch (err) {
      if (err instanceof ConnectionTestError) {
        setError(`Connection test failed: ${err.message}${err.connectionError ? '\n' + err.connectionError : ''}`)
        setConnectionTestResult({
          success: false,
          error: err.connectionError || err.message,
        })
      } else if (err instanceof ConfigError) {
        setError(err.message)
      } else {
        setError('Failed to test connection')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleGetHistory = async () => {
    clearMessages()
    setLoading(true)
    setConfigHistory(null)
    try {
      const result = await getConfigHistory()
      setConfigHistory(result)
      setSuccess(`Found ${result.versions?.length || 0} configuration versions`)
    } catch (err) {
      const message = err instanceof ConfigError ? err.message : 'Failed to fetch configuration history'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const handleLoadVersion = async () => {
    clearMessages()
    if (!selectedVersionId.trim()) {
      setError('Please enter a version ID')
      return
    }

    setLoading(true)
    setLoadedVersion(null)
    try {
      const result = await loadConfigVersion(selectedVersionId)
      setLoadedVersion(result)
      setConfigJson(JSON.stringify(result.config, null, 2))
      setSuccess(`Version ${result.version_id} loaded successfully`)
    } catch (err) {
      const message = err instanceof ConfigError ? err.message : 'Failed to load configuration version'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto p-8 space-y-8 max-w-6xl">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Admin Test Page</h1>
        <p className="text-gray-600">Test UI components and backend API endpoints</p>
      </div>

      {/* Navigation Tabs */}
      <Card>
        <CardBody>
          <Tabs
            tabs={[
              { id: 'config-api', label: 'Config API' },
              { id: 'ui-components', label: 'UI Components' },
            ]}
            activeTab={activeTab}
            onChange={setActiveTab}
          />
        </CardBody>
      </Card>

      {/* Config API Testing */}
      {activeTab === 'config-api' && (
        <div className="space-y-6">
          {/* Status Messages */}
          {(error || success) && (
            <Card>
              <CardBody>
                {error && (
                  <div className="flex items-center gap-2 text-red-600">
                    <XCircle className="w-5 h-5" />
                    <pre className="whitespace-pre-wrap text-sm">{error}</pre>
                  </div>
                )}
                {success && (
                  <div className="flex items-center gap-2 text-green-600">
                    <CheckCircle className="w-5 h-5" />
                    <span>{success}</span>
                  </div>
                )}
              </CardBody>
            </Card>
          )}

          {/* Fetch Config */}
          <Card>
            <CardHeader>
              <CardTitle>Fetch Current Configuration</CardTitle>
              <CardDescription>Get the current Baselinr configuration</CardDescription>
            </CardHeader>
            <CardBody className="space-y-4">
              <Button onClick={handleFetchConfig} disabled={loading}>
                {loading ? <LoadingSpinner size="sm" /> : 'Fetch Config'}
              </Button>
              {currentConfig && (
                <div className="mt-4">
                  <Badge variant="success">Config loaded</Badge>
                  <p className="text-sm text-gray-600 mt-2">
                    Version: {currentConfig.version || 'N/A'} | 
                    Last Modified: {currentConfig.last_modified || 'N/A'}
                  </p>
                </div>
              )}
            </CardBody>
          </Card>

          {/* Save Config */}
          <Card>
            <CardHeader>
              <CardTitle>Save Configuration</CardTitle>
              <CardDescription>Save a new Baselinr configuration</CardDescription>
            </CardHeader>
            <CardBody className="space-y-4">
              <FormField label="Configuration JSON" required>
                <textarea
                  className="w-full h-64 p-3 border border-gray-300 rounded-lg font-mono text-sm"
                  value={configJson}
                  onChange={(e) => setConfigJson(e.target.value)}
                  placeholder='{"environment": "development", "source": {...}, "storage": {...}}'
                />
              </FormField>
              <Button onClick={handleSaveConfig} disabled={loading || !configJson.trim()}>
                {loading ? <LoadingSpinner size="sm" /> : 'Save Config'}
              </Button>
            </CardBody>
          </Card>

          {/* Validate Config */}
          <Card>
            <CardHeader>
              <CardTitle>Validate Configuration</CardTitle>
              <CardDescription>Validate a configuration without saving it</CardDescription>
            </CardHeader>
            <CardBody className="space-y-4">
              <Button onClick={handleValidateConfig} disabled={loading || !configJson.trim()}>
                {loading ? <LoadingSpinner size="sm" /> : 'Validate Config'}
              </Button>
              {validationResult && (
                <div className="mt-4">
                  {validationResult.valid ? (
                    <Badge variant="success">Valid</Badge>
                  ) : (
                    <Badge variant="error">Invalid</Badge>
                  )}
                  {validationResult.errors && validationResult.errors.length > 0 && (
                    <ul className="mt-2 list-disc list-inside text-sm text-red-600">
                      {validationResult.errors.map((err, idx) => (
                        <li key={idx}>{err}</li>
                      ))}
                    </ul>
                  )}
                  {validationResult.warnings && validationResult.warnings.length > 0 && (
                    <ul className="mt-2 list-disc list-inside text-sm text-yellow-600">
                      {validationResult.warnings.map((warn, idx) => (
                        <li key={idx}>{warn}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </CardBody>
          </Card>

          {/* Test Connection */}
          <Card>
            <CardHeader>
              <CardTitle>Test Database Connection</CardTitle>
              <CardDescription>Test a database connection configuration</CardDescription>
            </CardHeader>
            <CardBody className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <FormField label="Database Type" required>
                  <select
                    className="w-full p-2 border border-gray-300 rounded-lg"
                    value={connectionForm.type}
                    onChange={(e) => setConnectionForm({ ...connectionForm, type: e.target.value as any })}
                  >
                    <option value="postgres">PostgreSQL</option>
                    <option value="snowflake">Snowflake</option>
                    <option value="mysql">MySQL</option>
                    <option value="bigquery">BigQuery</option>
                    <option value="redshift">Redshift</option>
                    <option value="sqlite">SQLite</option>
                  </select>
                </FormField>
                <FormField label="Host">
                  <Input
                    value={connectionForm.host || ''}
                    onChange={(e) => setConnectionForm({ ...connectionForm, host: e.target.value })}
                    placeholder="localhost"
                  />
                </FormField>
                <FormField label="Port">
                  <Input
                    type="number"
                    value={connectionForm.port || ''}
                    onChange={(e) => setConnectionForm({ ...connectionForm, port: parseInt(e.target.value) || undefined })}
                    placeholder="5432"
                  />
                </FormField>
                <FormField label="Database" required>
                  <Input
                    value={connectionForm.database}
                    onChange={(e) => setConnectionForm({ ...connectionForm, database: e.target.value })}
                    placeholder="database_name"
                  />
                </FormField>
                <FormField label="Username">
                  <Input
                    value={connectionForm.username || ''}
                    onChange={(e) => setConnectionForm({ ...connectionForm, username: e.target.value })}
                    placeholder="username"
                  />
                </FormField>
                <FormField label="Password">
                  <Input
                    type="password"
                    value={connectionForm.password || ''}
                    onChange={(e) => setConnectionForm({ ...connectionForm, password: e.target.value })}
                    placeholder="password"
                  />
                </FormField>
                <FormField label="Schema">
                  <Input
                    value={connectionForm.schema || ''}
                    onChange={(e) => setConnectionForm({ ...connectionForm, schema: e.target.value })}
                    placeholder="public"
                  />
                </FormField>
              </div>
              <Button onClick={handleTestConnection} disabled={loading || !connectionForm.database}>
                {loading ? <LoadingSpinner size="sm" /> : 'Test Connection'}
              </Button>
              {connectionTestResult && (
                <div className="mt-4">
                  {connectionTestResult.success ? (
                    <div>
                      <Badge variant="success">Connection successful</Badge>
                      {connectionTestResult.connection_time_ms && (
                        <p className="text-sm text-gray-600 mt-2">
                          Connection time: {connectionTestResult.connection_time_ms}ms
                        </p>
                      )}
                    </div>
                  ) : (
                    <div>
                      <Badge variant="error">Connection failed</Badge>
                      {connectionTestResult.error && (
                        <p className="text-sm text-red-600 mt-2">{connectionTestResult.error}</p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </CardBody>
          </Card>

          {/* Config History */}
          <Card>
            <CardHeader>
              <CardTitle>Configuration History</CardTitle>
              <CardDescription>View and load previous configuration versions</CardDescription>
            </CardHeader>
            <CardBody className="space-y-4">
              <div className="flex gap-4">
                <Button onClick={handleGetHistory} disabled={loading}>
                  {loading ? <LoadingSpinner size="sm" /> : 'Get History'}
                </Button>
              </div>
              {configHistory && (
                <div className="mt-4">
                  <p className="text-sm text-gray-600 mb-2">
                    Found {configHistory.versions?.length || 0} versions
                  </p>
                  {configHistory.versions && configHistory.versions.length > 0 && (
                    <div className="space-y-2">
                      {configHistory.versions.map((version) => (
                        <div
                          key={version.version_id}
                          className="p-3 border border-gray-200 rounded-lg flex items-center justify-between"
                        >
                          <div>
                            <p className="font-medium">{version.version_id}</p>
                            <p className="text-sm text-gray-600">
                              {version.created_at} {version.is_current && '(Current)'}
                            </p>
                            {version.description && (
                              <p className="text-sm text-gray-500">{version.description}</p>
                            )}
                          </div>
                          <Button
                            size="sm"
                            onClick={() => {
                              setSelectedVersionId(version.version_id)
                              handleLoadVersion()
                            }}
                            disabled={loading}
                          >
                            Load
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </CardBody>
          </Card>

          {/* Load Version */}
          <Card>
            <CardHeader>
              <CardTitle>Load Configuration Version</CardTitle>
              <CardDescription>Load a specific configuration version by ID</CardDescription>
            </CardHeader>
            <CardBody className="space-y-4">
              <FormField label="Version ID" required>
                <Input
                  value={selectedVersionId}
                  onChange={(e) => setSelectedVersionId(e.target.value)}
                  placeholder="version-id"
                />
              </FormField>
              <Button onClick={handleLoadVersion} disabled={loading || !selectedVersionId.trim()}>
                {loading ? <LoadingSpinner size="sm" /> : 'Load Version'}
              </Button>
              {loadedVersion && (
                <div className="mt-4">
                  <Badge variant="success">Version loaded</Badge>
                  <p className="text-sm text-gray-600 mt-2">
                    Version: {loadedVersion.version_id} | Created: {loadedVersion.created_at}
                  </p>
                </div>
              )}
            </CardBody>
          </Card>
        </div>
      )}

      {/* UI Components Link */}
      {activeTab === 'ui-components' && (
        <Card>
          <CardHeader>
            <CardTitle>UI Component Testing</CardTitle>
            <CardDescription>Test all UI components from the shared component library</CardDescription>
          </CardHeader>
          <CardBody>
            <Link href="/ui-test">
              <Button variant="primary">
                Go to UI Test Page
                <ExternalLink className="w-4 h-4 ml-2" />
              </Button>
            </Link>
          </CardBody>
        </Card>
      )}
    </div>
  )
}

