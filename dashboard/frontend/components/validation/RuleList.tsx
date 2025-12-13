'use client'

import { useState, useMemo } from 'react'
import { Edit, Trash2, Eye, Shield } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Input } from '@/components/ui/Input'
import { Select, SelectOption } from '@/components/ui/Select'
import { ValidationRuleConfig } from '@/types/config'

export interface RuleListProps {
  rules: ValidationRuleConfig[]
  onEdit: (rule: ValidationRuleConfig, index: number) => void
  onDelete: (index: number) => void
  onTest?: (rule: ValidationRuleConfig) => void
  isLoading?: boolean
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

const STATUS_OPTIONS: SelectOption[] = [
  { value: '', label: 'All Status' },
  { value: 'enabled', label: 'Enabled' },
  { value: 'disabled', label: 'Disabled' },
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

function getRuleTypeVariant(type: string): 'success' | 'warning' | 'error' | 'info' | 'default' {
  const variants: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
    format: 'info',
    range: 'success',
    enum: 'default',
    not_null: 'warning',
    unique: 'info',
    referential: 'default',
  }
  return variants[type] || 'default'
}

function getSeverityVariant(severity: string): 'success' | 'warning' | 'error' | 'info' | 'default' {
  const variants: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
    low: 'default',
    medium: 'warning',
    high: 'error',
  }
  return variants[severity] || 'default'
}

function getRuleSummary(rule: ValidationRuleConfig): string {
  switch (rule.type) {
    case 'format':
      return rule.pattern || 'No pattern'
    case 'range':
      const min = rule.min_value !== null && rule.min_value !== undefined ? rule.min_value : '∞'
      const max = rule.max_value !== null && rule.max_value !== undefined ? rule.max_value : '∞'
      return `${min} - ${max}`
    case 'enum':
      return rule.allowed_values?.length
        ? `${rule.allowed_values.length} values`
        : 'No values'
    case 'referential':
      return rule.references
        ? `${rule.references.table}.${rule.references.column}`
        : 'No reference'
    default:
      return 'No parameters'
  }
}

export function RuleList({ rules, onEdit, onDelete, onTest, isLoading }: RuleListProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [severityFilter, setSeverityFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  const filteredRules = useMemo(() => {
    return rules.filter((rule) => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        const tableMatch = rule.table?.toLowerCase().includes(query)
        const columnMatch = rule.column?.toLowerCase().includes(query)
        if (!tableMatch && !columnMatch) return false
      }

      // Type filter
      if (typeFilter && rule.type !== typeFilter) return false

      // Severity filter
      if (severityFilter && rule.severity !== severityFilter) return false

      // Status filter
      if (statusFilter === 'enabled' && rule.enabled === false) return false
      if (statusFilter === 'disabled' && rule.enabled !== false) return false

      return true
    })
  }, [rules, searchQuery, typeFilter, severityFilter, statusFilter])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-sm text-slate-400">Loading rules...</div>
      </div>
    )
  }

  if (rules.length === 0) {
    return (
      <Card>
        <div className="py-12 text-center">
          <Shield className="w-12 h-12 text-slate-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No validation rules</h3>
          <p className="text-sm text-slate-400">
            Create your first validation rule to start validating your data
          </p>
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
            <div>
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search table or column..."
                className="w-full"
              />
            </div>
            <Select
              value={typeFilter}
              onChange={setTypeFilter}
              options={RULE_TYPE_OPTIONS}
              placeholder="Filter by type"
            />
            <Select
              value={severityFilter}
              onChange={setSeverityFilter}
              options={SEVERITY_OPTIONS}
              placeholder="Filter by severity"
            />
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              options={STATUS_OPTIONS}
              placeholder="Filter by status"
            />
          </div>
        </div>
      </Card>

      {/* Rules list */}
      <div className="space-y-3">
        {filteredRules.length === 0 ? (
          <Card>
            <div className="py-8 text-center">
              <p className="text-sm text-slate-400">No rules match your filters</p>
            </div>
          </Card>
        ) : (
          filteredRules.map((rule) => {
            const originalIndex = rules.indexOf(rule)
            return (
              <Card key={originalIndex}>
                <div className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge
                          variant={getRuleTypeVariant(rule.type)}
                          outline
                        >
                          {getRuleTypeLabel(rule.type)}
                        </Badge>
                        <Badge
                          variant={getSeverityVariant(rule.severity || 'medium')}
                          outline
                        >
                          {rule.severity || 'medium'}
                        </Badge>
                        {rule.enabled === false && (
                          <Badge variant="default" outline>
                            Disabled
                          </Badge>
                        )}
                      </div>
                      <div className="space-y-1">
                        <p className="text-sm font-medium text-white">
                          {rule.table}
                          {rule.column && <span className="text-slate-400">.{rule.column}</span>}
                        </p>
                        <p className="text-xs text-slate-400">{getRuleSummary(rule)}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {onTest && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onTest(rule)}
                          icon={<Eye className="w-4 h-4" />}
                          title="Test rule"
                        />
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onEdit(rule, originalIndex)}
                        icon={<Edit className="w-4 h-4" />}
                        title="Edit rule"
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onDelete(originalIndex)}
                        icon={<Trash2 className="w-4 h-4" />}
                        title="Delete rule"
                      />
                    </div>
                  </div>
                </div>
              </Card>
            )
          })
        )}
      </div>

      {/* Summary */}
      <div className="text-sm text-slate-400">
        Showing {filteredRules.length} of {rules.length} rules
      </div>
    </div>
  )
}

