'use client'

import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/Button'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { Select, SelectOption } from '@/components/ui/Select'
import { Toggle } from '@/components/ui/Toggle'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import type { ValidationRule, CreateValidationRuleRequest, UpdateValidationRuleRequest } from '@/types/validationRules'
import { createValidationRule, updateValidationRule, ValidationRulesError } from '@/lib/api/validationRules'
import { FormatRuleForm } from './FormatRuleForm'
import { RangeRuleForm } from './RangeRuleForm'
import { EnumRuleForm } from './EnumRuleForm'
import { ReferentialRuleForm } from './ReferentialRuleForm'

export interface ValidationRuleModalProps {
  isOpen: boolean
  onClose: () => void
  rule?: ValidationRule | null
}

const RULE_TYPES: SelectOption[] = [
  { value: 'format', label: 'Format' },
  { value: 'range', label: 'Range' },
  { value: 'enum', label: 'Enum' },
  { value: 'not_null', label: 'Not Null' },
  { value: 'unique', label: 'Unique' },
  { value: 'referential', label: 'Referential' },
]

const SEVERITY_OPTIONS: SelectOption[] = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
]

export default function ValidationRuleModal({ isOpen, onClose, rule }: ValidationRuleModalProps) {
  const isEditMode = !!rule
  const queryClient = useQueryClient()

  const [formData, setFormData] = useState<CreateValidationRuleRequest>({
    rule_type: 'format',
    table: '',
    schema: null,
    column: null,
    config: {},
    severity: 'medium',
    enabled: true,
  })

  const [errors, setErrors] = useState<Record<string, string>>({})

  // Initialize form data when modal opens or rule changes
  useEffect(() => {
    if (isOpen) {
      if (rule) {
        setFormData({
          rule_type: rule.rule_type,
          table: rule.table,
          schema: rule.schema || null,
          column: rule.column || null,
          config: rule.config,
          severity: rule.severity,
          enabled: rule.enabled,
        })
      } else {
        setFormData({
          rule_type: 'format',
          table: '',
          schema: null,
          column: null,
          config: {},
          severity: 'medium',
          enabled: true,
        })
      }
      setErrors({})
    }
  }, [isOpen, rule])

  const createMutation = useMutation({
    mutationFn: createValidationRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['validation-rules'] })
      onClose()
    },
    onError: (error) => {
      if (error instanceof ValidationRulesError) {
        setErrors({ general: error.message })
      } else {
        setErrors({ general: 'Failed to create rule' })
      }
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ ruleId, data }: { ruleId: string; data: UpdateValidationRuleRequest }) =>
      updateValidationRule(ruleId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['validation-rules'] })
      onClose()
    },
    onError: (error) => {
      if (error instanceof ValidationRulesError) {
        setErrors({ general: error.message })
      } else {
        setErrors({ general: 'Failed to update rule' })
      }
    },
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrors({})

    // Validation
    if (!formData.table) {
      setErrors({ table: 'Table name is required' })
      return
    }

    if (isEditMode && rule) {
      const updateData: UpdateValidationRuleRequest = {
        rule_type: formData.rule_type,
        table: formData.table,
        schema: formData.schema,
        column: formData.column,
        config: formData.config,
        severity: formData.severity,
        enabled: formData.enabled,
      }
      await updateMutation.mutateAsync({ ruleId: rule.id, data: updateData })
    } else {
      await createMutation.mutateAsync(formData)
    }
  }

  const handleConfigChange = (config: Record<string, unknown>) => {
    setFormData((prev) => ({ ...prev, config }))
  }

  const isLoading = createMutation.isPending || updateMutation.isPending

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditMode ? 'Edit Validation Rule' : 'Create Validation Rule'}
      size="xl"
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        {errors.general && (
          <div className="p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
            {errors.general}
          </div>
        )}

        {/* Basic Info */}
        <div className="space-y-4">
          <FormField label="Rule Type" required>
            <Select
              value={formData.rule_type}
              onChange={(value) => setFormData((prev) => ({ ...prev, rule_type: value as typeof formData.rule_type, config: {} }))}
              options={RULE_TYPES}
              disabled={isEditMode}
            />
          </FormField>

          <div className="grid grid-cols-2 gap-4">
            <FormField label="Schema" error={errors.schema}>
              <Input
                value={formData.schema || ''}
                onChange={(e) => setFormData((prev) => ({ ...prev, schema: e.target.value || null }))}
                placeholder="public"
              />
            </FormField>
            <FormField label="Table" required error={errors.table}>
              <Input
                value={formData.table}
                onChange={(e) => setFormData((prev) => ({ ...prev, table: e.target.value }))}
                placeholder="users"
              />
            </FormField>
          </div>

          <FormField label="Column" error={errors.column}>
            <Input
              value={formData.column || ''}
              onChange={(e) => setFormData((prev) => ({ ...prev, column: e.target.value || null }))}
              placeholder="email (optional for table-level rules)"
            />
          </FormField>

          <FormField label="Severity">
            <Select
              value={formData.severity}
              onChange={(value) => setFormData((prev) => ({ ...prev, severity: value as typeof formData.severity }))}
              options={SEVERITY_OPTIONS}
            />
          </FormField>

          <FormField label="Enabled">
            <Toggle
              checked={formData.enabled ?? true}
              onChange={(checked) => setFormData((prev) => ({ ...prev, enabled: checked }))}
            />
          </FormField>
        </div>

        {/* Rule-Specific Configuration */}
        <div className="border-t pt-4">
          {formData.rule_type === 'format' && (
            <FormatRuleForm
              rule={{
                type: 'format',
                table: formData.table,
                column: formData.column || undefined,
                pattern: (formData.config.pattern as string) || undefined,
                severity: formData.severity,
                enabled: formData.enabled,
              }}
              onChange={(rule) => {
                handleConfigChange({
                  pattern: rule.pattern || undefined,
                })
              }}
            />
          )}
          {formData.rule_type === 'range' && (
            <RangeRuleForm
              rule={{
                type: 'range',
                table: formData.table,
                column: formData.column || undefined,
                min_value: (formData.config.min_value as number) || undefined,
                max_value: (formData.config.max_value as number) || undefined,
                severity: formData.severity,
                enabled: formData.enabled,
              }}
              onChange={(rule) => {
                handleConfigChange({
                  min_value: rule.min_value || undefined,
                  max_value: rule.max_value || undefined,
                })
              }}
            />
          )}
          {formData.rule_type === 'enum' && (
            <EnumRuleForm
              rule={{
                type: 'enum',
                table: formData.table,
                column: formData.column || undefined,
                allowed_values: (formData.config.allowed_values as unknown[]) || undefined,
                severity: formData.severity,
                enabled: formData.enabled,
              }}
              onChange={(rule) => {
                handleConfigChange({
                  allowed_values: rule.allowed_values || undefined,
                })
              }}
            />
          )}
          {formData.rule_type === 'referential' && (
            <ReferentialRuleForm
              rule={{
                type: 'referential',
                table: formData.table,
                column: formData.column || undefined,
                references: (formData.config.references as Record<string, string>) || undefined,
                severity: formData.severity,
                enabled: formData.enabled,
              }}
              onChange={(rule) => {
                handleConfigChange({
                  references: rule.references || undefined,
                })
              }}
            />
          )}
          {(formData.rule_type === 'not_null' || formData.rule_type === 'unique') && (
            <div className="text-sm text-gray-500">
              No additional configuration needed for {formData.rule_type} rules.
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={isLoading}>
            {isLoading ? (
              <>
                <LoadingSpinner size="sm" className="mr-2" />
                {isEditMode ? 'Updating...' : 'Creating...'}
              </>
            ) : (
              isEditMode ? 'Update Rule' : 'Create Rule'
            )}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

