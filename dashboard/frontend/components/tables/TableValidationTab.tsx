'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, XCircle, BarChart3 } from 'lucide-react'
import { LoadingSpinner } from '@/components/ui'
import { Badge } from '@/components/ui'
import { fetchTableValidationResults } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

interface TableValidationTabProps {
  tableName: string
  schema?: string
}

const COLORS = ['#10b981', '#ef4444'] // Green for pass, red for fail

export default function TableValidationTab({
  tableName,
  schema
}: TableValidationTabProps) {
  const [ruleTypeFilter, setRuleTypeFilter] = useState<string | undefined>()
  const [statusFilter, setStatusFilter] = useState<'all' | 'passed' | 'failed'>('all')
  const [severityFilter, setSeverityFilter] = useState<string | undefined>()

  const { data: results, isLoading, error } = useQuery({
    queryKey: ['table-validation-results', tableName, schema],
    queryFn: () => fetchTableValidationResults(tableName, { schema, limit: 100 }),
    staleTime: 30000
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error || !results) {
    return (
      <div className="bg-surface-800/40 border border-rose-500/20 rounded-lg p-6 text-center">
        <p className="text-rose-400 font-medium">Error loading validation results</p>
        <p className="text-slate-400 text-sm mt-1">
          {error instanceof Error ? error.message : 'Unknown error'}
        </p>
      </div>
    )
  }

  const validationResults = Array.isArray(results.validation_results) ? results.validation_results : []

  const filteredResults = validationResults.filter(result => {
    if (ruleTypeFilter && result.rule_type !== ruleTypeFilter) return false
    if (statusFilter === 'passed' && !result.passed) return false
    if (statusFilter === 'failed' && result.passed) return false
    if (severityFilter && result.severity !== severityFilter) return false
    return true
  })

  const passFailData = [
    { name: 'Passed', value: results.summary?.passed || 0 },
    { name: 'Failed', value: results.summary?.failed || 0 }
  ]

  const ruleTypeData = Object.entries(results.summary?.by_rule_type || {})
    .map(([name, value]) => ({ name, value: value as number }))
    .sort((a, b) => b.value - a.value)

  const uniqueRuleTypes = Array.from(new Set(validationResults.map(r => r.rule_type)))

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glass-card p-6">
          <p className="text-sm font-medium text-slate-400">Total Rules</p>
          <p className="text-2xl font-bold text-white mt-2">
            {results.summary?.total || validationResults.length}
          </p>
        </div>
        <div className="glass-card p-6 border-2 border-emerald-500/30 bg-emerald-500/5">
          <p className="text-sm font-medium text-emerald-400">Passed</p>
          <p className="text-2xl font-bold text-emerald-400 mt-2">
            {results.summary?.passed || 0}
          </p>
        </div>
        <div className="glass-card p-6 border-2 border-rose-500/30 bg-rose-500/5">
          <p className="text-sm font-medium text-rose-400">Failed</p>
          <p className="text-2xl font-bold text-rose-400 mt-2">
            {results.summary?.failed || 0}
          </p>
        </div>
        <div className="glass-card p-6">
          <p className="text-sm font-medium text-slate-400">Pass Rate</p>
          <p className="text-2xl font-bold text-white mt-2">
            {results.summary?.pass_rate?.toFixed(1) || '0.0'}%
          </p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pass/Fail Distribution */}
        <div className="glass-card p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            Pass/Fail Distribution
          </h2>
          <div className="h-64">
            {passFailData.some(d => d.value > 0) ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={passFailData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {passFailData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-slate-500">
                <p>No validation data available</p>
              </div>
            )}
          </div>
        </div>

        {/* Rule Type Breakdown */}
        <div className="glass-card p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Rule Type Breakdown</h2>
          <div className="h-64">
            {ruleTypeData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={ruleTypeData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis dataKey="name" type="category" width={120} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#0ea5e9" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-slate-500">
                <p>No rule type data available</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="glass-card p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Filter by Rule Type:</label>
            <select
              value={ruleTypeFilter || ''}
              onChange={(e) => setRuleTypeFilter(e.target.value || undefined)}
              className="w-full px-3 py-2 bg-surface-800/50 border border-surface-600 rounded-lg text-white focus:ring-2 focus:ring-cyan-500"
            >
              <option value="">All Rule Types</option>
              {uniqueRuleTypes.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Filter by Status:</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as 'all' | 'passed' | 'failed')}
              className="w-full px-3 py-2 bg-surface-800/50 border border-surface-600 rounded-lg text-white focus:ring-2 focus:ring-cyan-500"
            >
              <option value="all">All Statuses</option>
              <option value="passed">Passed Only</option>
              <option value="failed">Failed Only</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Filter by Severity:</label>
            <select
              value={severityFilter || ''}
              onChange={(e) => setSeverityFilter(e.target.value || undefined)}
              className="w-full px-3 py-2 bg-surface-800/50 border border-surface-600 rounded-lg text-white focus:ring-2 focus:ring-cyan-500"
            >
              <option value="">All Severities</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>
        </div>
      </div>

      {/* Validation Results Table */}
      <div className="glass-card overflow-hidden">
        <div className="px-6 py-4 border-b border-surface-700/50">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            {statusFilter === 'failed' ? (
              <XCircle className="w-5 h-5 text-rose-400" />
            ) : (
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            )}
            Validation Results ({filteredResults.length})
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-surface-800/60">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Rule Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Column
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Severity
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Failure Rate
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Validated At
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Details
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-700/50">
              {filteredResults.length > 0 ? (
                filteredResults.map((result) => (
                  <tr key={result.id} className="hover:bg-surface-800/30">
                    <td className="px-6 py-4 whitespace-nowrap">
                      {result.passed ? (
                        <Badge variant="success" size="sm">
                          <CheckCircle2 className="w-3 h-3 mr-1" />
                          Passed
                        </Badge>
                      ) : (
                        <Badge variant="error" size="sm">
                          <XCircle className="w-3 h-3 mr-1" />
                          Failed
                        </Badge>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                      {result.rule_type}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-400">
                      {result.column_name || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {result.severity ? (
                        <Badge
                          variant={result.severity === 'high' ? 'error' : result.severity === 'medium' ? 'warning' : 'default'}
                          size="sm"
                        >
                          {result.severity}
                        </Badge>
                      ) : (
                        '-'
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-400">
                      {result.failure_rate !== null && result.failure_rate !== undefined
                        ? `${result.failure_rate.toFixed(2)}%`
                        : result.failed_rows && result.total_rows
                        ? `${((result.failed_rows / result.total_rows) * 100).toFixed(2)}%`
                        : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-400">
                      {formatDate(result.validated_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {result.failure_reason && (
                        <span className="text-rose-400" title={result.failure_reason}>
                          {result.failure_reason.substring(0, 50)}
                          {result.failure_reason.length > 50 ? '...' : ''}
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-slate-500">
                    No validation results found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

