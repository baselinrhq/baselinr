'use client'

import { useState, useEffect } from 'react'
import { Database, CheckCircle, XCircle } from 'lucide-react'
import { ConnectionConfig, DatabaseType } from '@/types/config'
import { SavedConnection } from '@/types/connection'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { FormField } from '@/components/ui/FormField'
import { ConnectionForm } from './ConnectionForm'
import { testConnection, ConnectionTestError } from '@/lib/api/config'

export interface ConnectionWizardProps {
  isOpen: boolean
  onClose: () => void
  onSave: (connection: SavedConnection) => void
  initialConnection?: ConnectionConfig
  connectionId?: string
}

const DATABASE_TYPES: Array<{
  value: DatabaseType
  label: string
  description: string
}> = [
  {
    value: 'postgres',
    label: 'PostgreSQL',
    description: 'Open-source relational database',
  },
  {
    value: 'mysql',
    label: 'MySQL',
    description: 'Popular open-source database',
  },
  {
    value: 'redshift',
    label: 'Amazon Redshift',
    description: 'AWS data warehouse',
  },
  {
    value: 'snowflake',
    label: 'Snowflake',
    description: 'Cloud data platform',
  },
  {
    value: 'bigquery',
    label: 'Google BigQuery',
    description: 'Google cloud data warehouse',
  },
  {
    value: 'sqlite',
    label: 'SQLite',
    description: 'Lightweight file-based database',
  },
]

type TestResult = {
  success: boolean
  message?: string
  error?: string
} | null

export function ConnectionWizard({
  isOpen,
  onClose,
  onSave,
  initialConnection,
  connectionId,
}: ConnectionWizardProps) {
  const [currentStep, setCurrentStep] = useState(1)
  const [connection, setConnection] = useState<ConnectionConfig>(() => {
    if (initialConnection) {
      return initialConnection
    }
    return {
      type: 'postgres',
      database: '',
    }
  })
  const [connectionName, setConnectionName] = useState('')
  const [testResult, setTestResult] = useState<TestResult>(null)
  const [isTesting, setIsTesting] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  const isEditMode = !!connectionId

  // Reset state when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      if (initialConnection) {
        setConnection(initialConnection)
        setCurrentStep(2) // Skip type selection in edit mode
      } else {
        setConnection({
          type: 'postgres',
          database: '',
        })
        setCurrentStep(1)
      }
      setConnectionName('')
      setTestResult(null)
      setErrors({})
    }
  }, [isOpen, initialConnection, connectionId])

  const validateStep1 = (): boolean => {
    if (!connection.type) {
      setErrors({ type: 'Please select a database type' })
      return false
    }
    setErrors({})
    return true
  }

  const validateStep2 = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!connection.database) {
      newErrors.database = 'Database is required'
    }

    // Type-specific validation
    if (connection.type === 'postgres' || connection.type === 'mysql' || connection.type === 'redshift') {
      if (!connection.host) {
        newErrors.host = 'Host is required'
      }
      if (!connection.port) {
        newErrors.port = 'Port is required'
      }
    } else if (connection.type === 'snowflake') {
      if (!connection.account) {
        newErrors.account = 'Account is required'
      }
      if (!connection.username) {
        newErrors.username = 'Username is required'
      }
      if (!connection.password) {
        newErrors.password = 'Password is required'
      }
    } else if (connection.type === 'bigquery') {
      if (!connection.extra_params?.credentials_path) {
        newErrors.credentials_path = 'Credentials path is required'
      }
    } else if (connection.type === 'sqlite') {
      if (!connection.filepath) {
        newErrors.filepath = 'File path is required'
      }
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleTestConnection = async () => {
    setIsTesting(true)
    setTestResult(null)
    setErrors({})

    try {
      const result = await testConnection(connection)
      setTestResult({
        success: true,
        message: result.message || 'Connection test successful',
      })
    } catch (error) {
      // Handle ConnectionTestError or regular Error
      // Check both instanceof and name property for compatibility with mocks
      const isConnectionTestError = 
        error instanceof ConnectionTestError ||
        (error && typeof error === 'object' && 'name' in error && error.name === 'ConnectionTestError')
      
      if (isConnectionTestError) {
        const connError = error as ConnectionTestError
        const errorMessage = connError.message || 'Connection test failed'
        const isNotFound = errorMessage.includes('Not Found') || errorMessage.includes('404')
        
        setTestResult({
          success: false,
          message: isNotFound 
            ? 'Backend API endpoint not available'
            : connError.message,
          error: isNotFound
            ? 'The test connection endpoint (/api/config/test-connection) is not yet implemented. This requires Plan 2 backend implementation.'
            : connError.connectionError,
        })
      } else {
        const errorMessage = error instanceof Error ? error.message : 'Connection test failed'
        const isNotFound = errorMessage.includes('Not Found') || errorMessage.includes('404')
        
        setTestResult({
          success: false,
          message: isNotFound
            ? 'Backend API endpoint not available'
            : errorMessage,
          error: isNotFound
            ? 'The test connection endpoint is not yet implemented. This requires Plan 2 backend implementation.'
            : undefined,
        })
      }
    } finally {
      setIsTesting(false)
    }
  }

  const handleSave = async () => {
    if (!connectionName.trim()) {
      setErrors({ name: 'Connection name is required' })
      return
    }

    setIsSaving(true)
    try {
      // The actual save will be handled by the parent component
      // We create a mock SavedConnection for the callback
      const savedConnection: SavedConnection = {
        id: connectionId || 'new',
        name: connectionName,
        connection,
        created_at: new Date().toISOString(),
        is_active: true,
      }
      onSave(savedConnection)
      handleClose()
    } catch (error) {
      setErrors({
        save: error instanceof Error ? error.message : 'Failed to save connection',
      })
    } finally {
      setIsSaving(false)
    }
  }

  const handleNext = () => {
    if (currentStep === 1) {
      if (validateStep1()) {
        setCurrentStep(2)
      }
    } else if (currentStep === 2) {
      if (validateStep2()) {
        setCurrentStep(3)
      }
    } else if (currentStep === 3) {
      if (testResult?.success) {
        setCurrentStep(4)
      }
    }
  }

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
      setTestResult(null)
    }
  }

  const handleClose = () => {
    setCurrentStep(1)
    setConnection({
      type: 'postgres',
      database: '',
    })
    setConnectionName('')
    setTestResult(null)
    setErrors({})
    onClose()
  }

  const getStepTitle = () => {
    switch (currentStep) {
      case 1:
        return 'Select Database Type'
      case 2:
        return 'Connection Details'
      case 3:
        return 'Test Connection'
      case 4:
        return 'Save Connection'
      default:
        return 'Connection Wizard'
    }
  }

  const renderStep1 = () => (
    <div className="space-y-4">
      <p className="text-sm text-gray-600 mb-6">
        Choose the type of database you want to connect to.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {DATABASE_TYPES.map((dbType) => (
          <button
            key={dbType.value}
            type="button"
            onClick={() => {
              setConnection({
                type: dbType.value,
                database: '',
              })
              setErrors({})
            }}
            className={`
              p-4 border-2 rounded-lg text-left transition-all
              hover:border-primary-500 hover:bg-primary-50
              ${connection.type === dbType.value
                ? 'border-primary-500 bg-primary-50'
                : 'border-gray-200'
              }
            `}
          >
            <div className="flex items-start gap-3">
              <Database className="w-5 h-5 text-primary-600 mt-0.5" />
              <div className="flex-1">
                <div className="font-medium text-gray-900">{dbType.label}</div>
                <div className="text-sm text-gray-500 mt-1">
                  {dbType.description}
                </div>
              </div>
              {connection.type === dbType.value && (
                <CheckCircle className="w-5 h-5 text-primary-600" />
              )}
            </div>
          </button>
        ))}
      </div>
      {errors.type && (
        <p className="text-sm text-red-600 mt-2">{errors.type}</p>
      )}
    </div>
  )

  const renderStep2 = () => (
    <div>
      <ConnectionForm
        connection={connection}
        onChange={setConnection}
        errors={errors}
        databaseType={connection.type}
      />
    </div>
  )

  const renderStep3 = () => (
    <div className="space-y-4">
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-medium text-gray-900 mb-2">Connection Summary</h4>
        <div className="text-sm text-gray-600 space-y-1">
          <div><strong>Type:</strong> {connection.type}</div>
          {connection.host && <div><strong>Host:</strong> {connection.host}</div>}
          {connection.port && <div><strong>Port:</strong> {connection.port}</div>}
          {connection.database && <div><strong>Database:</strong> {connection.database}</div>}
          {connection.account && <div><strong>Account:</strong> {connection.account}</div>}
          {connection.filepath && <div><strong>File Path:</strong> {connection.filepath}</div>}
        </div>
      </div>

      <div className="flex items-center gap-4">
        <Button
          onClick={handleTestConnection}
          loading={isTesting}
          disabled={isTesting}
        >
          Test Connection
        </Button>
      </div>

      {testResult && (
        <div
          className={`
            p-4 rounded-lg flex items-start gap-3
            ${testResult.success
              ? 'bg-green-50 border border-green-200'
              : 'bg-red-50 border border-red-200'
            }
          `}
        >
          {testResult.success ? (
            <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
          ) : (
            <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          )}
          <div className="flex-1">
            <div
              className={`font-medium ${
                testResult.success ? 'text-green-900' : 'text-red-900'
              }`}
            >
              {testResult.success ? 'Connection Successful' : 'Connection Failed'}
            </div>
            {testResult.message && (
              <div
                className={`text-sm mt-1 ${
                  testResult.success ? 'text-green-700' : 'text-red-700'
                }`}
              >
                {testResult.message}
              </div>
            )}
            {testResult.error && (
              <div className="text-sm text-red-600 mt-1 font-mono">
                {testResult.error}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )

  const renderStep4 = () => (
    <div className="space-y-4">
      <FormField
        label="Connection Name"
        required
        error={errors.name}
        helperText="Give this connection a memorable name"
      >
        <Input
          value={connectionName}
          onChange={(e) => {
            setConnectionName(e.target.value)
            setErrors({ ...errors, name: '' })
          }}
          placeholder="My Production Database"
          error={errors.name}
        />
      </FormField>

      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-medium text-gray-900 mb-3">Connection Details</h4>
        <div className="text-sm text-gray-600 space-y-1">
          <div><strong>Type:</strong> {connection.type}</div>
          {connection.host && <div><strong>Host:</strong> {connection.host}</div>}
          {connection.port && <div><strong>Port:</strong> {connection.port}</div>}
          {connection.database && <div><strong>Database:</strong> {connection.database}</div>}
          {connection.account && <div><strong>Account:</strong> {connection.account}</div>}
          {connection.filepath && <div><strong>File Path:</strong> {connection.filepath}</div>}
        </div>
      </div>

      {errors.save && (
        <p className="text-sm text-red-600">{errors.save}</p>
      )}
    </div>
  )

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return renderStep1()
      case 2:
        return renderStep2()
      case 3:
        return renderStep3()
      case 4:
        return renderStep4()
      default:
        return null
    }
  }

  const renderFooter = () => {
    const canGoNext =
      (currentStep === 1 && connection.type) ||
      (currentStep === 2 && Object.keys(errors).length === 0) ||
      (currentStep === 3 && testResult?.success) ||
      currentStep === 4

    return (
      <div className="flex items-center justify-between">
        <div>
          {currentStep > 1 && (
            <Button variant="outline" onClick={handleBack}>
              Back
            </Button>
          )}
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          {currentStep < 4 ? (
            <Button onClick={handleNext} disabled={!canGoNext}>
              Next
            </Button>
          ) : (
            <Button onClick={handleSave} loading={isSaving}>
              {isEditMode ? 'Update Connection' : 'Save Connection'}
            </Button>
          )}
        </div>
      </div>
    )
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={getStepTitle()}
      size="lg"
      footer={renderFooter()}
    >
      {/* Step indicator */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          {[1, 2, 3, 4].map((step) => (
            <div key={step} className="flex items-center flex-1">
              <div className="flex flex-col items-center flex-1">
                <div
                  className={`
                    w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                    ${step <= currentStep
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-200 text-gray-600'
                    }
                  `}
                >
                  {step < currentStep ? '✓' : step}
                </div>
                <div className="text-xs text-gray-500 mt-1 text-center">
                  {step === 1 && 'Type'}
                  {step === 2 && 'Details'}
                  {step === 3 && 'Test'}
                  {step === 4 && 'Save'}
                </div>
              </div>
              {step < 4 && (
                <div
                  className={`
                    h-0.5 flex-1 mx-2
                    ${step < currentStep ? 'bg-primary-600' : 'bg-gray-200'}
                  `}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Step content */}
      <div className="min-h-[300px]">
        {renderStepContent()}
      </div>
    </Modal>
  )
}

export default ConnectionWizard

