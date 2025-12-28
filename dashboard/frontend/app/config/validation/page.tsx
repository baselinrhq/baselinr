'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useMutation } from '@tanstack/react-query'
import { Save, Loader2, AlertCircle, CheckCircle, Plus, ChevronRight, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Toggle } from '@/components/ui/Toggle'
import { RuleList } from '@/components/validation/RuleList'
import { RuleWizard } from '@/components/validation/RuleWizard'
import { useConfig } from '@/hooks/useConfig'
import { ValidationRuleConfig, ValidationConfig } from '@/types/config'

/**
 * Deep merge utility for merging config updates
 */
function deepMerge(target: Record<string, unknown>, source: Record<string, unknown>): Record<string, unknown> {
  const output = { ...target }
  if (isObject(target) && isObject(source)) {
    Object.keys(source).forEach((key) => {
      if (isObject(source[key])) {
        if (!(key in target)) {
          Object.assign(output, { [key]: source[key] })
        } else {
          output[key] = deepMerge(target[key] as Record<string, unknown>, source[key] as Record<string, unknown>)
        }
      } else {
        Object.assign(output, { [key]: source[key] })
      }
    })
  }
  return output
}

function isObject(item: unknown): boolean {
  return item && typeof item === 'object' && !Array.isArray(item)
}

export default function ValidationPage() {
  const {
    currentConfig,
    modifiedConfig,
    loadConfig,
    updateConfigPath,
    saveConfig,
    isLoading: isConfigLoading,
    error: configError,
    canSave,
  } = useConfig()

  const [saveSuccess, setSaveSuccess] = useState(false)
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({})
  const [hasTriedLoad, setHasTriedLoad] = useState(false)
  const [isWizardOpen, setIsWizardOpen] = useState(false)
  const [editingRule, setEditingRule] = useState<ValidationRuleConfig | undefined>(undefined)
  const [editingIndex, setEditingIndex] = useState<number>(-1)

  // Load config on mount (only once)
  useEffect(() => {
    if (!currentConfig && !hasTriedLoad && !configError) {
      setHasTriedLoad(true)
      loadConfig().catch(() => {
        // Error is handled by useConfig hook
      })
    }
  }, [currentConfig, loadConfig, hasTriedLoad, configError])

  // Get effective config (current + modifications) and extract validation
  const effectiveConfig = currentConfig && modifiedConfig
    ? deepMerge(currentConfig as unknown as Record<string, unknown>, modifiedConfig as unknown as Record<string, unknown>)
    : (currentConfig || {}) as unknown as Record<string, unknown>
  const validation: ValidationConfig | undefined = effectiveConfig?.validation as ValidationConfig | undefined
  const rules: ValidationRuleConfig[] = validation?.rules || []

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async () => {
      setSaveSuccess(false)
      setValidationErrors({})
      await saveConfig()
    },
    onSuccess: () => {
      setSaveSuccess(true)
      // Clear success message after 3 seconds
      setTimeout(() => setSaveSuccess(false), 3000)
    },
    onError: (error) => {
      // Handle validation errors
      if (error instanceof Error && error.message.includes('validation')) {
        setValidationErrors({
          general: error.message,
        })
      } else {
        setValidationErrors({
          general: error instanceof Error ? error.message : 'Failed to save validation configuration',
        })
      }
    },
  })

  // Handle rules change
  const handleRulesChange = (newRules: ValidationRuleConfig[]) => {
    updateConfigPath(['validation', 'rules'], newRules)
  }

  // Handle validation enabled change
  const handleEnabledChange = (enabled: boolean) => {
    updateConfigPath(['validation', 'enabled'], enabled)
  }

  // Handle add rule
  const handleAddRule = () => {
    setEditingRule(undefined)
    setEditingIndex(-1)
    setIsWizardOpen(true)
  }

  // Handle edit rule
  const handleEditRule = (rule: ValidationRuleConfig, index: number) => {
    setEditingRule(rule)
    setEditingIndex(index)
    setIsWizardOpen(true)
  }

  // Handle delete rule
  const handleDeleteRule = (index: number) => {
    if (confirm('Are you sure you want to delete this validation rule?')) {
      const newRules = [...rules]
      newRules.splice(index, 1)
      handleRulesChange(newRules)
    }
  }

  // Handle save rule from wizard
  const handleSaveRule = (rule: ValidationRuleConfig) => {
    const newRules = [...rules]
    if (editingIndex >= 0) {
      newRules[editingIndex] = rule
    } else {
      newRules.push(rule)
    }
    handleRulesChange(newRules)
    setIsWizardOpen(false)
    setEditingRule(undefined)
    setEditingIndex(-1)
  }

  // Handle wizard close
  const handleWizardClose = () => {
    setIsWizardOpen(false)
    setEditingRule(undefined)
    setEditingIndex(-1)
  }

  // Handle save
  const handleSave = () => {
    saveMutation.mutate()
  }

  // Show loading state
  if (isConfigLoading && !currentConfig) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
      </div>
    )
  }

  // Show error state if config failed to load
  if (configError && !currentConfig) {
    return (
      <div className="max-w-2xl mx-auto p-6 lg:p-8">
        <Card>
          <div className="py-12 text-center">
            <AlertCircle className="h-12 w-12 text-rose-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">Failed to load configuration</h2>
            <p className="text-slate-400 mb-4">
              {typeof configError === 'string'
                ? configError
                : configError && typeof configError === 'object' && 'message' in configError
                ? String((configError as { message: unknown }).message)
                : 'Backend API Not Available'}
            </p>
            <Button onClick={() => loadConfig()}>Retry</Button>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
            <Link href="/config" className="hover:text-cyan-400">
              Configuration
            </Link>
            <ChevronRight className="w-4 h-4" />
            <span className="text-white font-medium">Validation</span>
          </div>
          <h1 className="text-2xl font-bold text-white">Validation Rules</h1>
          <p className="text-sm text-slate-400 mt-1">
            Create and manage data validation rules for your tables
          </p>
        </div>
        <div className="flex items-center gap-3">
          {saveSuccess && (
            <div className="flex items-center gap-2 text-sm text-emerald-400">
              <CheckCircle className="w-4 h-4" />
              <span>Configuration saved</span>
            </div>
          )}
          <Button
            onClick={handleAddRule}
            icon={<Plus className="w-4 h-4" />}
          >
            Add Rule
          </Button>
          <Button
            onClick={handleSave}
            disabled={!canSave || saveMutation.isPending}
            icon={saveMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          >
            {saveMutation.isPending ? 'Saving...' : 'Save Configuration'}
          </Button>
        </div>
      </div>

      {/* Error message */}
      {validationErrors.general && (
        <Card className="glass-card border-rose-500/30 bg-rose-500/10">
          <div className="p-4 flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-rose-300">Error</p>
              <p className="text-sm text-rose-400/80 mt-1">{validationErrors.general}</p>
            </div>
          </div>
        </Card>
      )}

      {/* Banner linking to contracts */}
      <div className="glass-card border-emerald-500/30 bg-emerald-500/10 p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div>
            <p className="text-sm font-medium text-emerald-300">
              Contract-level validation rules
            </p>
            <p className="text-xs text-emerald-400/80 mt-1">
              Configure validation rules per contract, dataset, and column
            </p>
          </div>
        </div>
        <Link href="/config/contracts">
          <Button variant="outline" icon={<ArrowRight className="w-4 h-4" />}>
            Manage in Contracts
          </Button>
        </Link>
      </div>

      {/* Validation enabled toggle */}
      <Card>
        <div className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-white mb-1">Enable Validation</h3>
              <p className="text-xs text-slate-400">
                When enabled, validation rules will be executed during profiling runs
              </p>
            </div>
            <Toggle
              checked={validation?.enabled !== false}
              onChange={handleEnabledChange}
            />
          </div>
        </div>
      </Card>

      {/* Rules list */}
      <RuleList
        rules={rules}
        onEdit={handleEditRule}
        onDelete={handleDeleteRule}
        isLoading={isConfigLoading}
      />

      {/* Rule wizard */}
      <RuleWizard
        isOpen={isWizardOpen}
        onClose={handleWizardClose}
        onSave={handleSaveRule}
        initialRule={editingRule}
      />
    </div>
  )
}

