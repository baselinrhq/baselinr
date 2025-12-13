'use client'

import { CheckCircle, Download, Upload, TestTube } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { useConfig } from '@/hooks/useConfig'
import { useState } from 'react'

export interface ConfigQuickActionsProps {
  onValidate?: () => void
}

export function ConfigQuickActions({ onValidate }: ConfigQuickActionsProps) {
  const {
    currentConfig,
    validateConfig: validateConfigHook,
    validationErrors,
    validationWarnings,
  } = useConfig()
  const [isValidating, setIsValidating] = useState(false)
  const [validationResult, setValidationResult] = useState<{
    valid: boolean
    message: string
  } | null>(null)

  const handleValidate = async () => {
    if (!currentConfig) {
      alert('No configuration loaded')
      return
    }

    setIsValidating(true)
    setValidationResult(null)

    try {
      // Use the hook's validateConfig which uses the store
      const isValid = await validateConfigHook()
      let message = 'Configuration is valid'
      if (!isValid) {
        if (validationErrors && validationErrors.length > 0) {
          message = `Validation failed: ${validationErrors.join(', ')}`
        } else {
          message = 'Validation failed. Check the configuration for errors.'
        }
      } else if (validationWarnings && validationWarnings.length > 0) {
        message = `Configuration is valid with warnings: ${validationWarnings.join(', ')}`
      }
      setValidationResult({
        valid: isValid,
        message,
      })
      if (onValidate) {
        onValidate()
      }
    } catch (error) {
      setValidationResult({
        valid: false,
        message: error instanceof Error ? error.message : 'Validation failed',
      })
    } finally {
      setIsValidating(false)
    }
  }

  const handleExport = () => {
    if (!currentConfig) {
      alert('No configuration loaded')
      return
    }

    const dataStr = JSON.stringify(currentConfig, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'baselinr-config.json'
    link.click()
    URL.revokeObjectURL(url)
  }

  const handleImport = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json,.yaml,.yml'
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return

      const reader = new FileReader()
      reader.onload = (event) => {
        try {
          const content = event.target?.result as string
          JSON.parse(content) // Parse to validate, but don't use the result yet
          // TODO: Implement import logic (would need to save via API)
          alert('Import functionality requires API integration')
        } catch {
          alert('Failed to parse configuration file')
        }
      }
      reader.readAsText(file)
    }
    input.click()
  }

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Quick Actions</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Button
          variant="secondary"
          onClick={handleValidate}
          disabled={!currentConfig || isValidating}
          icon={<CheckCircle className="w-4 h-4" />}
          fullWidth
        >
          {isValidating ? 'Validating...' : 'Validate Config'}
        </Button>

        <Button
          variant="secondary"
          onClick={handleExport}
          disabled={!currentConfig}
          icon={<Download className="w-4 h-4" />}
          fullWidth
        >
          Export Config
        </Button>

        <Button
          variant="secondary"
          onClick={handleImport}
          icon={<Upload className="w-4 h-4" />}
          fullWidth
        >
          Import Config
        </Button>

        <Button
          variant="secondary"
          onClick={() => {
            // TODO: Implement test all connections
            alert('Test all connections functionality coming soon')
          }}
          icon={<TestTube className="w-4 h-4" />}
          fullWidth
        >
          Test Connections
        </Button>
      </div>

      {validationResult && (
        <div
          className={`mt-4 p-3 rounded-lg ${
            validationResult.valid
              ? 'bg-emerald-500/10 border border-emerald-500/30'
              : 'bg-rose-500/10 border border-rose-500/30'
          }`}
        >
          <p
            className={`text-sm ${
              validationResult.valid ? 'text-emerald-300' : 'text-rose-300'
            }`}
          >
            {validationResult.message}
          </p>
        </div>
      )}
    </Card>
  )
}

export default ConfigQuickActions

