'use client'

import { useState, useEffect } from 'react'
import { CheckCircle, XCircle, ArrowRight, ArrowLeft } from 'lucide-react'
import { HookConfig } from '@/types/config'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Select'
import { FormField } from '@/components/ui/FormField'
import { LoggingHookForm } from './LoggingHookForm'
import { SlackHookForm } from './SlackHookForm'
import { SQLHookForm } from './SQLHookForm'
import { SnowflakeHookForm } from './SnowflakeHookForm'
import { CustomHookForm } from './CustomHookForm'
import { HookTestButton } from './HookTestButton'

export interface HookWizardProps {
  isOpen: boolean
  onClose: () => void
  onSave: (hook: HookConfig) => void
  initialHook?: HookConfig
  hookId?: string
}

const HOOK_TYPES = [
  { value: 'logging', label: 'Logging', description: 'Log events to stdout' },
  { value: 'sql', label: 'SQL', description: 'Store events in SQL database' },
  { value: 'snowflake', label: 'Snowflake', description: 'Store events in Snowflake' },
  { value: 'slack', label: 'Slack', description: 'Send Slack notifications' },
  { value: 'custom', label: 'Custom', description: 'Custom hook implementation' },
]

export function HookWizard({
  isOpen,
  onClose,
  onSave,
  initialHook,
  hookId,
}: HookWizardProps) {
  const [currentStep, setCurrentStep] = useState(1)
  const [hook, setHook] = useState<HookConfig>(() => {
    if (initialHook) {
      return initialHook
    }
    return {
      type: 'logging',
      enabled: true,
    }
  })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [isSaving, setIsSaving] = useState(false)

  const isEditMode = !!hookId
  const totalSteps = 4

  // Reset state when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      if (initialHook) {
        setHook(initialHook)
        setCurrentStep(2) // Skip type selection in edit mode
      } else {
        setHook({
          type: 'logging',
          enabled: true,
        })
        setCurrentStep(1)
      }
      setErrors({})
    }
  }, [isOpen, initialHook, hookId])

  const validateStep1 = (): boolean => {
    if (!hook.type) {
      setErrors({ type: 'Please select a hook type' })
      return false
    }
    setErrors({})
    return true
  }

  const validateStep2 = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (hook.type === 'slack') {
      if (!hook.webhook_url) {
        newErrors.webhook_url = 'Webhook URL is required'
      }
    } else if (hook.type === 'sql' || hook.type === 'snowflake') {
      if (!hook.connection) {
        newErrors.connection = 'Connection is required'
      }
    } else if (hook.type === 'custom') {
      if (!hook.module) {
        newErrors.module = 'Module path is required'
      }
      if (!hook.class_name) {
        newErrors.class_name = 'Class name is required'
      }
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleNext = () => {
    if (currentStep === 1) {
      if (!validateStep1()) return
      setCurrentStep(2)
    } else if (currentStep === 2) {
      if (!validateStep2()) return
      setCurrentStep(3)
    } else if (currentStep === 3) {
      setCurrentStep(4)
    }
  }

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSave = async () => {
    if (!validateStep2()) return

    setIsSaving(true)
    try {
      await onSave(hook)
    } catch (err) {
      console.error('Failed to save hook:', err)
      // Error will be handled by the parent component
    } finally {
      setIsSaving(false)
    }
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="space-y-4">
            <FormField label="Hook Type" required error={errors.type}>
              <Select
                options={HOOK_TYPES.map((type) => ({
                  value: type.value,
                  label: `${type.label} - ${type.description}`,
                }))}
                value={hook.type}
                onChange={(value) =>
                  setHook({
                    ...hook,
                    type: value as HookConfig['type'],
                  })
                }
              />
            </FormField>
          </div>
        )

      case 2:
        return (
          <div className="space-y-4">
            {hook.type === 'logging' && (
              <LoggingHookForm hook={hook} onChange={setHook} errors={errors} />
            )}
            {hook.type === 'slack' && (
              <SlackHookForm hook={hook} onChange={setHook} errors={errors} />
            )}
            {hook.type === 'sql' && (
              <SQLHookForm hook={hook} onChange={setHook} errors={errors} />
            )}
            {hook.type === 'snowflake' && (
              <SnowflakeHookForm hook={hook} onChange={setHook} errors={errors} />
            )}
            {hook.type === 'custom' && (
              <CustomHookForm hook={hook} onChange={setHook} errors={errors} />
            )}
          </div>
        )

      case 3:
        return (
          <div className="space-y-4">
            <div className="glass-card border-surface-700/50 p-4">
              <h3 className="font-medium text-white mb-2">Test Hook</h3>
              <p className="text-sm text-slate-400 mb-4">
                Test your hook configuration by sending a test event. This is optional but recommended.
              </p>
              {hookId ? (
                <HookTestButton hookId={hookId} hook={hook} />
              ) : (
                <div className="text-sm text-slate-500 italic">
                  Save the hook first to enable testing
                </div>
              )}
            </div>
          </div>
        )

      case 4:
        return (
          <div className="space-y-4">
            <div className="glass-card border-cyan-500/30 bg-cyan-500/10 p-4">
              <h3 className="font-medium text-cyan-300 mb-2">Review Configuration</h3>
              <div className="text-sm text-cyan-200 space-y-1">
                <div>
                  <strong>Type:</strong> {HOOK_TYPES.find((t) => t.value === hook.type)?.label}
                </div>
                <div>
                  <strong>Enabled:</strong> {hook.enabled !== false ? 'Yes' : 'No'}
                </div>
                {hook.type === 'slack' && hook.channel && (
                  <div>
                    <strong>Channel:</strong> {hook.channel}
                  </div>
                )}
                {hook.type === 'logging' && hook.log_level && (
                  <div>
                    <strong>Log Level:</strong> {hook.log_level}
                  </div>
                )}
              </div>
            </div>
          </div>
        )

      default:
        return null
    }
  }

  const getStepTitle = () => {
    switch (currentStep) {
      case 1:
        return 'Select Hook Type'
      case 2:
        return 'Configure Hook'
      case 3:
        return 'Test Hook (Optional)'
      case 4:
        return 'Review & Save'
      default:
        return 'Hook Wizard'
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={getStepTitle()}
      size="lg"
    >
      {/* Progress Indicator */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          {Array.from({ length: totalSteps }).map((_, idx) => {
            const step = idx + 1
            const isActive = step === currentStep
            const isCompleted = step < currentStep

            return (
              <div key={step} className="flex items-center flex-1">
                <div className="flex items-center flex-1">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                      isActive
                        ? 'bg-cyan-500 text-white'
                        : isCompleted
                        ? 'bg-emerald-500 text-white'
                        : 'bg-surface-700 text-slate-400'
                    }`}
                  >
                    {isCompleted ? (
                      <CheckCircle className="w-5 h-5" />
                    ) : (
                      step
                    )}
                  </div>
                  {step < totalSteps && (
                    <div
                      className={`flex-1 h-1 mx-2 ${
                        isCompleted ? 'bg-emerald-500' : 'bg-surface-700'
                      }`}
                    />
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Step Content */}
      <div className="min-h-[300px]">{renderStepContent()}</div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-6 border-t border-surface-700/50">
        <Button
          variant="outline"
          onClick={currentStep === 1 ? onClose : handleBack}
          icon={currentStep === 1 ? <XCircle className="w-4 h-4" /> : <ArrowLeft className="w-4 h-4" />}
        >
          {currentStep === 1 ? 'Cancel' : 'Back'}
        </Button>

        <div className="flex gap-2">
          {currentStep < totalSteps ? (
            <Button
              onClick={handleNext}
              icon={<ArrowRight className="w-4 h-4" />}
              iconPosition="right"
            >
              Next
            </Button>
          ) : (
            <Button
              onClick={handleSave}
              loading={isSaving}
              icon={<CheckCircle className="w-4 h-4" />}
            >
              {isEditMode ? 'Update Hook' : 'Create Hook'}
            </Button>
          )}
        </div>
      </div>
    </Modal>
  )
}

export default HookWizard

