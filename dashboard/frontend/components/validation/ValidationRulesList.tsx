'use client'

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Edit, Trash2, Play, Plus, Shield, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Input } from '@/components/ui/Input'
import { Select, SelectOption } from '@/components/ui/Select'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import type { ValidationRule, ValidationRulesFilters, ValidationRuleType } from '@/types/validationRules'
import {
  listValidationRules,
  deleteValidationRule,
  testValidationRule,
  ValidationRulesError,
} from '@/lib/api/validationRules'
import { useQuery } from '@tanstack/react-query'

export interface ValidationRulesListProps {
  onCreateRule: () => void
  onEditRule: (rule: ValidationRule) => void
}

const RULE_TYPE_OPTIONS: SelectOption[] = [
  { value: '', label: 'All Types' },
  { value: 'format', label: 'Format' },
  { value: 'range', label: 'Range' },
  { value: 'enum', label: 'Enum' },
  { value: 'not_null', label: 'Not Null' },
  { value: 'unique', label: 'Unique' },
  { value: 'referential', label: 'Referential' },
]

const SEVERITY_OPTIONS: SelectOption[] = [
  { value: '', label: 'All Severities' },
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
]

function getRuleTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    format: 'Format',
    range: 'Range',
    enum: 'Enum',
    not_null: 'Not Null',
    unique: 'Unique',
    referential: 'Referential',
  }
  return labels[type] || type
}

function getSeverityVariant(severity: string): 'success' | 'warning' | 'error' | 'info' | 'default' {
  const variants: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
    low: 'default',
    medium: 'warning',
    high: 'error',
  }
  return variants[severity] || 'default'
}

function getRuleSummary(rule: ValidationRule): string {
  switch (rule.rule_type) {
    case 'format':
      return (rule.config.pattern as string) || 'No pattern'
    case 'range':
      const min = rule.config.min_value !== null && rule.config.min_value !== undefined 
        ? rule.config.min_value 
        : '∞'
      const max = rule.config.max_value !== null && rule.config.max_value !== undefined 
        ? rule.config.max_value 
        : '∞'
      return `${min} - ${max}`
    case 'enum':
      const values = rule.config.allowed_values as unknown[]
      return values?.length ? `${values.length} values` : 'No values'
    case 'referential':
      const ref = rule.config.references as Record<string, string>
      return ref ? `${ref.table}.${ref.column}` : 'No reference'
    default:
      return 'No parameters'
  }
}

export default function ValidationRulesList({ onCreateRule, onEditRule }: ValidationRulesListProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [severityFilter, setSeverityFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [testingRuleId, setTestingRuleId] = useState<string | null>(null)
  const queryClient = useQueryClient()

  // Build filters
  const filters: ValidationRulesFilters = {
    ...(typeFilter && { rule_type: typeFilter as ValidationRuleType }),
    ...(severityFilter && { severity: severityFilter }),
    ...(statusFilter === 'enabled' && { enabled: true }),
    ...(statusFilter === 'disabled' && { enabled: false }),
  }

  // Fetch rules
  const { data, isLoading, error } = useQuery({
    queryKey: ['validation-rules', filters],
    queryFn: () => listValidationRules(filters),
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: deleteValidationRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['validation-rules'] })
    },
  })

  // Test mutation
  const testMutation = useMutation({
    mutationFn: testValidationRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['validation-rules'] })
      setTestingRuleId(null)
    },
    onError: () => {
      setTestingRuleId(null)
    },
  })

  const handleDelete = async (ruleId: string) => {
    if (!confirm('Are you sure you want to delete this validation rule?')) {
      return
    }

    try {
      await deleteMutation.mutateAsync(ruleId)
    } catch (error) {
      console.error('Failed to delete rule:', error)
      alert(error instanceof ValidationRulesError ? error.message : 'Failed to delete rule')
    }
  }

  const handleTest = async (ruleId: string) => {
    setTestingRuleId(ruleId)
    try {
      await testMutation.mutateAsync(ruleId)
    } catch (error) {
      console.error('Failed to test rule:', error)
      alert(error instanceof ValidationRulesError ? error.message : 'Failed to test rule')
    }
  }

  // Filter rules by search query
  const filteredRules = (data?.rules || []).filter((rule) => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      rule.table.toLowerCase().includes(query) ||
      rule.column?.toLowerCase().includes(query) ||
      rule.schema?.toLowerCase().includes(query) ||
      getRuleTypeLabel(rule.rule_type).toLowerCase().includes(query)
    )
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error) {
    const errorMessage =
      error instanceof ValidationRulesError
        ? error.message
        : error instanceof Error
        ? error.message
        : 'Failed to load validation rules'
    return (
      <Card>
        <div className="p-6 text-center" role="alert">
          <AlertCircle className="w-12 h-12 text-rose-400 mx-auto mb-4" />
          <p className="text-rose-400">{errorMessage || 'Failed to load validation rules'}</p>
        </div>
      </Card>
    )
  }

  if (filteredRules.length === 0 && !searchQuery && !typeFilter && !severityFilter && !statusFilter) {
    return (
      <Card>
        <div className="p-12 text-center">
          <Shield className="w-16 h-16 text-slate-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No validation rules</h3>
          <p className="text-slate-400 mb-4">Create your first validation rule to get started</p>
          <Button onClick={onCreateRule} variant="primary">
            <Plus className="w-4 h-4 mr-2" />
            Create Rule
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <Card>
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Input
              placeholder="Search rules..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <Select
              value={typeFilter}
              onChange={(value) => setTypeFilter(value)}
              options={RULE_TYPE_OPTIONS}
            />
            <Select
              value={severityFilter}
              onChange={(value) => setSeverityFilter(value)}
              options={SEVERITY_OPTIONS}
            />
            <Select
              value={statusFilter}
              onChange={(value) => setStatusFilter(value)}
              options={[
                { value: '', label: 'All Status' },
                { value: 'enabled', label: 'Enabled' },
                { value: 'disabled', label: 'Disabled' },
              ]}
            />
          </div>
          <div className="flex justify-between items-center">
            <p className="text-sm text-slate-400">
              {filteredRules.length} of {data?.total || 0} rules
            </p>
            <Button onClick={onCreateRule} variant="primary" size="sm">
              <Plus className="w-4 h-4 mr-2" />
              Create Rule
            </Button>
          </div>
        </div>
      </Card>

      {/* Rules List */}
      <div className="space-y-3">
        {filteredRules.map((rule) => (
          <Card key={rule.id}>
            <div className="p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="font-semibold text-white">
                      {rule.schema ? `${rule.schema}.` : ''}
                      {rule.table}
                      {rule.column && `.${rule.column}`}
                    </h3>
                    <Badge variant={getSeverityVariant(rule.severity)}>{rule.severity}</Badge>
                    <Badge variant={rule.enabled ? 'success' : 'default'}>
                      {rule.enabled ? 'Enabled' : 'Disabled'}
                    </Badge>
                    {rule.last_test_result !== null && (
                      <Badge variant={rule.last_test_result ? 'success' : 'error'}>
                        {rule.last_test_result ? (
                          <CheckCircle className="w-3 h-3 mr-1" />
                        ) : (
                          <XCircle className="w-3 h-3 mr-1" />
                        )}
                        {rule.last_test_result ? 'Passed' : 'Failed'}
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="info">{getRuleTypeLabel(rule.rule_type)}</Badge>
                    <span className="text-sm text-slate-400">{getRuleSummary(rule)}</span>
                  </div>
                  <div className="text-xs text-slate-500">
                    Created: {new Date(rule.created_at).toLocaleDateString()}
                    {rule.last_tested && (
                      <> • Last tested: {new Date(rule.last_tested).toLocaleDateString()}</>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleTest(rule.id)}
                    disabled={testingRuleId === rule.id}
                    aria-label="Test rule"
                  >
                    {testingRuleId === rule.id ? (
                      <LoadingSpinner size="sm" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => onEditRule(rule)}
                    aria-label="Edit rule"
                  >
                    <Edit className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => handleDelete(rule.id)}
                    disabled={deleteMutation.isPending}
                    aria-label="Delete rule"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {filteredRules.length === 0 && (searchQuery || typeFilter || severityFilter || statusFilter) && (
        <Card>
          <div className="p-6 text-center">
            <p className="text-slate-400">No rules match your filters</p>
          </div>
        </Card>
      )}
    </div>
  )
}

