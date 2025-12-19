'use client'

import { useState, useEffect } from 'react'
import { ChevronLeft, ChevronRight, Database, CheckCircle } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/Button'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { Select, SelectOption } from '@/components/ui/Select'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { ValidationRuleConfig } from '@/types/config'
import { discoverTables, getTablePreview, TableInfo, TableMetadataResponse } from '@/lib/api/tables'
import { listConnections } from '@/lib/api/connections'
import { useQuery } from '@tanstack/react-query'
import { FormatRuleForm } from './FormatRuleForm'
import { RangeRuleForm } from './RangeRuleForm'
import { EnumRuleForm } from './EnumRuleForm'
import { ReferentialRuleForm } from './ReferentialRuleForm'
import { RuleTestPreview } from './RuleTestPreview'

export interface RuleWizardProps {
  isOpen: boolean
  onClose: () => void
  onSave: (rule: ValidationRuleConfig) => void
  initialRule?: ValidationRuleConfig
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

export function RuleWizard({ isOpen, onClose, onSave, initialRule }: RuleWizardProps) {
  const [currentStep, setCurrentStep] = useState(1)
  const [rule, setRule] = useState<ValidationRuleConfig>(() => {
    if (initialRule) {
      return { ...initialRule }
    }
    return {
      type: 'format',
      severity: 'medium',
      enabled: true,
    }
  })
  const [schema, setSchema] = useState<string>('public')
  const [table, setTable] = useState<string>('')
  const [column, setColumn] = useState<string>('')
  const [connectionId, setConnectionId] = useState<string | undefined>(undefined)
  const [errors, setErrors] = useState<Record<string, string>>({})

  const isEditMode = !!initialRule

  // Reset state when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      if (initialRule) {
        setRule({ ...initialRule })
        setSchema(initialRule.table?.split('.')[0] || 'public')
        setTable(initialRule.table?.split('.')[1] || initialRule.table || '')
        setColumn(initialRule.column || '')
        setCurrentStep(1)
      } else {
        setRule({
          type: 'format',
          severity: 'medium',
          enabled: true,
        })
        setSchema('public')
        setTable('')
        setColumn('')
        setCurrentStep(1)
      }
      setErrors({})
    }
  }, [isOpen, initialRule])

  // Fetch tables for table selector
  const { data: tablesData, isLoading: isLoadingTables } = useQuery<{ tables: TableInfo[] }>({
    queryKey: ['tables', 'discover', schema, connectionId],
    queryFn: async () => {
      const result = await discoverTables(
        {
          schemas: [schema],
        },
        connectionId
      )
      return { tables: result.tables }
    },
    enabled: !!schema,
  })

  // Fetch columns for column selector
  const { data: tableMetadata, isLoading: isLoadingColumns } = useQuery<TableMetadataResponse>({
    queryKey: ['table', 'preview', schema, table, connectionId],
    queryFn: () => getTablePreview(schema, table, connectionId),
    enabled: !!schema && !!table,
  })

  // Fetch connections
  const { data: connectionsData } = useQuery({
    queryKey: ['connections'],
    queryFn: listConnections,
  })

  const validateStep1 = (): boolean => {
    const newErrors: Record<string, string> = {}
    if (!schema) {
      newErrors.schema = 'Schema is required'
    }
    if (!table) {
      newErrors.table = 'Table is required'
    }
    if (!column) {
      newErrors.column = 'Column is required'
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const validateStep2 = (): boolean => {
    if (!rule.type) {
      setErrors({ type: 'Please select a rule type' })
      return false
    }
    setErrors({})
    return true
  }

  const validateStep3 = (): boolean => {
    const newErrors: Record<string, string> = {}
    
    switch (rule.type) {
      case 'format':
        if (!rule.pattern) {
          newErrors.pattern = 'Pattern is required for format validation'
        }
        break
      case 'range':
        if (rule.min_value === null && rule.max_value === null) {
          newErrors.range = 'At least one bound (min or max) is required'
        }
        if (rule.min_value !== null && rule.max_value !== null && rule.min_value > rule.max_value) {
          newErrors.range = 'Minimum value must be less than or equal to maximum value'
        }
        break
      case 'enum':
        if (!rule.allowed_values || rule.allowed_values.length === 0) {
          newErrors.allowed_values = 'At least one allowed value is required'
        }
        break
      case 'referential':
        if (!rule.references?.table || !rule.references?.column) {
          newErrors.references = 'Reference table and column are required'
        }
        break
    }
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleNext = () => {
    if (currentStep === 1 && !validateStep1()) return
    if (currentStep === 2 && !validateStep2()) return
    if (currentStep === 3 && !validateStep3()) return
    
    if (currentStep < 5) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSave = () => {
    // Update rule with table and column
    const fullTable = schema !== 'public' ? `${schema}.${table}` : table
    const finalRule: ValidationRuleConfig = {
      ...rule,
      table: fullTable,
      column,
    }
    onSave(finalRule)
    onClose()
  }

  // Update rule when table/column changes
  useEffect(() => {
    if (table && column) {
      const fullTable = schema !== 'public' ? `${schema}.${table}` : table
      setRule((prev) => ({
        ...prev,
        table: fullTable,
        column,
      }))
    }
  }, [schema, table, column])

  const tableOptions: SelectOption[] = (tablesData?.tables || []).map((t) => ({
    value: t.table,
    label: t.table,
  }))

  const columnOptions: SelectOption[] = (tableMetadata?.columns || []).map((col) => ({
    value: col.name,
    label: `${col.name} (${col.type})`,
  }))

  const connectionOptions: SelectOption[] = [
    { value: '', label: 'Use default connection' },
    ...(connectionsData?.connections || []).map((conn) => ({
      value: conn.id,
      label: conn.name,
    })),
  ]

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-sm text-gray-600 mb-4">
              <Database className="w-4 h-4" />
              <span>Select the table and column to validate</span>
            </div>

            <FormField label="Connection" helperText="Optional: Select a saved connection">
              <Select
                value={connectionId || ''}
                onChange={(value) => setConnectionId(value || undefined)}
                options={connectionOptions}
              />
            </FormField>

            <FormField
              label="Schema"
              error={errors.schema}
              required
            >
              <Input
                value={schema}
                onChange={(e) => setSchema(e.target.value)}
                placeholder="public"
              />
            </FormField>

            <FormField
              label="Table"
              error={errors.table}
              required
            >
              {isLoadingTables ? (
                <LoadingSpinner size="sm" />
              ) : (
                <Select
                  value={table}
                  onChange={setTable}
                  options={tableOptions}
                  placeholder="Select table"
                />
              )}
            </FormField>

            <FormField
              label="Column"
              error={errors.column}
              required
            >
              {isLoadingColumns ? (
                <LoadingSpinner size="sm" />
              ) : (
                <Select
                  value={column}
                  onChange={setColumn}
                  options={columnOptions}
                  placeholder="Select column"
                  disabled={!table}
                />
              )}
            </FormField>
          </div>
        )

      case 2:
        return (
          <div className="space-y-4">
            <div className="text-sm text-gray-600 mb-4">
              Select the type of validation rule to create
            </div>

            <FormField
              label="Rule Type"
              error={errors.type}
              required
            >
              <Select
                value={rule.type}
                onChange={(value) => setRule({ ...rule, type: value as ValidationRuleConfig['type'] })}
                options={RULE_TYPES}
              />
            </FormField>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-900">
                {rule.type === 'format' && 'Validates column values against a regex pattern or predefined format (email, URL, phone).'}
                {rule.type === 'range' && 'Validates numeric values or string lengths are within min/max bounds.'}
                {rule.type === 'enum' && 'Validates that column values are in a list of allowed values.'}
                {rule.type === 'not_null' && 'Validates that columns do not contain NULL values.'}
                {rule.type === 'unique' && 'Validates that column values are unique across all rows.'}
                {rule.type === 'referential' && 'Validates foreign key relationships between tables.'}
              </p>
            </div>
          </div>
        )

      case 3:
        return (
          <div className="space-y-4">
            {rule.type === 'format' && (
              <FormatRuleForm
                rule={rule}
                onChange={setRule}
                errors={errors}
              />
            )}
            {rule.type === 'range' && (
              <RangeRuleForm
                rule={rule}
                onChange={setRule}
                errors={errors}
              />
            )}
            {rule.type === 'enum' && (
              <EnumRuleForm
                rule={rule}
                onChange={setRule}
                errors={errors}
              />
            )}
            {rule.type === 'referential' && (
              <ReferentialRuleForm
                rule={rule}
                onChange={setRule}
                errors={errors}
                connectionId={connectionId}
              />
            )}
            {(rule.type === 'not_null' || rule.type === 'unique') && (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <p className="text-sm text-gray-700">
                  {rule.type === 'not_null' && 'This rule requires no additional parameters. It will validate that the column does not contain NULL values.'}
                  {rule.type === 'unique' && 'This rule requires no additional parameters. It will validate that all values in the column are unique.'}
                </p>
              </div>
            )}
          </div>
        )

      case 4:
        return (
          <div className="space-y-4">
            <FormField
              label="Severity"
              required
            >
              <Select
                value={rule.severity || 'medium'}
                onChange={(value) => setRule({ ...rule, severity: value as 'low' | 'medium' | 'high' })}
                options={SEVERITY_OPTIONS}
              />
            </FormField>

            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <p className="text-sm text-gray-700 mb-2">
                <strong>Severity levels:</strong>
              </p>
              <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
                <li><strong>Low:</strong> Informational, non-critical issues</li>
                <li><strong>Medium:</strong> Important issues that should be addressed</li>
                <li><strong>High:</strong> Critical issues that must be fixed</li>
              </ul>
            </div>

            <FormField
              label="Enabled"
              helperText="Disable this rule to temporarily skip validation"
            >
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={rule.enabled !== false}
                  onChange={(e) => setRule({ ...rule, enabled: e.target.checked })}
                  className="w-4 h-4 text-primary-600 rounded"
                />
                <span className="text-sm text-gray-700">
                  {rule.enabled !== false ? 'Rule is enabled' : 'Rule is disabled'}
                </span>
              </div>
            </FormField>
          </div>
        )

      case 5:
        return (
          <div className="space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <h4 className="text-sm font-medium text-green-900">Rule Summary</h4>
              </div>
              <div className="text-sm text-green-800 space-y-1">
                <p><strong>Table:</strong> {rule.table}</p>
                <p><strong>Column:</strong> {rule.column}</p>
                <p><strong>Type:</strong> {rule.type}</p>
                <p><strong>Severity:</strong> {rule.severity}</p>
                <p><strong>Enabled:</strong> {rule.enabled !== false ? 'Yes' : 'No'}</p>
              </div>
            </div>

            <RuleTestPreview rule={rule} connectionId={connectionId} />
          </div>
        )

      default:
        return null
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditMode ? 'Edit Validation Rule' : 'Create Validation Rule'}
      size="xl"
    >
      <div className="space-y-6">
        {/* Step indicator */}
        <div className="flex items-center justify-between">
          {[1, 2, 3, 4, 5].map((step) => (
            <div key={step} className="flex items-center flex-1">
              <div
                className={`flex items-center justify-center w-8 h-8 rounded-full ${
                  step === currentStep
                    ? 'bg-primary-600 text-white'
                    : step < currentStep
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-200 text-gray-600'
                }`}
              >
                {step < currentStep ? <CheckCircle className="w-5 h-5" /> : step}
              </div>
              {step < 5 && (
                <div
                  className={`flex-1 h-1 mx-2 ${
                    step < currentStep ? 'bg-green-600' : 'bg-gray-200'
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        <div className="text-xs text-gray-600 text-center">
          Step {currentStep} of 5: {
            currentStep === 1 && 'Table & Column'
            || currentStep === 2 && 'Rule Type'
            || currentStep === 3 && 'Rule Parameters'
            || currentStep === 4 && 'Severity & Options'
            || currentStep === 5 && 'Preview & Test'
          }
        </div>

        {/* Step content */}
        <div className="min-h-[300px]">
          {renderStepContent()}
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between pt-4 border-t">
          <Button
            variant="outline"
            onClick={currentStep === 1 ? onClose : handleBack}
            icon={currentStep === 1 ? undefined : <ChevronLeft className="w-4 h-4" />}
          >
            {currentStep === 1 ? 'Cancel' : 'Back'}
          </Button>

          <div className="flex items-center gap-2">
            {currentStep < 5 ? (
              <Button
                onClick={handleNext}
                icon={<ChevronRight className="w-4 h-4" />}
                iconPosition="right"
              >
                Next
              </Button>
            ) : (
              <Button
                onClick={handleSave}
                icon={<CheckCircle className="w-4 h-4" />}
              >
                {isEditMode ? 'Update Rule' : 'Create Rule'}
              </Button>
            )}
          </div>
        </div>
      </div>
    </Modal>
  )
}

